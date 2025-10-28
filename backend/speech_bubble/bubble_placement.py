from backend.utils import convert_to_css_pixel, get_panel_type, types
import cv2
import dlib
import numpy as np
import os
from PIL import Image

# Default bubble sizes (smaller to fit in letterbox areas)
DEFAULT_BUBBLE_WIDTH = 160
DEFAULT_BUBBLE_HEIGHT = 75

# Initialize face detector (same as in lip_detection.py)
face_detector = dlib.get_frontal_face_detector()

# Face exclusion parameters
# Increased values for strict face avoidance based on user feedback
FACE_PADDING = 45  # Extra pixels around face to avoid (generous safety margin)
MIN_FACE_DISTANCE = 60  # Minimum distance bubble center should be from face edge


def get_image_bounds_in_panel(frame_path, crop_coord, panel_type):
    """
    Detect where the actual image content is within the panel (excluding letterbox areas).
    Returns (image_top, image_bottom) in CSS pixel coordinates.
    """
    try:
        # Read the frame
        frame = cv2.imread(frame_path)
        if frame is None:
            print(f"Warning: Could not load frame {frame_path}")
            return None
        
        left, right, top, bottom = crop_coord
        cropped_panel = frame[top:bottom, left:right]
        
        # Convert to grayscale and find non-black regions
        gray = cv2.cvtColor(cropped_panel, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        
        # Find rows that have content (non-black pixels)
        row_has_content = np.any(thresh > 0, axis=1)
        
        if not np.any(row_has_content):
            print("Warning: No content detected in frame")
            return None
        
        # Find first and last rows with content
        content_rows = np.where(row_has_content)[0]
        image_start_row = content_rows[0]
        image_end_row = content_rows[-1]
        
        # Convert to CSS pixels
        panel_height = types[panel_type]['height']
        actual_height = bottom - top
        scale_factor = panel_height / actual_height
        
        image_top_css = image_start_row * scale_factor
        image_bottom_css = image_end_row * scale_factor
        
        print(f"Image bounds in panel: top={image_top_css:.1f}px, bottom={image_bottom_css:.1f}px (panel height={panel_height}px)")
        
        return {
            'image_top': image_top_css,
            'image_bottom': image_bottom_css,
            'panel_height': panel_height,
            'top_letterbox_height': image_top_css,
            'bottom_letterbox_height': panel_height - image_bottom_css
        }
        
    except Exception as e:
        print(f"Error detecting image bounds: {e}")
        return None


def place_bubble_in_letterbox(image_bounds, lip_y, panel_type):
    """
    Place bubble in the letterbox area (top or bottom background space).
    Chooses top or bottom based on where the speaker's mouth is.
    Ensures bubble stays COMPLETELY within panel boundaries.
    Returns (bubble_x, bubble_y) in CSS pixels.
    """
    panel_width = types[panel_type]['width']
    panel_height = types[panel_type]['height']
    bubble_width = DEFAULT_BUBBLE_WIDTH
    bubble_height = DEFAULT_BUBBLE_HEIGHT
    
    # Safety margins to keep bubble fully inside panel
    MARGIN = 8  # Pixels from panel edge
    
    if image_bounds is None:
        # Fallback: center horizontally, top position
        bubble_x = (panel_width - bubble_width) / 2
        bubble_y = MARGIN
        print(f"⚠️ No image bounds, using safe fallback at ({bubble_x:.1f}, {bubble_y:.1f})")
        return (bubble_x, bubble_y)
    
    image_top = image_bounds['image_top']
    image_bottom = image_bounds['image_bottom']
    top_space = image_bounds['top_letterbox_height']
    bottom_space = image_bounds['bottom_letterbox_height']
    
    # Center horizontally with margin check
    bubble_x = max(MARGIN, min((panel_width - bubble_width) / 2, panel_width - bubble_width - MARGIN))
    
    image_middle = (image_top + image_bottom) / 2
    
    print(f"Lip Y: {lip_y}, Image middle: {image_middle:.1f}, Top space: {top_space:.1f}, Bottom space: {bottom_space:.1f}")
    
    # Minimum space required (bubble height + margins)
    MIN_SPACE_REQUIRED = bubble_height + (2 * MARGIN)
    
    # Decide placement based on available space and speaker position
    if lip_y != -1 and lip_y < image_middle:
        # Mouth in top half - prefer bottom letterbox
        if bottom_space >= MIN_SPACE_REQUIRED:
            # Place in bottom letterbox, ensuring it fits
            bubble_y = min(image_bottom + MARGIN, panel_height - bubble_height - MARGIN)
            print(f"✅ Placing in BOTTOM letterbox at y={bubble_y:.1f}")
        elif top_space >= MIN_SPACE_REQUIRED:
            # Fallback to top letterbox
            bubble_y = max(MARGIN, image_top - bubble_height - MARGIN)
            if bubble_y < MARGIN:
                bubble_y = MARGIN  # Safety clamp
            print(f"✅ Placing in TOP letterbox at y={bubble_y:.1f}")
        else:
            # Insufficient space - place at very top
            bubble_y = MARGIN
            print(f"⚠️ Insufficient space, placing at top with margin")
    else:
        # Mouth in bottom half or unknown - prefer top letterbox
        if top_space >= MIN_SPACE_REQUIRED:
            # Place in top letterbox
            bubble_y = max(MARGIN, image_top - bubble_height - MARGIN)
            if bubble_y < MARGIN:
                bubble_y = MARGIN  # Safety clamp
            print(f"✅ Placing in TOP letterbox at y={bubble_y:.1f}")
        elif bottom_space >= MIN_SPACE_REQUIRED:
            # Fallback to bottom letterbox
            bubble_y = min(image_bottom + MARGIN, panel_height - bubble_height - MARGIN)
            print(f"✅ Placing in BOTTOM letterbox at y={bubble_y:.1f}")
        else:
            # Insufficient space - place at very bottom
            bubble_y = panel_height - bubble_height - MARGIN
            print(f"⚠️ Insufficient space, placing at bottom with margin")
    
    # Final safety check: ensure bubble is completely within panel
    bubble_y = max(MARGIN, min(bubble_y, panel_height - bubble_height - MARGIN))
    bubble_x = max(MARGIN, min(bubble_x, panel_width - bubble_width - MARGIN))
    
    print(f"📍 Final clamped position: ({bubble_x:.1f}, {bubble_y:.1f})")
    return (bubble_x, bubble_y)

def detect_faces_in_panel(frame_path, crop_coord):
    """
    Detect all faces in a cropped panel region and return their bounding boxes.
    Returns list of face rectangles in panel coordinates (relative to crop).
    """
    try:
        # Read the full frame
        frame = cv2.imread(frame_path)
        if frame is None:
            print(f"Warning: Could not load frame {frame_path}")
            return []
        
        left, right, top, bottom = crop_coord
        
        # Extract the cropped panel region
        cropped_panel = frame[top:bottom, left:right]
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(cropped_panel, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        face_rects = face_detector(gray, 1)
        
        # Convert dlib rectangles to our format (x, y, width, height)
        faces = []
        for rect in face_rects:
            x = rect.left()
            y = rect.top()
            w = rect.width()
            h = rect.height()
            faces.append({
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'center_x': x + w // 2,
                'center_y': y + h // 2
            })
        
        print(f"Detected {len(faces)} face(s) in panel")
        return faces
        
    except Exception as e:
        print(f"Error detecting faces: {e}")
        return []


def is_overlapping_face(bubble_x, bubble_y, faces, panel_type, bubble_width, bubble_height):
    """
    Check if a bubble position overlaps with any detected face.
    Returns True if overlapping, False if safe.
    """
    if not faces:
        return False  # No faces detected, safe to place anywhere
    
    # Get panel dimensions
    panel_width = types[panel_type]['width']
    panel_height = types[panel_type]['height']
    
    # Calculate bubble bounding box (in panel coordinates)
    bubble_right = bubble_x + bubble_width
    bubble_bottom = bubble_y + bubble_height
    
    # Check overlap with each face
    for face in faces:
        # Expand face bounding box with padding
        face_left = max(0, face['x'] - FACE_PADDING)
        face_right = min(panel_width, face['x'] + face['width'] + FACE_PADDING)
        face_top = max(0, face['y'] - FACE_PADDING)
        face_bottom = min(panel_height, face['y'] + face['height'] + FACE_PADDING)
        
        # Check for overlap using rectangle intersection
        if not (bubble_right < face_left or      # Bubble is to the left of face
                bubble_x > face_right or         # Bubble is to the right of face
                bubble_bottom < face_top or      # Bubble is above face
                bubble_y > face_bottom):         # Bubble is below face
            print(f"Bubble overlaps face at ({face['x']}, {face['y']})")
            return True
    
    return False


def find_best_position_avoiding_faces(crop_coord, CAM_data, faces, panel_type, bubble_width, bubble_height):
    """
    Find the best bubble position that:
    1. Avoids all detected faces
    2. Prefers low-importance CAM regions
    3. Falls back to corners if needed
    """
    left, right, top, bottom = crop_coord
    x_ = CAM_data['x_']
    y_ = CAM_data['y_']
    ten_map = CAM_data['ten_map']
    
    new_top = int(top / y_)
    new_bottom = int(bottom / y_)
    new_left = int(left / x_)
    new_right = int(right / x_)
    
    # Get panel dimensions
    panel_width = types[panel_type]['width']
    panel_height = types[panel_type]['height']
    
    # Create a list of candidate positions with their CAM scores
    candidates = []
    
    # Scan through the CAM map to find all possible positions
    for i in range(new_left, new_right + 1):
        for j in range(new_top, new_bottom + 1):
            if i < ten_map.shape[0] and j < ten_map.shape[1]:
                # Convert CAM coordinates to panel coordinates
                panel_x = i * x_ - left
                panel_y = j * y_ - top
                
                # Ensure position is within panel bounds
                if panel_x < 0:
                    panel_x = 0
                elif panel_x > panel_width - bubble_width:
                    panel_x = panel_width - bubble_width
                    
                if panel_y < 0:
                    panel_y = 0
                elif panel_y > panel_height - bubble_height:
                    panel_y = panel_height - bubble_height
                
                # Convert to CSS pixels for overlap check
                css_x, css_y = convert_to_css_pixel(panel_x, panel_y, crop_coord, False)
                
                # Check if this position overlaps with faces
                if not is_overlapping_face(css_x, css_y, faces, panel_type, bubble_width, bubble_height):
                    candidates.append({
                        'x': panel_x,
                        'y': panel_y,
                        'cam_score': ten_map[i][j],
                        'css_x': css_x,
                        'css_y': css_y
                    })
    
    # If we found positions that don't overlap faces, choose the one with lowest CAM score
    if candidates:
        best = min(candidates, key=lambda c: c['cam_score'])
        print(f"Found safe position at ({best['css_x']}, {best['css_y']}) with CAM score {best['cam_score']}")
        return best['css_x'], best['css_y']
    
    # FALLBACK: No safe position found in CAM map, try corner positions
    print("Warning: No safe CAM position found, trying corner fallbacks")
    corner_positions = [
        (10, 10, 'top-left'),
        (panel_width - bubble_width - 10, 10, 'top-right'),
        (10, panel_height - bubble_height - 10, 'bottom-left'),
        (panel_width - bubble_width - 10, panel_height - bubble_height - 10, 'bottom-right'),
    ]
    
    for x, y, corner_name in corner_positions:
        css_x, css_y = convert_to_css_pixel(x, y, crop_coord, False)
        if not is_overlapping_face(css_x, css_y, faces, panel_type, bubble_width, bubble_height):
            print(f"Using {corner_name} corner as fallback")
            return css_x, css_y
    
    # LAST RESORT: Place at top-left with warning
    print("WARNING: Could not find any position avoiding faces! Using top-left corner.")
    css_x, css_y = convert_to_css_pixel(10, 10, crop_coord, False)
    return css_x, css_y


def add_bubble_padding(least_roi_x, least_roi_y, crop_coord, bubble_width, bubble_height):
    left,right,top,bottom = crop_coord
    panel = get_panel_type(left, right, top, bottom)
    
    image_width = types[panel]['width']
    image_height = types[panel]['height']

    if least_roi_x == 0:
        if panel == '1' or panel == '2':
            least_roi_x += 10
        elif panel == '3':
            least_roi_x += 30
        else:
            least_roi_x += 20

    elif least_roi_x == image_width:
        least_roi_x -= bubble_width + 15

    elif least_roi_x >= image_width - bubble_width:
        least_roi_x -= bubble_width - (image_width - least_roi_x) + 15

    if least_roi_y == 0:
        if panel == '2':
            least_roi_y += 30
        else:
            least_roi_y += 15

    elif least_roi_y == image_height:
        least_roi_y -= bubble_height + 15

    elif least_roi_y >= image_height - bubble_height:
        least_roi_y -= bubble_height - (image_height - least_roi_y) + 15
    
    return least_roi_x, least_roi_y


def get_bubble_position(crop_coord, CAM_data, is_normal_page=False, frame_index=None, bubble_width=None, bubble_height=None, lip_y=-1):
    """
    Get optimal bubble position in the letterbox areas (background space) of the panel.
    Places bubbles OUTSIDE the image content, in the top or bottom letterbox areas.
    
    Args:
        crop_coord: Tuple of (left, right, top, bottom) coordinates
        CAM_data: Dictionary with CAM heatmap data  
        is_normal_page: Boolean indicating if this is a normal page
        frame_index: Frame number (1-indexed) to load the corresponding image
        bubble_width: Dynamic bubble width (defaults to DEFAULT_BUBBLE_WIDTH)
        bubble_height: Dynamic bubble height (defaults to DEFAULT_BUBBLE_HEIGHT)
        lip_y: Y coordinate of speaker's mouth in CSS pixels (-1 if unknown)
    """
    # Use default sizes if not provided
    if bubble_width is None:
        bubble_width = DEFAULT_BUBBLE_WIDTH
    if bubble_height is None:
        bubble_height = DEFAULT_BUBBLE_HEIGHT
    
    left, right, top, bottom = crop_coord
    
    # Determine panel type
    if is_normal_page:
        panel_type = '1'
    else:
        panel_type = get_panel_type(left, right, top, bottom)
    
    # ✅ NEW APPROACH: Place bubble in letterbox area (background space)
    if frame_index is not None:
        frame_path = f"frames/final/frame{frame_index:03}.png"
        if os.path.exists(frame_path):
            print(f"\n🎯 Using LETTERBOX placement for frame {frame_index}")
            
            # Detect where the actual image content is within the panel
            image_bounds = get_image_bounds_in_panel(frame_path, crop_coord, panel_type)
            
            # Place bubble in top or bottom letterbox area
            bubble_x, bubble_y = place_bubble_in_letterbox(image_bounds, lip_y, panel_type)
            
            print(f"✅ Final bubble position: ({bubble_x:.1f}, {bubble_y:.1f}) - IN LETTERBOX AREA")
            return bubble_x, bubble_y
        else:
            print(f"Warning: Frame {frame_path} not found")
    
    # FALLBACK: If frame detection fails, use safe default positioning
    panel_width = types[panel_type]['width']
    panel_height = types[panel_type]['height']
    
    # Place at top center as fallback
    bubble_x = (panel_width - bubble_width) / 2
    bubble_y = 10
    
    print(f"⚠️ Fallback: Placing bubble at top center ({bubble_x:.1f}, {bubble_y:.1f})")
    return bubble_x, bubble_y