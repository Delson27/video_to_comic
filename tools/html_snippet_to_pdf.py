r"""
HTML to PDF Converter - Using PyHTML2PDF

Convert HTML files directly to PDF with all resources (CSS, JS, images) preserved.

Dependencies:
- Python packages: pdfkit, pillow
  Install with: pip install pdfkit pillow
- wkhtmltopdf system tool
  Windows: choco install wkhtmltopdf
  Linux: sudo apt-get install wkhtmltopdf
  macOS: brew install wkhtmltopdf

Usage:
python tools/html_snippet_to_pdf.py --html output_template/page.html --out output/comic.pdf
"""

import argparse
import os
import sys
import re

try:
    import pdfkit
    HAS_PDFKIT = True
except ImportError:
    HAS_PDFKIT = False
    print("⚠ pdfkit not installed. Install with: pip install pdfkit")

try:
    from bs4 import BeautifulSoup
    HAS_BEAUTIFULSOUP = True
except ImportError:
    HAS_BEAUTIFULSOUP = False


def fix_javascript_paths(html_content, base_html_path):
    """
    Fix JavaScript paths to use absolute paths for image loading.
    Also embeds external scripts inline with fixed paths.
    
    Args:
        html_content: HTML content as string
        base_html_path: Path to the HTML file
    
    Returns:
        Updated HTML content with fixed paths and embedded scripts
    """
    if not HAS_BEAUTIFULSOUP:
        return html_content
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        base_dir = os.path.dirname(os.path.abspath(base_html_path))
        
        # Find the path to frames/final directory
        frames_final_path = os.path.join(os.path.dirname(base_dir), 'frames', 'final')
        frames_final_path = os.path.normpath(frames_final_path)
        
        if not os.path.exists(frames_final_path):
            print(f"⚠ Frames directory not found: {frames_final_path}")
        else:
            print(f"✓ Found frames directory: {frames_final_path}")
        
        # Convert path for use in JavaScript (just forward slashes)
        js_frames_path = frames_final_path.replace('\\', '/')
        
        # Find and process all script tags
        for script in soup.find_all('script'):
            src = script.get('src')
            
            if src:
                # External script - read and embed it inline
                script_path = os.path.join(base_dir, src)
                if os.path.exists(script_path):
                    try:
                        with open(script_path, 'r', encoding='utf-8') as f:
                            script_content = f.read()
                        
                        # Fix the path variable in the script
                        if 'path = "../frames/final/"' in script_content:
                            script_content = script_content.replace(
                                'path = "../frames/final/"',
                                f'path = "{js_frames_path}/"'
                            )
                            print(f"✓ Fixed {src}: path → {js_frames_path}/")
                        
                        # Create new inline script tag
                        new_script = soup.new_tag('script')
                        new_script.string = script_content
                        script.replace(new_script)
                        print(f"✓ Embedded script: {src}")
                        
                    except Exception as e:
                        print(f"⚠ Could not embed script {src}: {e}")
            else:
                # Inline script - modify if it contains path references
                if script.string:
                    script_content = script.string
                    if 'path = "../frames/final/"' in script_content:
                        script_content = script_content.replace(
                            'path = "../frames/final/"',
                            f'path = "{js_frames_path}/"'
                        )
                        script.string = script_content
                        print(f"✓ Fixed inline script path → {js_frames_path}/")
        
        # Also fix any static <img> src attributes
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and not src.startswith(('http://', 'https://', 'data:', 'file://')):
                # Convert relative path to absolute
                abs_path = os.path.normpath(os.path.join(base_dir, src))
                if os.path.exists(abs_path):
                    abs_path_url = abs_path.replace('\\', '/')
                    img['src'] = abs_path_url
                    print(f"✓ Fixed img src: {src} → {abs_path_url}")
        
        return str(soup.prettify())
    
    except Exception as e:
        print(f"⚠ Error fixing paths: {e}")
        import traceback
        traceback.print_exc()
        return html_content


