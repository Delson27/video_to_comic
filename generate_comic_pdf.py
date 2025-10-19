#!/usr/bin/env python3
"""
Comic PDF Generator - Simple Runner
Just run: python generate_comic_pdf.py

All parameters defined here - no command line args needed!
"""

import asyncio
import os
import sys
from pathlib import Path

# ============================================
# CONFIGURATION - Edit these to change behavior
# ============================================

# Input HTML file
HTML_INPUT = "output_template/page.html"

# Output PDF file
PDF_OUTPUT = "output/comic.pdf"

# JPEG quality (1-100)
# 75  = small file, good web quality
# 85  = balanced (recommended)
# 95  = high quality
# 98  = nearly lossless
PDF_QUALITY = 85

# Rendering dimensions (in pixels)
RENDER_WIDTH = 3000
RENDER_HEIGHT = 3000

# ============================================
# END OF CONFIGURATION
# ============================================


def check_dependencies():
    """Check if required packages are installed."""
    print("✓ Checking dependencies...")
    
    try:
        from playwright.async_api import async_playwright
        print("  ✓ Playwright installed")
    except ImportError:
        print("  ✗ Playwright NOT installed")
        print("\n  Install with: pip install playwright")
        print("  Then install browser: python -m playwright install chromium")
        return False
    
    try:
        from PIL import Image
        import img2pdf
        print("  ✓ Pillow and img2pdf installed")
    except ImportError:
        print("  ✗ Required packages NOT installed")
        print("\n  Install with: pip install pillow img2pdf")
        return False
    
    return True


async def render_html_to_screenshot_with_browser(html_path, png_output_path, viewport_width=3000, viewport_height=3000):
    """Render HTML using Chromium browser and capture screenshot."""
    from playwright.async_api import async_playwright
    from PIL import Image
    
    print(f"\n🌐 Loading HTML in Chromium browser...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height}
            )
            page = await context.new_page()
            
            # Convert file path to file:// URL
            file_url = Path(html_path).as_uri()
            print(f"   Opening: {file_url}")
            
            # Navigate to page
            await page.goto(file_url, wait_until="networkidle")
            
            # Wait for images to load
            print(f"   Waiting for images to load...")
            await page.evaluate("""
                async () => {
                    // Wait for all images to load
                    const images = Array.from(document.querySelectorAll('img'));
                    await Promise.all(images.map(img => {
                        return new Promise(resolve => {
                            if (img.complete) {
                                resolve();
                            } else {
                                img.onload = resolve;
                                img.onerror = resolve;
                            }
                        });
                    }));
                    
                    // Also wait for background images to load
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            """)
            
            # Get the full page height
            body_height = await page.evaluate("() => document.body.scrollHeight")
            print(f"   Page size: {viewport_width}x{body_height}px")
            
            # Take screenshot
            print(f"   Capturing screenshot...")
            await page.screenshot(path=png_output_path, full_page=True)
            
            await context.close()
            await browser.close()
        
        if os.path.exists(png_output_path):
            file_size_mb = os.path.getsize(png_output_path) / 1024 / 1024
            img = Image.open(png_output_path)
            print(f"✅ Screenshot captured: {file_size_mb:.2f} MB ({img.size[0]}x{img.size[1]}px)")
            img.close()
            return True
        else:
            print(f"✗ PNG file not created")
            return False
    
    except Exception as e:
        print(f"✗ Error rendering: {e}")
        return False


def screenshot_to_pdf(png_path, pdf_path, jpeg_quality=98):
    """Convert screenshot PNG to PDF using img2pdf."""
    from PIL import Image
    import img2pdf
    
    print(f"\n📕 Converting screenshot to PDF...")
    
    try:
        # Load image and convert RGBA to RGB
        img = Image.open(png_path)
        print(f"   Image mode: {img.mode}")
        
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as high-quality JPEG
        temp_jpg_path = png_path.replace('.png', '.temp.jpg')
        img.save(temp_jpg_path, 'JPEG', quality=jpeg_quality, optimize=False)
        temp_size_mb = os.path.getsize(temp_jpg_path) / 1024 / 1024
        print(f"   Converted JPEG: {temp_size_mb:.2f} MB (quality {jpeg_quality})")
        
        # Convert JPEG to PDF using img2pdf
        with open(temp_jpg_path, 'rb') as f:
            pdf_bytes = img2pdf.convert(f.read())
        
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        
        # Cleanup
        if os.path.exists(temp_jpg_path):
            os.remove(temp_jpg_path)
        
        file_size_mb = os.path.getsize(pdf_path) / 1024 / 1024
        print(f"✅ PDF created: {file_size_mb:.2f} MB")
        
        return True
    
    except Exception as e:
        print(f"✗ Error converting to PDF: {e}")
        return False


async def convert_html_to_pdf_browser(html_path, pdf_path, viewport_width=3000, viewport_height=3000, jpeg_quality=98):
    """Main orchestration function."""
    
    if not os.path.exists(html_path):
        print(f"✗ HTML file not found: {html_path}")
        return False
    
    # Create temporary files
    temp_png = pdf_path.replace('.pdf', '.temp.png')
    
    try:
        # Step 1: Render to screenshot
        if not await render_html_to_screenshot_with_browser(html_path, temp_png, viewport_width, viewport_height):
            return False
        
        # Step 2: Convert to PDF
        if not screenshot_to_pdf(temp_png, pdf_path, jpeg_quality):
            return False
        
        # Cleanup
        if os.path.exists(temp_png):
            os.remove(temp_png)
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Main entry point."""
    
    print("\n" + "=" * 60)
    print("🎬 Comic PDF Generator")
    print("=" * 60)
    
    # Convert to absolute paths
    html_path = os.path.abspath(HTML_INPUT)
    pdf_path = os.path.abspath(PDF_OUTPUT)
    
    print(f"\n📋 Configuration:")
    print(f"   HTML Input:    {html_path}")
    print(f"   PDF Output:    {pdf_path}")
    print(f"   Quality:       {PDF_QUALITY}%")
    print(f"   Dimensions:    {RENDER_WIDTH}x{RENDER_HEIGHT}px")
    
    # Check dependencies
    if not check_dependencies():
        print("\n✗ Dependencies missing! Please install them first.")
        return False
    
    print("\n✓ All dependencies OK!")
    
    # Run conversion
    try:
        success = asyncio.run(convert_html_to_pdf_browser(
            html_path, 
            pdf_path,
            viewport_width=RENDER_WIDTH,
            viewport_height=RENDER_HEIGHT,
            jpeg_quality=PDF_QUALITY
        ))
        
        if success:
            final_size = os.path.getsize(pdf_path) / 1024 / 1024
            print(f"\n" + "=" * 60)
            print(f"✅ SUCCESS!")
            print(f"   PDF generated: {pdf_path}")
            print(f"   File size: {final_size:.2f} MB")
            print("=" * 60 + "\n")
            return True
        else:
            print("\n✗ Failed to generate PDF")
            return False
    
    except KeyboardInterrupt:
        print("\n\n✗ Cancelled by user")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
