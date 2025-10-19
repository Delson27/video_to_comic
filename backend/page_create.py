from backend.class_def import Page,panel,bubble
import json
from fpdf import FPDF
from PIL import Image
import os
import shutil
from shutil import copyfile

def page_create(page_templates,panels,bubbles):
    count = 0
    pages = []
    for page_template in page_templates:

        new_page = Page(panels[count:count+len(page_template)],bubbles[count:count+len(page_template)])
        pages.append(new_page)
        count = count +len(page_template)
        print(new_page.__dict__)        

    return pages


def page_json(pages):
    pages_dict = []

    for page in pages:
        pages_dict.append(page.__dict__)

    with open('output_template/page.js', 'w') as f:
        f.write(f'var pages = ')
        json.dump(pages_dict, f , indent=4)

def generate_pdf_from_frames(frames_dir='frames/final', output_path='output/generated_comic.pdf', archive_path='output/gen_pdf.pdf'):
    """
    Generate a PDF from images in the specified directory and store a copy in the output folder.

    :param frames_dir: Directory containing the frame images.
    :param output_path: Path to save the generated PDF.
    :param archive_path: Path to store a copy of the generated PDF.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Get all PNG files in the directory, sorted alphabetically
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])

    for i in range(0, len(frame_files), 6):
        pdf.add_page()
        for j in range(6):
            if i + j < len(frame_files):
                frame_path = os.path.join(frames_dir, frame_files[i + j])
                x = 15 + (j % 2) * 100  # Adjust x position for 2 frames per row
                y = 20 + (j // 2) * 140  # Adjust y position for 3 rows per page
                pdf.image(frame_path, x=x, y=y, w=90, h=120)  # Larger size for better visibility

    pdf.output(output_path)
    print(f"PDF generated successfully at: {output_path}")

    # Store a copy in the output folder
    copyfile(output_path, archive_path)
    print(f"PDF copy stored at: {archive_path}")

    return output_path, archive_path

# Example usage
# generate_pdf_with_frames_v2('AutoComic/new_frames')