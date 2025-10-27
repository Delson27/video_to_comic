from backend.utils import convert_to_css_pixel, get_panel_type, types
import cv2
import dlib
import numpy as np
import os

BUBBLE_WIDTH = 200
BUUBLE_HEIGHT = 94

# Initialize face detector (same as in lip_detection.py)
face_detector = dlib.get_frontal_face_detector()

# Face exclusion parameters
FACE_PADDING = 20  # Extra pixels around face to avoid
MIN_FACE_DISTANCE = 30  # Minimum distance bubble center should be from face edge

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


def is_overlapping_face(bubble_x, bubble_y, faces, panel_type):
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
    bubble_right = bubble_x + BUBBLE_WIDTH
    bubble_bottom = bubble_y + BUUBLE_HEIGHT
    
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


def find_best_position_avoiding_faces(crop_coord, CAM_data, faces, panel_type):
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
                elif panel_x > panel_width - BUBBLE_WIDTH:
                    panel_x = panel_width - BUBBLE_WIDTH
                    
                if panel_y < 0:
                    panel_y = 0
                elif panel_y > panel_height - BUUBLE_HEIGHT:
                    panel_y = panel_height - BUUBLE_HEIGHT
                
                # Convert to CSS pixels for overlap check
                css_x, css_y = convert_to_css_pixel(panel_x, panel_y, crop_coord, False)
                
                # Check if this position overlaps with faces
                if not is_overlapping_face(css_x, css_y, faces, panel_type):
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
        (panel_width - BUBBLE_WIDTH - 10, 10, 'top-right'),
        (10, panel_height - BUUBLE_HEIGHT - 10, 'bottom-left'),
        (panel_width - BUBBLE_WIDTH - 10, panel_height - BUUBLE_HEIGHT - 10, 'bottom-right'),
    ]
    
    for x, y, corner_name in corner_positions:
        css_x, css_y = convert_to_css_pixel(x, y, crop_coord, False)
        if not is_overlapping_face(css_x, css_y, faces, panel_type):
            print(f"Using {corner_name} corner as fallback")
            return css_x, css_y
    
    # LAST RESORT: Place at top-left with warning
    print("WARNING: Could not find any position avoiding faces! Using top-left corner.")
    css_x, css_y = convert_to_css_pixel(10, 10, crop_coord, False)
    return css_x, css_y


def add_bubble_padding(least_roi_x, least_roi_y, crop_coord):
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
        least_roi_x -= BUBBLE_WIDTH + 15

    elif least_roi_x >= image_width - BUBBLE_WIDTH:
        least_roi_x -= BUBBLE_WIDTH - (image_width - least_roi_x) + 15

    if least_roi_y == 0:
        if panel == '2':
            least_roi_y += 30
        else:
            least_roi_y += 15

    elif least_roi_y == image_height:
        least_roi_y -= BUUBLE_HEIGHT + 15

    elif least_roi_y >= image_height - BUUBLE_HEIGHT:
        least_roi_y -= BUUBLE_HEIGHT - (image_height - least_roi_y) + 15
    
    return least_roi_x, least_roi_y


def get_bubble_position(crop_coord, CAM_data, is_normal_page=False, frame_index=None):
    """
    Get optimal bubble position that avoids faces and prefers low-importance regions.
    
    Args:
        crop_coord: Tuple of (left, right, top, bottom) coordinates
        CAM_data: Dictionary with CAM heatmap data
        is_normal_page: Boolean indicating if this is a normal page
        frame_index: Frame number (1-indexed) to load the corresponding image
    """
    left, right, top, bottom = crop_coord
    
    # Determine panel type
    if is_normal_page:
        panel_type = '1'
    else:
        panel_type = get_panel_type(left, right, top, bottom)
    
    # Detect faces in the panel if frame_index is provided
    faces = []
    if frame_index is not None:
        frame_path = f"frames/final/frame{frame_index:03}.png"
        if os.path.exists(frame_path):
            faces = detect_faces_in_panel(frame_path, crop_coord)
        else:
            print(f"Warning: Frame {frame_path} not found, skipping face detection")
    
    # Find best position avoiding faces
    if faces:
        print(f"Using face-aware placement for frame {frame_index}")
        bubble_x, bubble_y = find_best_position_avoiding_faces(crop_coord, CAM_data, faces, panel_type)
    else:
        print(f"No faces detected or frame not provided, using standard CAM placement")
        # Original algorithm (when no faces detected)
        x_ = CAM_data['x_']
        y_ = CAM_data['y_']
        ten_map = CAM_data['ten_map']
        
        new_top = int(top / y_)
        new_bottom = int(bottom / y_)
        new_left = int(left / x_)
        new_right = int(right / x_)
        
        min_value = float('inf')
        min_point = None
        
        for i in range(new_left, new_right + 1):
            for j in range(new_top, new_bottom + 1):
                if (i < ten_map.shape[0] and j < ten_map.shape[1]) and ten_map[i][j] < min_value:
                    min_point = (i, j)
                    min_value = ten_map[i][j]
        
        least_roi_x = min_point[0] * x_
        least_roi_y = min_point[1] * y_
        
        if least_roi_x < left:
            least_roi_x = left
        elif least_roi_x > right:
            least_roi_x = right
        if least_roi_y < top:
            least_roi_y = top
        elif least_roi_y > bottom:
            least_roi_y = bottom
        
        least_roi_x -= left
        least_roi_y -= top
        print("Least ROI coords: ", least_roi_x, least_roi_y)
        
        bubble_x, bubble_y = convert_to_css_pixel(least_roi_x, least_roi_y, crop_coord, is_normal_page)
        print("Least ROI coords after scaling: ", bubble_x, bubble_y)
    
    # Add padding to avoid edges
    bubble_x, bubble_y = add_bubble_padding(bubble_x, bubble_y, crop_coord)
    
    print(f"Final bubble position: ({bubble_x}, {bubble_y})")
    return bubble_x, bubble_y