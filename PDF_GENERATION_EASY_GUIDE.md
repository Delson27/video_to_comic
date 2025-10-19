# 🚀 Easy PDF Generation Guide

## Quick Start (3 Ways)

### Method 1: Double-Click (Windows) ✅ EASIEST
```
1. Open File Explorer
2. Navigate to: c:\Users\Deepak\Desktop\delson\video_to_comic\
3. Double-click: RUN_PDF_GENERATOR.bat
4. Wait for PDF to generate
5. Find PDF in: output/comic.pdf
```

### Method 2: Command Line
```bash
cd c:\Users\Deepak\Desktop\delson\video_to_comic
python generate_comic_pdf.py
```

### Method 3: From Python
```python
import asyncio
from generate_comic_pdf import convert_html_to_pdf_browser

asyncio.run(convert_html_to_pdf_browser(
    'output_template/page.html',
    'output/comic.pdf',
    jpeg_quality=85
))
```

---

## 🔧 Customizing Parameters

To change settings, edit `generate_comic_pdf.py` (lines 8-20):

```python
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
```

### Quality Options

| Quality | File Size | Best For |
|---------|-----------|----------|
| 75 | 0.4 MB | Web, quick sharing |
| **85** | **0.63 MB** | **General use (default)** |
| 90 | 0.9 MB | High-quality |
| 95 | 1.2 MB | Very high quality |
| 98 | 1.51 MB | Archival, professional |

### Changing Output Filename

**Example: Save to `output/comic_v2.pdf`**
```python
PDF_OUTPUT = "output/comic_v2.pdf"
```

**Example: Save to custom location**
```python
PDF_OUTPUT = "C:/My Documents/my_comic.pdf"
```

---

## 📋 What Each File Does

| File | Purpose |
|------|---------|
| `generate_comic_pdf.py` | 🌟 **Main script** - Run this or use RUN_PDF_GENERATOR.bat |
| `RUN_PDF_GENERATOR.bat` | 💻 **Windows shortcut** - Double-click to run |
| `generate_pdf.bat` | Advanced batch script with CLI options |
| `tools/html_to_pdf_browser.py` | Core converter (used by generate_comic_pdf.py) |

---

## ✅ Workflow

```
1. Edit generate_comic_pdf.py (optional)
   └─ Change quality, input, or output path

2. Run PDF generator (one of three ways)
   └─ Double-click RUN_PDF_GENERATOR.bat (easiest)
   └─ python generate_comic_pdf.py (command line)
   └─ Use from Python code (advanced)

3. PDF generated
   └─ Check: output/comic.pdf
   └─ View in any PDF reader

4. Done! ✨
```

---

## 🎯 Common Tasks

### Generate Standard PDF (Quality 85, 0.63 MB)
```bash
python generate_comic_pdf.py
```
_Just run as-is, all defaults are good._

### Generate High-Quality PDF (Quality 95, 1.2 MB)
1. Edit `generate_comic_pdf.py`
2. Change: `PDF_QUALITY = 95`
3. Save file
4. Run: `python generate_comic_pdf.py`

### Generate Small File (Quality 75, 0.4 MB)
1. Edit `generate_comic_pdf.py`
2. Change: `PDF_QUALITY = 75`
3. Save file
4. Run: `python generate_comic_pdf.py`

### Save to Different Location
1. Edit `generate_comic_pdf.py`
2. Change: `PDF_OUTPUT = "output/my_comic.pdf"`
3. Save file
4. Run: `python generate_comic_pdf.py`

---

## 📊 Expected Output

```
============================================================
🎬 Comic PDF Generator
============================================================

📋 Configuration:
   HTML Input:    C:\...\output_template\page.html
   PDF Output:    C:\...\output\comic.pdf
   Quality:       85%
   Dimensions:    3000x3000px
✓ Checking dependencies...
  ✓ Playwright installed
  ✓ Pillow and img2pdf installed

✓ All dependencies OK!

🌐 Loading HTML in Chromium browser...
   Opening: file:///C:/...
   Waiting for images to load...
   Page size: 3000x3000px
   Capturing screenshot...
✅ Screenshot captured: 2.76 MB (3000x3000px)

📕 Converting screenshot to PDF...
   Image mode: RGB
   Converted JPEG: 0.62 MB (quality 85)
✅ PDF created: 0.63 MB

============================================================
✅ SUCCESS!
   PDF generated: C:\...\output\comic.pdf
   File size: 0.63 MB
============================================================
```

---

## ⏱️ Processing Time

| Stage | Time |
|-------|------|
| Dependencies check | <1 sec |
| Browser startup | 2-3 sec |
| HTML loading | 1-2 sec |
| Screenshot capture | 2-3 sec |
| PDF conversion | <1 sec |
| **Total** | **~10-15 sec** |

---

## 🐛 Troubleshooting

### "Playwright not installed"
```bash
pip install playwright
python -m playwright install chromium
```

### "Pillow or img2pdf not installed"
```bash
pip install pillow img2pdf
```

### "HTML file not found"
- Check `HTML_INPUT` path in generate_comic_pdf.py
- Make sure file exists at: `output_template/page.html`

### "Output folder doesn't exist"
- The `output/` folder must exist
- If missing, create it manually or adjust `PDF_OUTPUT` path

### "PDF is too large/small"
- Edit `generate_comic_pdf.py`
- Change `PDF_QUALITY` value:
  - Larger (75-90): Smaller file
  - Higher (95-98): Larger file but better quality

### "Process takes too long"
- This is normal, takes 10-15 seconds
- Browser startup is the main delay
- First run may be slower (Chromium initialization)

---

## 💡 Pro Tips

### Batch Processing Multiple Files
Create a new Python file:
```python
import asyncio
import os
from generate_comic_pdf import convert_html_to_pdf_browser

async def batch_generate():
    files = [
        ('output_template/page.html', 'output/comic_v1.pdf'),
        ('output_template/page2.html', 'output/comic_v2.pdf'),
    ]
    
    for html, pdf in files:
        print(f"\nGenerating: {pdf}")
        await convert_html_to_pdf_browser(html, pdf, jpeg_quality=85)

asyncio.run(batch_generate())
```

### Generate with Different Settings
```python
# Save current settings
PDF_QUALITY = 85  # Default

# Generate standard version
python generate_comic_pdf.py

# Then manually change PDF_QUALITY to 95
# And regenerate for high-quality version
```

---

## 📞 Quick Reference

| Need | Do This |
|------|---------|
| Generate PDF quickly | Double-click `RUN_PDF_GENERATOR.bat` |
| Change quality | Edit `generate_comic_pdf.py` line 20 |
| Change output path | Edit `generate_comic_pdf.py` line 14 |
| Use from Python code | `from generate_comic_pdf import convert_html_to_pdf_browser` |
| Help with dependencies | `pip install -r requirements.txt` |
| Show all options | `python generate_pdf.bat --help` |

---

## ✨ Summary

**Easiest way to generate PDF:**
1. Double-click `RUN_PDF_GENERATOR.bat`
2. Wait ~15 seconds
3. Find PDF in `output/comic.pdf`
4. Done! 🎉

**To customize:**
1. Edit `generate_comic_pdf.py` (lines 8-20)
2. Save file
3. Double-click `RUN_PDF_GENERATOR.bat`
4. Done! 🎉

---

**Status: ✅ PRODUCTION READY - Simple one-click PDF generation**
