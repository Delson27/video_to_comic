import os
from os import listdir
from backend.panel_layout.cam import get_coordinates
from backend.utils import crop_image
from backend.panel_layout.layout.page import get_templates, panel_create
from backend.utils import get_panel_type, types
from PIL import Image


def centroid_crop(index, img_w, img_h):
    """
    Simplified cropping - uses full frame dimensions.
    cam_coords parameter removed as it was unused.
    
    Args:
        index: Frame index
        img_w: Image width
        img_h: Image height
        
    Returns:
        Crop coordinates for the full frame
    """
    # Use full frame dimensions (no cropping)
    crop_left = 0
    crop_right = img_w
    crop_top = 0
    crop_bottom = img_h

    frame_path = os.path.join("frames", 'final', f"frame{index+1:03d}.png")
    crop_coords = crop_image(frame_path, crop_left, crop_right, crop_top, crop_bottom)
    return crop_coords


def generate_layout():
    """
    Generate comic page layout from keyframes.
    Simplified to use full frames without CAM-based ROI cropping.
    """
    input_seq = ""
    
    # Get dimensions of images
    img = Image.open(os.path.join("frames", 'final', f"frame001.png"))
    width, height = img.size

    # Loop through images and get panel type based on dimensions
    folder_dir = "frames/final"
    for image in os.listdir(folder_dir):
        frame_path = os.path.join("frames", 'final', image)
        # get_coordinates now returns full frame bounds
        left, right, top, bottom = get_coordinates(frame_path)
        input_seq += get_panel_type(left, right, top, bottom)

    page_templates = get_templates(input_seq)
    print(page_templates)
    
    # Generate crop coordinates for each panel
    i = 0
    crop_coords = []
    try:
        for page in page_templates:
            for panel in page:
                # Use full frame dimensions for each panel
                origin = centroid_crop(i, width, height)
                crop_coords.append(origin)
                i += 1
    except(IndexError):
        pass

    panels = panel_create(page_templates)
    return crop_coords, page_templates, panels
