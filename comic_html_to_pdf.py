#!/usr/bin/env python
"""
Quick Integration Script for HTML Comic to PDF Conversion
Automatically converts output/page.html to PDF with smart defaults
"""

import os
import sys
import subprocess
from pathlib import Path

def run_html_to_pdf(
    html_file="output/page.html",
    pdf_file="output/comic.pdf",
    selector=".comic-content",
    width=1600,
    quality=95,
    crop=None
):
    """
    Quickly convert comic HTML to PDF
    
    Args:
        html_file: Input HTML file
        pdf_file: Output PDF file
        selector: CSS selector for content extraction
        width: Render width in pixels
        quality: Image quality (1-100)
        crop: Optional crop tuple (x, y, width, height)
    """
    script_path = "tools/html_snippet_to_pdf.py"
    
    # Build command
    cmd = [
        sys.executable,
        script_path,
        "--html", html_file,
        "--out", pdf_file,
        "--width", str(width),
        "--quality", str(quality),
    ]
    
    # Add selector if provided
    if selector:
        cmd.extend(["--selector", selector])
    
    # Add crop if provided
    if crop:
        x, y, w, h = crop
        cmd.extend(["--crop", str(x), str(y), str(w), str(h)])
    
    # Run command
    print(f"Converting: {html_file} → {pdf_file}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd)
    return result.returncode == 0

def main():
    """Main conversion routine"""
    
    # Check if comic has been generated
    if not os.path.exists("output/page.html"):
        print("❌ Comic HTML not found: output/page.html")
        print("Please run the video-to-comic pipeline first:")
        print("  python -m flask --app app run")
        print("Or:")
        print("  python main.py")
        sys.exit(1)
    
    print("🎬 Video to Comic - HTML to PDF Converter")
    print("=" * 50)
    print()
    
    # Try different conversion options
    print("Converting comic to PDF...")
    print()
    
    # Option 1: Try with selector first (extracts main content)
    print("Option 1: Extract main content")
    success = run_html_to_pdf(
        selector=".comic-content",  # or adjust to your HTML structure
        quality=95
    )
    
    if success:
        print()
        print("✅ Success! Comic PDF created: output/comic.pdf")
        print()
        print("Other options you can try:")
        print()
        print("  # High quality (large file)")
        print("  python -c \"from comic_html_to_pdf import run_html_to_pdf; run_html_to_pdf(quality=100)\"")
        print()
        print("  # Full page, no selector")
        print("  python -c \"from comic_html_to_pdf import run_html_to_pdf; run_html_to_pdf(selector=None)\"")
        print()
        print("  # Specific crop area")
        print("  python -c \"from comic_html_to_pdf import run_html_to_pdf; run_html_to_pdf(crop=(100, 100, 800, 600))\"")
        print()
        return 0
    else:
        print()
        print("⚠️ First attempt failed, trying without selector...")
        print()
        
        # Option 2: Try without selector
        success = run_html_to_pdf(selector=None, quality=95)
        
        if success:
            print()
            print("✅ Success! Comic PDF created: output/comic.pdf")
            return 0
        else:
            print()
            print("❌ Conversion failed")
            print("Try manual conversion with more options:")
            print()
            print("  python tools/html_snippet_to_pdf.py \\")
            print("    --html output/page.html \\")
            print("    --out output/comic.pdf \\")
            print("    --width 1600 \\")
            print("    --quality 95 \\")
            print("    --keep-tmp")
            print()
            return 1

if __name__ == '__main__':
    sys.exit(main())
