
import os
import webbrowser
import time
import warnings
import uuid
import json
import threading
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow logs
import logging
logging.getLogger().setLevel(logging.ERROR)  # Set logging level to ERROR to reduce output noise
#Added new part
try:
    import os
    _threads = str(max(1, (os.cpu_count() or 2) - 1))
    os.environ.setdefault("OMP_NUM_THREADS", _threads)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", _threads)
    os.environ.setdefault("MKL_NUM_THREADS", _threads)
    os.environ.setdefault("NUMEXPR_NUM_THREADS", _threads)
    os.environ.setdefault("OPENCV_OPENCL_RUNTIME", "disabled")
    try:
        import cv2
        cv2.setNumThreads(int(_threads))
    except Exception:
        pass
except Exception:
    pass



from flask import Flask, render_template,request,send_file,send_from_directory,jsonify,Response
from backend.subtitles.subs import get_subtitles
from backend.keyframes.keyframes import generate_keyframes, black_bar_crop
from backend.panel_layout.layout_gen import generate_layout
from backend.cartoonize.cartoonize import style_frames
from backend.speech_bubble.bubble import bubble_create
from backend.page_create import page_create,page_json
from backend.utils import cleanup, download_video
from backend.utils import copy_template
import pdfkit

log= logging.getLogger('werkzeug')
log.setLevel(logging.INFO)  # Set logging level to INFO for Werkzeug logs
app = Flask(__name__)

# Global dictionary to store job statuses
job_statuses = {}

@app.route('/')
def index():
    return render_template('index.html')

def run_comic_generation(video_path, job_id):
    """Background thread function for comic generation with progress updates"""
    try:
        start_time = time.time()
        
        # Step 1: Get Subtitles
        job_statuses[job_id]['progress'] = 15
        job_statuses[job_id]['message'] = 'Generating subtitles... (This may take a while)'
        get_subtitles(video_path)
        

        # Step 2: Extract Keyframes
        job_statuses[job_id]['progress'] = 30
        job_statuses[job_id]['message'] = 'Selecting keyframes from video...'
        generate_keyframes(video_path)

        # Step 3: Crop Black Bars
        job_statuses[job_id]['progress'] = 50
        job_statuses[job_id]['message'] = 'Cropping black bars from frames...'
        black_x, black_y, _, _ = black_bar_crop()

        # Step 4: Apply Cartoon Style
        job_statuses[job_id]['progress'] = 65
        job_statuses[job_id]['message'] = 'Applying cartoon style to frames...'
        style_frames()

        # Step 5: Generate Layout
        job_statuses[job_id]['progress'] = 80
        job_statuses[job_id]['message'] = 'Designing comic panel layout...'
        crop_coords, page_templates, panels = generate_layout()

        # Step 6: Create Speech Bubbles
        job_statuses[job_id]['progress'] = 90
        job_statuses[job_id]['message'] = 'Creating and placing speech bubbles...'
        bubbles = bubble_create(video_path, crop_coords, black_x, black_y)

        # Step 7: Assemble Final Comic
        job_statuses[job_id]['progress'] = 95
        job_statuses[job_id]['message'] = 'Assembling the final comic...'
        pages = page_create(page_templates,panels,bubbles)
        page_json(pages)
        copy_template()

        # Step 8: Done!
        job_statuses[job_id]['progress'] = 100
        job_statuses[job_id]['message'] = 'Success! Your comic is ready.'
        job_statuses[job_id]['result_url'] = '/output/page.html'
        
        print("--- Execution time : %s minutes ---" % ((time.time() - start_time) / 60))

    except Exception as e:
        print(f"Error during comic generation for job {job_id}: {e}")
        job_statuses[job_id]['progress'] = -1
        job_statuses[job_id]['message'] = f'An error occurred: {str(e)}'

@app.route('/start-job', methods=['POST'])
def start_job():
    cleanup()
    job_id = str(uuid.uuid4())
    video_path = ""
    job_statuses[job_id] = {'progress': 5, 'message': 'Initializing...'}

    if 'file' in request.files and request.files['file'].filename != '':
        video_file = request.files['file']
        video_path = os.path.join('video', 'uploaded.mp4')
        os.makedirs('video', exist_ok=True)
        video_file.save(video_path)
    elif 'link' in request.form and request.form['link'] != '':
        link = request.form['link']
        download_video(link)
        video_path = os.path.join('video', 'uploaded.mp4')
    else:
        return jsonify({'error': 'No file or link provided'}), 400

    thread = threading.Thread(target=run_comic_generation, args=(video_path, job_id))
    thread.start()
    
    return jsonify({'job_id': job_id})

@app.route('/progress/<job_id>')
def progress(job_id):
    def generate():
        last_progress = -2 
        while True:
            status = job_statuses.get(job_id, {})
            current_progress = status.get('progress', 0)
            
            if current_progress != last_progress:
                data_to_send = json.dumps(status)
                yield f"data: {data_to_send}\n\n"
                last_progress = current_progress

            if current_progress == 100 or current_progress == -1:
                break
            
            time.sleep(1)
            
    return Response(generate(), mimetype='text/event-stream')

@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        print(dict(request.form))  
        f = request.files['file']  #we got the file as file storage object from frontend
        print(type(f))
        cleanup()
        f.save("video/uploaded.mp4")
        copy_template()
        return "Comic created Successfully"
    

@app.route('/handle_link', methods=['GET', 'POST'])
def handle_link():
    if request.method == 'POST':
        print(dict(request.form))  
        link = request.form['link']
        cleanup()
        download_video(link)
        copy_template()
        return "Comic created Successfully"

@app.route('/download', methods=['GET'])
def download():
 # Path to the HTML file you want to convert
 html_file_path = os.path.join(os.getcwd(), 'output/page.html')
 
 # Path to the output PDF file
 pdf_file_path = os.path.join(os.getcwd(), 'output/comic_strip.pdf')
 
 # Convert HTML to PDF
 # You might need to install wkhtmltopdf and configure the path
 # Example: config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
 pdfkit.from_file(html_file_path, pdf_file_path)
 
 # Send the file to the client for download
 return send_file(pdf_file_path, as_attachment=True)

# Route to serve the generated comic and its assets
@app.route('/output/<path:filename>')
def output_static(filename):
    return send_from_directory('output', filename)

# Route to serve the frames directory
@app.route('/frames/<path:filename>')
def frames_static(filename):
    return send_from_directory('frames', filename)

 
if __name__ == "__main__":
    app.run(debug=False, threaded=True)     # at the end set it to false