r"""
HTML to PDF Converter - Browser-based Rendering (Playwright)

This approach uses a real headless browser (Chromium) to:
1. Load the HTML page
2. Execute all JavaScript (page.js loads frames)
3. Wait for all images to load
4. Take a screenshot of the rendered content
5. Convert screenshot to PDF with high quality

This is more reliable than wkhtmltoimage as it properly handles:
- Dynamic JavaScript rendering
- Image loading
- CSS styling
- Network requests
"""

import argparse
import os
import sys
import json
import asyncio
from pathlib import Path

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    from PIL import Image
    import img2pdf
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


async def render_html_to_screenshot_with_browser(html_path, png_output_path, viewport_width=3000, viewport_height=3000):
    """
    Render HTML using Chromium browser and capture screenshot.
    Waits for all images to load before taking screenshot.
    """
    print(f"🌐 Loading HTML in Chromium browser...")
    
    if not HAS_PLAYWRIGHT:
        print("✗ Playwright not installed")
        return False
    
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
            print(f"✗ Screenshot file not created")
            return False
    
    except Exception as e:
        print(f"✗ Error rendering: {e}")
        return False


def screenshot_to_pdf(png_path, pdf_path, jpeg_quality=98):
    """
    Convert screenshot PNG to PDF using img2pdf.
    """
    print(f"📕 Converting screenshot to PDF...")
    
    if not HAS_PIL:
        print("✗ PIL not installed")
        return False
    
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
    """
    Main orchestration function.
    1. Render HTML via Chromium browser
    2. Convert screenshot to PDF
    """
    
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
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="Convert HTML to PDF using browser rendering (Playwright + Chromium)"
    )
    parser.add_argument('--html', required=True, help='Input HTML file path')
    parser.add_argument('--out', required=True, help='Output PDF file path')
    parser.add_argument('--width', type=int, default=3000, help='Viewport width in pixels (default: 3000)')
    parser.add_argument('--height', type=int, default=3000, help='Viewport height in pixels (default: 3000)')
    parser.add_argument('--quality', type=int, default=98, help='JPEG quality 1-100 (default: 98, nearly lossless)')
    
    args = parser.parse_args()
    
    # Convert to absolute paths
    html_path = os.path.abspath(args.html)
    pdf_path = os.path.abspath(args.out)
    
    print("🎬 HTML to PDF Converter (Browser-based)")
    print("=" * 50)
    print(f"\n📄 HTML Input: {html_path}")
    print(f"📕 PDF Output: {pdf_path}\n")
    
    if not HAS_PLAYWRIGHT:
        print("✗ Playwright is not installed")
        print("   Install with: pip install playwright")
        print("   Then install browser: python -m playwright install chromium")
        return False
    
    if not HAS_PIL:
        print("✗ Required packages not installed")
        print("   Install with: pip install pillow img2pdf")
        return False
    
    # Run async function
    success = asyncio.run(convert_html_to_pdf_browser(
        html_path, 
        pdf_path,
        viewport_width=args.width,
        viewport_height=args.height,
        jpeg_quality=args.quality
    ))
    
    if success:
        final_size = os.path.getsize(pdf_path) / 1024 / 1024
        print(f"\n✅ Final PDF size: {final_size:.2f} MB")
        print(f"✨ Success! Browser-rendered PDF is ready")
        return True
    else:
        print(f"\n✗ Failed to generate PDF")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
