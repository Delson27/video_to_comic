from backend.utils import convert_to_css_pixel, get_panel_type, types
import cv2
import dlib
import numpy as np
import os
import math
from PIL import Image

# Default bubble sizes (dynamic sizing with min/max constraints)
DEFAULT_BUBBLE_WIDTH = 140  # Minimum width
DEFAULT_BUBBLE_HEIGHT = 60  # Minimum height
MAX_BUBBLE_WIDTH = 200  # Maximum width
MAX_BUBBLE_HEIGHT = 150  # Maximum height (allows expansion for longer text)

def calculate_bubble_size(dialogue_text):
    """
    Calculate the required bubble size based on dialogue length.
    Returns (width, height) ensuring all text will be visible.
    """
    text_length = len(dialogue_text)
    
    # Estimate lines needed (assuming ~25 chars per line at font size 10px)
    chars_per_line = 25
    estimated_lines = max(1, math.ceil(text_length / chars_per_line))
    
    # Calculate required height (base height + line height for each additional line)
    line_height = 14  # pixels per line at font size 10px with line-height 1.4
    required_height = DEFAULT_BUBBLE_HEIGHT + (estimated_lines - 2) * line_height if estimated_lines > 2 else DEFAULT_BUBBLE_HEIGHT
    
    # Clamp to max height
    height = min(required_height, MAX_BUBBLE_HEIGHT)
    
    # Width scales slightly with text length but clamped to max
    if text_length < 30:
        width = DEFAULT_BUBBLE_WIDTH
    elif text_length < 60:
        width = 170
    else:
        width = MAX_BUBBLE_WIDTH
    
    print(f"Dialogue length: {text_length} chars → Bubble size: {width}x{height}px ({estimated_lines} lines)")
    return width, height

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


def place_bubble_in_letterbox(image_bounds, lip_y, panel_type, bubble_width, bubble_height):
    """
    🎯 PRECISE BOUNDARY-BASED PLACEMENT:
    - Image width = Panel width (no left/right letterbox)
    - Bubble's TOP EDGE touches image's bottom boundary
    - Bubble extends downward into bottom letterbox area
    - Stays strictly within panel's bottom boundary
    
    Visual:
    ├─────────────────┤ ← Image bottom boundary
    ┌─────────────────┐ ← Bubble TOP edge (touches image boundary)
    │  SPEECH BUBBLE  │ ← Bubble extends into letterbox
    └─────────────────┘ ← Bubble bottom edge
    ─────────────────── ← Panel bottom boundary (limit)
    
    Returns (bubble_x, bubble_y) in CSS pixels where bubble_y is the TOP of the bubble.
    """
    panel_width = types[panel_type]['width']
    panel_height = types[panel_type]['height']
    
    # Safety margins to keep bubble fully inside panel
    MARGIN = 5  # Minimal margin for clean edges
    
    if image_bounds is None:
        # Fallback: place at bottom with margin
        bubble_x = (panel_width - bubble_width) / 2
        bubble_y = panel_height - bubble_height - MARGIN
        print(f"⚠️ No image bounds, using safe fallback at bottom ({bubble_x:.1f}, {bubble_y:.1f})")
        return (bubble_x, bubble_y)
    
    image_bottom = image_bounds['image_bottom']  # ⭐ This is where bubble TOP edge should be
    bottom_space = image_bounds['bottom_letterbox_height']
    
    # Center horizontally (frame width = panel width, so simple centering)
    bubble_x = (panel_width - bubble_width) / 2
    
    print(f"📏 Image bottom boundary: {image_bottom:.1f}px")
    print(f"📏 Panel bottom boundary: {panel_height}px")
    print(f"📏 Available bottom letterbox space: {bottom_space:.1f}px")
    print(f"📏 Bubble dimensions: {bubble_width}×{bubble_height}px")
    
    # 🎯 CRITICAL: Bubble's TOP EDGE should touch image bottom boundary
    # But ONLY if the bubble will fit within panel bottom boundary
    bubble_y = image_bottom
    bubble_bottom_edge = bubble_y + bubble_height
    
    # Check if bubble would exceed panel bottom boundary
    if bubble_bottom_edge > panel_height - MARGIN:
        # Bubble is too tall - we MUST shrink it or move it up
        # Move bubble up so bottom edge stays within panel
        bubble_y = panel_height - bubble_height - MARGIN
        print(f"⚠️ Bubble too tall ({bubble_height}px > {bottom_space:.1f}px available)")
        print(f"⚠️ Adjusted bubble TOP to: y={bubble_y:.1f}px to fit within panel")
        print(f"⚠️ Bubble will NOT touch image boundary (not enough space)")
    else:
        # Bubble fits perfectly - keep it touching image boundary
        print(f"✅ Bubble TOP edge at image boundary: y={bubble_y:.1f}px")
        print(f"✅ Bubble bottom edge at: y={bubble_bottom_edge:.1f}px (within panel)")
    
    # CRITICAL FINAL SAFETY: Absolutely ensure bubble stays within panel
    # This is the ultimate guard - bubble CANNOT exceed these bounds
    bubble_x = max(MARGIN, min(bubble_x, panel_width - bubble_width - MARGIN))
    bubble_y = max(MARGIN, bubble_y)  # Don't go above panel top
    
    # 🔒 ABSOLUTE RULE: Bubble bottom edge MUST be within panel
    max_allowed_y = panel_height - bubble_height - MARGIN
    if bubble_y > max_allowed_y:
        bubble_y = max_allowed_y
        print(f"🔒 CLAMPED: Forced bubble_y to {bubble_y:.1f} to prevent exceeding panel bottom")
    
    print(f"📍 Final position: ({bubble_x:.1f}, {bubble_y:.1f})")
    print(f"📍 Bubble zone: TOP edge y={bubble_y:.1f}, BOTTOM edge y={bubble_y + bubble_height:.1f}")
    print(f"📍 Panel boundaries: width=0 to {panel_width}px, height=0 to {panel_height}px")
    
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


def get_bubble_position(crop_coord, is_normal_page=False, frame_index=None, bubble_width=None, bubble_height=None, lip_y=-1):
    """
    Get optimal bubble position in the letterbox areas (background space) of the panel.
    Places bubbles OUTSIDE the image content, in the top or bottom letterbox areas.
    
    Args:
        crop_coord: Tuple of (left, right, top, bottom) coordinates
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
    
    # ✅ PRECISE BOUNDARY-BASED PLACEMENT: Place bubble in bottom letterbox only
    if frame_index is not None:
        frame_path = f"frames/final/frame{frame_index:03}.png"
        if os.path.exists(frame_path):
            print(f"\n🎯 Using PRECISE BOUNDARY placement for frame {frame_index}")
            
            # Detect where the actual image content is within the panel
            image_bounds = get_image_bounds_in_panel(frame_path, crop_coord, panel_type)
            
            # ✅ Pass bubble dimensions to placement function
            bubble_x, bubble_y = place_bubble_in_letterbox(image_bounds, lip_y, panel_type, bubble_width, bubble_height)
            
            print(f"✅ Final bubble position: ({bubble_x:.1f}, {bubble_y:.1f}) - IN BOTTOM LETTERBOX (STRICT BOUNDARIES)")
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