def find_wkhtmltopdf():
    """Find wkhtmltopdf executable in common installation paths."""
    # Common Windows installation paths
    possible_paths = [
        r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
        r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
        r'C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe',
        r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltoimage.exe',
    ]
    
    # Check environment variable
    env_path = os.environ.get('WKHTMLTOPDF_PATH')
    if env_path and os.path.exists(env_path):
        return env_path
    
    # Check PATH
    from shutil import which
    if which('wkhtmltopdf'):
        return which('wkhtmltopdf')
    
    # Check common installation paths
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def convert_html_to_pdf_simple(html_path, pdf_path, options=None):
    """
    Simple direct conversion of HTML to PDF preserving all resources.
    
    Args:
        html_path: Path to HTML file
        pdf_path: Path to output PDF
        options: pdfkit options dict
    """
    if not HAS_PDFKIT:
        print("✗ pdfkit not installed")
        print("  Install with: pip install pdfkit")
        sys.exit(1)
    
    # Find wkhtmltopdf
    wkhtmltopdf_path = find_wkhtmltopdf()
    if not wkhtmltopdf_path:
        print("✗ wkhtmltopdf not found in PATH or common installation locations")
        print("  Please install it from: https://wkhtmltopdf.org/")
        print("  Or set WKHTMLTOPDF_PATH environment variable")
        sys.exit(1)
    
    print(f"✓ Found wkhtmltopdf: {wkhtmltopdf_path}")
    
    # Default options
    if options is None:
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None,
        }
    
    try:
        # Get absolute path
        html_abs = os.path.abspath(html_path)
        pdf_abs = os.path.abspath(pdf_path)
        
        print(f"📄 HTML Input: {html_abs}")
        print(f"📕 PDF Output: {pdf_abs}")
        
        # Read HTML and fix all image paths
        print(f"🔧 Fixing image paths...")
        with open(html_abs, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        fixed_html = fix_javascript_paths(html_content, html_abs)
        
        # Save fixed HTML to temp file
        temp_html = pdf_abs.replace('.pdf', '.temp.html')
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(fixed_html)
        
        print(f"⏳ Converting... (this may take a moment)")
        
        # Convert with explicit wkhtmltopdf path
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        pdfkit.from_file(temp_html, pdf_abs, options=options, configuration=config)
        
        # Clean up temp file
        if os.path.exists(temp_html):
            os.remove(temp_html)
        
        print(f"✅ Done! PDF saved: {pdf_abs}")
        print(f"📊 File size: {os.path.getsize(pdf_abs) / 1024 / 1024:.2f} MB")
        
        return True
    
    except Exception as e:
        print(f"✗ Error converting HTML to PDF: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert HTML file to PDF (preserves all resources)'
    )
    parser.add_argument('--html', required=True, help='Path to input HTML file')
    parser.add_argument('--out', required=True, help='Path to output PDF file')
    parser.add_argument('--landscape', action='store_true', help='Use landscape orientation')
    parser.add_argument('--margin', type=float, default=0.75, help='Page margin in inches')
    
    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.html):
        print(f"✗ HTML file not found: {args.html}")
        sys.exit(1)
    
    # Prepare output directory
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    
    # Setup options
    options = {
        'page-size': 'A3' if args.landscape else 'A4',
        'orientation': 'Landscape' if args.landscape else 'Portrait',
        'margin-top': f'{args.margin}in',
        'margin-right': f'{args.margin}in',
        'margin-bottom': f'{args.margin}in',
        'margin-left': f'{args.margin}in',
        'encoding': 'UTF-8',
        'no-outline': None,
        'enable-local-file-access': None,
    }
    
    print("🎬 HTML to PDF Converter")
    print("=" * 50)
    print()
    
    # Convert
    success = convert_html_to_pdf_simple(args.html, args.out, options)
    
    if success:
        print()
        print("✨ Success! Your comic is ready as PDF")
        sys.exit(0)
    else:
        print()
        print("❌ Conversion failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
