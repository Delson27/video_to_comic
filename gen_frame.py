from flask import Flask, jsonify
from fpdf import FPDF
import os

app = Flask(__name__)

def generate_pdf_from_frames(frames_dir='frames/final', output_path='output/generated_comic.pdf'):
    """
    Generate a PDF from images in the specified directory, including dialog bubbles.

    :param frames_dir: Directory containing the frame images.
    :param output_path: Path to save the generated PDF.
    """
    from backend.speech_bubble.bubble_placement import get_bubble_position
    from backend.speech_bubble.bubble_shape import get_bubble_type
    from backend.speech_bubble.bubble import bubble_create

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Get all PNG files in the directory, sorted alphabetically
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])

    # Example crop_coords and CAM_data (replace with actual data loading logic)
    crop_coords = [(0, 100, 0, 100)] * len(frame_files)  # Placeholder crop coordinates
    CAM_data = [{"x_": 1, "y_": 1, "ten_map": [[0] * 100 for _ in range(100)]}] * len(frame_files)

    # Generate bubbles dynamically
    bubbles = bubble_create("video/uploaded.mp4", crop_coords, 0, 0)

    for i, frame_file in enumerate(frame_files):
        if i % 6 == 0:
            pdf.add_page()

        frame_path = os.path.join(frames_dir, frame_file)
        x = 15 + (i % 2) * 100  # Adjust x position for 2 frames per row
        y = 20 + ((i // 2) % 3) * 140  # Adjust y position for 3 rows per page
        pdf.image(frame_path, x=x, y=y, w=90, h=120)  # Larger size for better visibility

        # Add dialog bubble
        if i < len(bubbles):
            bubble = bubbles[i]
            pdf.set_xy(x + bubble.bubble_x, y + bubble.bubble_y)
            pdf.set_fill_color(255, 255, 255)  # White background
            pdf.set_text_color(0, 0, 0)  # Black text
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(50, 10, bubble.dialog, border=1, fill=True)

            # Add tail (simplified as a line for now)
            if bubble.lip_x != -1 and bubble.lip_y != -1:
                tail_x = x + bubble.bubble_x + (bubble.lip_x - bubble.bubble_x) / 2
                tail_y = y + bubble.bubble_y + (bubble.lip_y - bubble.bubble_y) / 2
                pdf.line(x + bubble.bubble_x, y + bubble.bubble_y, tail_x, tail_y)

    pdf.output(output_path)
    print(f"PDF generated successfully at: {output_path}")
    return output_path

@app.route('/generate-pdf', methods=['GET'])
def generate_pdf_endpoint():
    try:
        output_path = generate_pdf_from_frames()
        return jsonify({"message": "PDF generated successfully", "path": output_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Example usage
if __name__ == "__main__":
    app.run(debug=True)