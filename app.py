import os
import shutil
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
from backend.speech_bubble.bubble import bubble_create
from backend.page_create import page_create,page_json
from backend.utils import cleanup, download_video
from backend.utils import copy_template

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

        # Step 4: Generate Layout
        job_statuses[job_id]['progress'] = 70
        job_statuses[job_id]['message'] = 'Designing comic panel layout...'
        crop_coords, page_templates, panels = generate_layout()

        # Step 5: Create Speech Bubbles
        job_statuses[job_id]['progress'] = 85
        job_statuses[job_id]['message'] = 'Creating and placing speech bubbles...'
        bubbles = bubble_create(video_path, crop_coords, black_x, black_y)

        # Step 6: Assemble Final Comic
        job_statuses[job_id]['progress'] = 95
        job_statuses[job_id]['message'] = 'Assembling the final comic...'
        pages = page_create(page_templates,panels,bubbles)
        page_json(pages)
        copy_template()

        # Done!
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
        try:
            download_video(link)
            video_path = os.path.join('video', 'uploaded.mp4')
        except Exception as e:
            error_msg = str(e)
            if 'player response' in error_msg.lower():
                return jsonify({'error': 'YouTube download failed. Try: 1) Using a different video 2) Uploading the video file directly instead'}), 400
            elif 'private' in error_msg.lower() or 'unavailable' in error_msg.lower():
                return jsonify({'error': 'Video is private or unavailable. Please use a public video.'}), 400
            else:
                return jsonify({'error': f'Download failed: {error_msg}'}), 400
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

# Route to serve the generated comic and its assets
@app.route('/output/<path:filename>')
def output_static(filename):
    return send_from_directory('output', filename)

# Route to serve the frames directory
@app.route('/frames/<path:filename>')
def frames_static(filename):
    return send_from_directory('frames', filename)

async def render_html_to_pdf_async(html_path, pdf_path, viewport_width=3000, viewport_height=3000, jpeg_quality=85):
    """
    Render HTML to PDF using Playwright (headless Chromium).
    This handles JavaScript execution and captures ALL comic pages into a single PDF.
    """
    try:
        from playwright.async_api import async_playwright
        from PIL import Image
        import img2pdf
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}. Install with: pip install playwright pillow img2pdf && playwright install chromium")
    
    from pathlib import Path
    
    print(f"Rendering HTML to PDF: {html_path} -> {pdf_path}")
    
    temp_images = []
    
    try:
        # Step 1: Render ALL pages to screenshots using Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height}
            )
            page = await context.new_page()
            
            # Convert file path to file:// URL
            file_url = Path(html_path).resolve().as_uri()
            print(f"Opening: {file_url}")
            
            # Navigate and wait for page to load
            await page.goto(file_url, wait_until="networkidle")
            
            # Wait for images and JavaScript to complete
            await page.evaluate("""
                async () => {
                    const images = Array.from(document.querySelectorAll('img'));
                    await Promise.all(images.map(img => {
                        return new Promise(resolve => {
                            if (img.complete) resolve();
                            else {
                                img.onload = resolve;
                                img.onerror = resolve;
                            }
                        });
                    }));
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            """)
            
            # Get the total number of pages from the JavaScript variable
            num_pages = await page.evaluate("() => typeof pages !== 'undefined' ? pages.length : 1")
            print(f"Found {num_pages} comic pages to render")
            
            # Render each page
            for page_idx in range(num_pages):
                print(f"Rendering page {page_idx + 1}/{num_pages}...")
                
                # Navigate to specific page by calling the JavaScript function
                if page_idx > 0:
                    await page.evaluate(f"() => {{ current_page = {page_idx}; placeDialogs(pages[current_page]); }}")
                    await page.wait_for_timeout(500)  # Wait for page to render
                
                # Take screenshot of ONLY the comic wrapper (exclude navigation buttons and background)
                temp_png = pdf_path.replace('.pdf', f'.temp_page_{page_idx}.png')
                temp_images.append(temp_png)
                
                # Get the wrapper element and screenshot only that area
                wrapper = await page.query_selector('.wrapper')
                if wrapper:
                    await wrapper.screenshot(path=temp_png)
                else:
                    # Fallback to full page if wrapper not found
                    print(f"Warning: .wrapper not found, using full page screenshot")
                    await page.screenshot(path=temp_png, full_page=True)
            
            await context.close()
            await browser.close()
        
        # Step 2: Convert all PNGs to JPEGs and combine into single PDF
        print(f"Combining {len(temp_images)} pages into PDF...")
        temp_jpgs = []
        
        for i, temp_png in enumerate(temp_images):
            img = Image.open(temp_png)
            
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPEG
            temp_jpg = temp_png.replace('.png', '.jpg')
            temp_jpgs.append(temp_jpg)
            img.save(temp_jpg, 'JPEG', quality=jpeg_quality, optimize=False)
            img.close()
        
        # Convert all JPEGs to a single PDF
        with open(pdf_path, 'wb') as f:
            f.write(img2pdf.convert([open(jpg, 'rb').read() for jpg in temp_jpgs]))
        
        # Cleanup temp files
        for temp_file in temp_images + temp_jpgs:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        file_size_mb = os.path.getsize(pdf_path) / 1024 / 1024
        print(f"PDF generated successfully: {pdf_path} ({file_size_mb:.2f} MB, {num_pages} pages)")
        return pdf_path
    
    except Exception as e:
        # Cleanup on error
        for temp_file in temp_images:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            jpg_file = temp_file.replace('.png', '.jpg')
            if os.path.exists(jpg_file):
                os.remove(jpg_file)
        raise RuntimeError(f"PDF generation failed: {e}")

def generate_comic_pdf_sync(html_path='output/page.html', pdf_path='output/comic.pdf'):
    """Synchronous wrapper for async PDF generation."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(render_html_to_pdf_async(html_path, pdf_path))
        return result
    finally:
        loop.close()

@app.route('/generate-pdf', methods=['GET'])
def generate_pdf_endpoint():
    try:
        html_path = os.path.join('output', 'page.html')
        pdf_path = os.path.join('output', 'comic.pdf')
        
        if not os.path.exists(html_path):
            return jsonify({"error": "Comic HTML not found. Please generate the comic first."}), 404
        
        output_path = generate_comic_pdf_sync(html_path, pdf_path)
        
        # Send the PDF file for download
        return send_file(
            output_path,
            as_attachment=True,
            download_name='comic_strip.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, threaded=True)     # at the end set it to false