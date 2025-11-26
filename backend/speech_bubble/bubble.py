import json
import srt
from backend.speech_bubble.lip_detection import get_lips, refine_lip_position_with_proximity
from backend.speech_bubble.bubble_placement import get_bubble_position, calculate_bubble_size
from backend.speech_bubble.bubble_shape import get_bubble_type
from backend.class_def import bubble
from backend.utils import get_panel_type, types


def bubble_create(video, crop_coords, black_x, black_y):
    """Create speech bubbles for comic panels with dialogue and positioning."""
    bubbles = []

    data=""
    with open("test1.srt") as f:
        data=f.read()
    subs=srt.parse(data)

    # ✅ FIRST PASS: Get initial lip positions (may be incorrect for multi-speaker scenes)
    lips = get_lips(video, crop_coords, black_x, black_y)


    for sub in subs:
        lip_x = lips[sub.index][0]
        lip_y = lips[sub.index][1]

        idx_crop = min(sub.index - 1, len(crop_coords) - 1)
        
        # Determine if this is a normal page or last page
        # You'll need to pass this information through the pipeline
        is_normal_page = True  # This needs to be determined based on your logic
        
        # ✅ Calculate bubble size based on dialogue length
        dialogue = sub.content
        bubble_width, bubble_height = calculate_bubble_size(dialogue)
        
        # ✅ Pass lip_y and calculated bubble sizes to help position bubble appropriately
        bubble_x, bubble_y = get_bubble_position(
            crop_coords[idx_crop], 
            is_normal_page,
            frame_index=sub.index,  # Pass the frame number for image bounds detection
            bubble_width=bubble_width,  # ✅ NEW: Pass calculated width
            bubble_height=bubble_height,  # ✅ NEW: Pass calculated height
            lip_y=lip_y  # ✅ Pass lip Y coordinate for smart placement
        )

        emotion = get_bubble_type(dialogue)
        print(f'||emotion:{emotion}||')


        if is_normal_page:
            panel_type = '1'
        else:
            panel_type = get_panel_type(*crop_coords[idx_crop])

        panel_info = types[panel_type]

        temp = bubble(
            bubble_x,
            bubble_y,
            lip_x,
            lip_y,
            sub.content,
            emotion,
            bubble_width,
            bubble_height,
            panel_type,
            panel_info['width'],
            panel_info['height'],
        )
        bubbles.append(temp)
    
    # ✅ SECOND PASS: Refine lip positions for multi-speaker scenes
    print("\n✅ PASS 2: Refining lip positions for multi-speaker scenes...")
    for i, sub in enumerate(subs):
        if i >= len(bubbles):
            break
            
        current_bubble = bubbles[i]
        current_lip = lips[sub.index]
        
        # Skip if no lip was detected initially
        if current_lip == (-1, -1):
            continue
        
        # Try to refine using proximity to bubble
        idx_crop = min(sub.index - 1, len(crop_coords) - 1)
        refined_lip = refine_lip_position_with_proximity(
            sub.index,
            video,
            crop_coords,
            black_x,
            black_y,
            (current_bubble.bubble_x, current_bubble.bubble_y)
        )
        
        if refined_lip:
            # Update bubble with refined lip position
            print(f"  Frame {sub.index}: Updated lip from {current_lip} to {refined_lip}")
            
            # Recalculate tail angle with new lip position
            import numpy as np
            dx = refined_lip[0] - current_bubble.bubble_x
            dy = refined_lip[1] - current_bubble.bubble_y
            angle = np.arctan2(dy, dx)
            
            current_bubble.lip_x = refined_lip[0]
            current_bubble.lip_y = refined_lip[1]
            current_bubble.tail_deg = np.degrees(angle)
            
            tail_length = 80
            current_bubble.tail_offset_x = tail_length * np.cos(angle)
            current_bubble.tail_offset_y = tail_length * np.sin(angle)
            current_bubble.tail_length = tail_length
    
    return bubbles









