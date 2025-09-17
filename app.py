
import os
import shutil
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
    try:
        output_dir = os.path.join(os.getcwd(), 'output')
        source_html_path = os.path.join(output_dir, 'page.html')
        pdf_file_path = os.path.join(output_dir, 'comic_strip.pdf')
        print_html_path = os.path.join(output_dir, 'print.html')

        if not os.path.exists(source_html_path):
            return jsonify({'error': 'page.html not found. Generate the comic first.'}), 404

        # Find wkhtmltopdf binary
        wkhtml_path = os.environ.get('WKHTMLTOPDF_PATH') or shutil.which('wkhtmltopdf')
        if not wkhtml_path:
            # Common Windows install path
            possible_path = os.path.join('C:\\Program Files\\wkhtmltopdf\\bin', 'wkhtmltopdf.exe')
            if os.path.exists(possible_path):
                wkhtml_path = possible_path

        if not wkhtml_path:
            return jsonify({'error': 'wkhtmltopdf not found. Install it and/or set WKHTMLTOPDF_PATH env var.'}), 500

        config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

        options = {
            'enable-local-file-access': None,
            'quiet': '',
            'javascript-delay': '1500',
            'load-error-handling': 'ignore',
            'no-stop-slow-scripts': None,
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-right': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
        }

        # Create a minimal print-only HTML that renders all comic pages without UI controls
        # Build absolute file URL to frames to ensure wkhtmltopdf can load images
        frames_dir = os.path.abspath(os.path.join(os.getcwd(), 'AutoComic', 'frames', 'final'))
        if not os.path.exists(frames_dir):
            # Fallback to project-level frames path
            frames_dir = os.path.abspath(os.path.join(os.getcwd(), 'frames', 'final'))
        frames_url = 'file:///' + frames_dir.replace('\\', '/') + '/'

        print_html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>Comic Strip Print</title>
  <link rel=\"stylesheet\" href=\"page.css\">\n<link rel=\"stylesheet\" href=\"bubble.css\">
  <style>
    /* Hide navigation/buttons and background for print */
    body { background: none !important; }
    .button { display: none !important; }
    /* Ensure each wrapper becomes its own PDF page */
    .wrapper { page-break-after: always; max-width: 100%; margin: 0 auto; }
    .wrapper:last-of-type { page-break-after: auto; }
  </style>
  <script src=\"page.js\"></script>
  <script src=\"page_place.js\"></script>
  <script>
    // Force absolute path for frames to ensure images load in wkhtmltopdf
    window.path = '__FRAMES_URL__';
    document.addEventListener('DOMContentLoaded', function() {
      // Render all pages sequentially
      var container = document.body;
      for (var p = 0; p < pages.length; p++) {
        var wrap = document.createElement('div');
        wrap.className = 'wrapper';
        var grid = document.createElement('div');
        grid.className = 'grid-container';
        for (var i = 1; i <= 12; i++) {
          var gi = document.createElement('div');
          gi.className = 'grid-item';
          gi.id = '_' + i + '_p' + (p+1);
          grid.appendChild(gi);
        }
        wrap.appendChild(grid);
        container.appendChild(wrap);

        // Temporarily replace query selectors to target this wrapper
        (function(pageIndex, gridEl){
          var origQuery = document.querySelector;
          var origQueryAll = document.querySelectorAll;
          document.querySelector = function(sel){ if(sel === '.grid-container') return gridEl; return origQuery.call(document, sel); }
          document.querySelectorAll = function(sel){ if(sel === '.grid-item') return gridEl.querySelectorAll('.grid-item'); return origQueryAll.call(document, sel); }
          try { placeDialogs(pages[pageIndex]); } finally { document.querySelector = origQuery; document.querySelectorAll = origQueryAll; }
        })(p, grid);
      }
    });
  </script>
</head>
<body></body>
</html>"""

        # Inject frames url placeholder to avoid f-string brace escaping issues
        print_html = print_html.replace('__FRAMES_URL__', frames_url)

        with open(print_html_path, 'w', encoding='utf-8') as f:
            f.write(print_html)

        pdfkit.from_file(print_html_path, pdf_file_path, configuration=config, options=options)

        if not os.path.exists(pdf_file_path):
            return jsonify({'error': 'Failed to generate PDF.'}), 500

        return send_file(pdf_file_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500

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