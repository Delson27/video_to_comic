r"""
Render an HTML file to an image (PNG), optionally crop a snippet, then embed into a PDF.

Dependencies:
- wkhtmltoimage (part of wkhtmltopdf) must be installed and on PATH or set WKHTMLTOIMAGE_PATH env var.
- Python packages: pillow, fpdf
  Install with: pip install pillow fpdf

Usage example (PowerShell):
python tools/html_snippet_to_pdf.py --html output/page.html --out output/snippet.pdf

Optional snippet crop (pixels):
--crop x y width height

If wkhtmltoimage isn't available, the script will exit with a helpful message.
"""

import argparse
import os
import shutil
import subprocess
import sys
from PIL import Image
from fpdf import FPDF


def find_wkhtmltoimage():
    path = os.environ.get('WKHTMLTOIMAGE_PATH') or shutil.which('wkhtmltoimage')
    if path:
        return path
    # common Windows install path
    possible = os.path.join('C:\\Program Files\\wkhtmltopdf\\bin', 'wkhtmltoimage.exe')
    if os.path.exists(possible):
        return possible
    return None


def render_html_to_png(wkhtmltoimage, html_path, png_path, width=1200):
    # Ensure absolute paths so wkhtmltoimage can resolve local references
    html_abs = os.path.abspath(html_path)
    png_abs = os.path.abspath(png_path)

    cmd = [
        wkhtmltoimage,
        '--quality', '90',
        '--width', str(width),
        '--enable-local-file-access',
        html_abs,
        png_abs,
    ]
    try:
        # capture output so we can show the error messages if it fails
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        # include stdout/stderr in the raised error for easier debugging
        out = e.stdout or ''
        err = e.stderr or ''
        raise RuntimeError(f"wkhtmltoimage failed (retcode={e.returncode}). stdout:\n{out}\n\nstderr:\n{err}\nCommand: {' '.join(cmd)}")


def crop_image(src_png, cropped_png, crop_box):
    with Image.open(src_png) as im:
        cropped = im.crop(crop_box)
        cropped.save(cropped_png)


def image_to_pdf(image_path, pdf_path, page_size=(210, 297)):
    # page_size in mm (A4 default)
    pdf = FPDF(unit='mm', format=page_size)
    pdf.add_page()
    # calculate image display size preserving aspect ratio
    with Image.open(image_path) as im:
        img_w_px, img_h_px = im.size

    # convert page size mm -> px by assuming 96 DPI for sizing; we'll instead compute mm
    # FPDF places images by mm: to fit width of page minus margins
    margin = 10
    usable_w_mm = page_size[0] - 2 * margin
    usable_h_mm = page_size[1] - 2 * margin

    # Use PIL to get DPI if present, otherwise assume 96
    with Image.open(image_path) as im:
        dpi = im.info.get('dpi', (96, 96))[0]
        img_w_mm = img_w_px / dpi * 25.4
        img_h_mm = img_h_px / dpi * 25.4

    # Scale to fit within usable area
    scale = min(usable_w_mm / img_w_mm, usable_h_mm / img_h_mm, 1.0)
    disp_w = img_w_mm * scale
    disp_h = img_h_mm * scale
    x = (page_size[0] - disp_w) / 2
    y = (page_size[1] - disp_h) / 2

    pdf.image(image_path, x=x, y=y, w=disp_w, h=disp_h)
    pdf.output(pdf_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', required=True, help='Path to input HTML file')
    parser.add_argument('--out', required=True, help='Path to output PDF')
    parser.add_argument('--tmp', default='tools/tmp_render.png', help='Temporary PNG path')
    parser.add_argument('--crop', nargs=4, type=int, metavar=('X','Y','W','H'), help='Crop box in pixels')
    parser.add_argument('--width', type=int, default=1200, help='Render width in pixels')
    args = parser.parse_args()

    html_path = args.html
    out_pdf = args.out
    tmp_png = args.tmp
    cropped_png = tmp_png.replace('.png', '.crop.png')

    if not os.path.exists(html_path):
        print(f"HTML file not found: {html_path}")
        sys.exit(1)

    wk = find_wkhtmltoimage()
    if not wk:
        print("wkhtmltoimage not found. Install wkhtmltopdf and ensure wkhtmltoimage is on PATH or set WKHTMLTOIMAGE_PATH env var.")
        sys.exit(1)

    os.makedirs(os.path.dirname(tmp_png), exist_ok=True)

    print(f"Rendering {html_path} -> {tmp_png} using {wk} ...")
    render_html_to_png(wk, html_path, tmp_png, width=args.width)

    final_image = tmp_png
    if args.crop:
        x,y,w,h = args.crop
        print(f"Cropping to box x={x},y={y},w={w},h={h}")
        crop_image(tmp_png, cropped_png, (x,y,x+w,y+h))
        final_image = cropped_png

    print(f"Embedding {final_image} into PDF {out_pdf} ...")
    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)
    image_to_pdf(final_image, out_pdf)

    print("Done. Output:", out_pdf)

if __name__ == '__main__':
    main()
