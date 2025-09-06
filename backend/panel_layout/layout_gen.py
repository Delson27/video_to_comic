import os
from os import listdir
from backend.panel_layout.cam import get_coordinates, dump_CAM_data
from backend.utils import crop_image
from backend.panel_layout.layout.page import get_templates, panel_create
from backend.utils import get_panel_type, types
from PIL import Image


def centroid_crop(index, panel_type, cam_coords, img_w, img_h):
    left, right, top, bottom = cam_coords[0], cam_coords[1], cam_coords[2], cam_coords[3]
    xC, yC = (right + left) / 2, (bottom + top) / 2
    w, h = right - left, bottom - top

    # ✅ Make it a square based on the larger dimension
    side = max(w, h)

    crop_left = xC - (side / 2)
    crop_right = xC + (side / 2)
    crop_top = yC - (side / 2)
    crop_bottom = yC + (side / 2)

    # ✅ Reposition if crop goes outside image boundaries
    if crop_left < 0:
        crop_right -= crop_left
        crop_left = 0
    if crop_top < 0:
        crop_bottom -= crop_top
        crop_top = 0
    if crop_right > img_w:
        diff = crop_right - img_w
        crop_left -= diff
        crop_right = img_w
    if crop_bottom > img_h:
        diff = crop_bottom - img_h
        crop_top -= diff
        crop_bottom = img_h

    frame_path = os.path.join("frames", 'final', f"frame{index+1:03d}.png")
    crop_coords = crop_image(frame_path, crop_left, crop_right, crop_top, crop_bottom)
    return crop_coords


def generate_layout():
    input_seq = ""
    cam_coords = []
    # Get dimensions of images
    img = Image.open(os.path.join("frames", 'final', f"frame001.png"))
    width, height = img.size

    # Loop through images and get type
    folder_dir = "frames/final"
    for image in os.listdir(folder_dir):
        frame_path = os.path.join("frames", 'final', image)
        left, right, top, bottom = get_coordinates(frame_path)
        input_seq += get_panel_type(left, right, top, bottom)
        cam_coords.append((left, right, top, bottom))

    page_templates = get_templates(input_seq)
    print(page_templates)
    i = 0
    crop_coords = []
    try:
        for page in page_templates:
            for panel in page:
                origin = centroid_crop(i, panel, cam_coords[i], width, height)
                crop_coords.append(origin)
                i += 1
    except(IndexError):
        pass

    panels = panel_create(page_templates)
    dump_CAM_data()
    return crop_coords, page_templates, panels
