import dlib
import cv2
import os
import srt
import re
from math import floor,sqrt
from backend.utils import convert_to_css_pixel

# Some constants
THETA1 = 1.2    # Difference between lip distance of prev and curr frame
THETA2 = 0.4    # No. of lips crossed ratio
SAMPLE_RATE = 5 
FACE_AREA = 0.6 

# Face detector and landmark detector
face_detector = dlib.get_frontal_face_detector()   

# Update the path to use an absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
landmark_path = os.path.join(current_dir, "shape_predictor_68_face_landmarks.dat")

landmark_detector = dlib.shape_predictor(landmark_path)


def dist(p1, p2):
    p1_x = p1[0]
    p2_x = p2[0]
    p1_y = p1[1]
    p2_y = p2[1]
    dist = sqrt((p2_x - p1_x) ** 2 + (p2_y - p1_y) ** 2)
    return dist

# Checks if 2 face rectangles have the same area using their top-left and bottom-right corners
def similar_to_keyframe(face_rects, keyframe_face_rects):
    rect1_top_left = face_rects[0].tl_corner()
    rect1_bottom_right = face_rects[0].br_corner()
    rect2_top_left = keyframe_face_rects[0].tl_corner()
    rect2_bottom_right = keyframe_face_rects[0].br_corner()
    tolerance = 0.2
    
    def calculate_area(top_left, bottom_right):
        width = abs(bottom_right.x - top_left.x)
        height = abs(bottom_right.y - top_left.y)
        return width * height

    area_rect1 = calculate_area(rect1_top_left, rect1_bottom_right)
    area_rect2 = calculate_area(rect2_top_left, rect2_bottom_right)
    
    area_tolerance = area_rect1 * tolerance
    
    if abs(area_rect1 - area_rect2) <= area_tolerance:
        return True
    else:
        return False

#crop_coords contain left,right,top,bottom of each frame
def get_lips(video, crop_coords, black_x, black_y):
    """
    Main function to detect lip positions for all subtitle segments.
    Handles single-speaker, multi-speaker, and action scenes.
    """
    print(f"\n{'='*80}")
    print(f"STARTING LIP DETECTION PROCESS")
    print(f"{'='*80}\n")
    print(f"Crop coordinates: {len(crop_coords)} frames")
    
    data = ""
    with open("test1.srt") as f:
        data = f.read()
    subs = srt.parse(data)

    lips = {}
    
    for sub in subs:  
        keyframe_path = f"frames/final/frame{sub.index:03}.png"
        
        print(f"\n{'─'*80}")
        print(f"Processing Subtitle {sub.index}: \"{sub.content[:50]}...\"" if len(sub.content) > 50 else f"Processing Subtitle {sub.index}: \"{sub.content}\"")
        print(f"Time: {sub.start} → {sub.end}")
        
        # Check if keyframe exists
        if not os.path.exists(keyframe_path):
            print(f"❌ Keyframe not found: {keyframe_path}")
            lips[sub.index] = (-1, -1)
            continue
            
        keyframe = cv2.imread(keyframe_path)
        if keyframe is None:
            print(f"❌ Failed to load keyframe: {keyframe_path}")
            lips[sub.index] = (-1, -1)
            continue
            
        gray = cv2.cvtColor(keyframe, cv2.COLOR_BGR2GRAY)
        face_rects = face_detector(gray, 1)
        
        # Action scene handling
        if sub.content == "((action-scene))":
            print("⚡ Action scene detected - skipping lip detection")
            lips[sub.index] = (-1, -1)
            continue

        # No face detected
        if len(face_rects) < 1:
            print(f"⚠️ No faces detected in keyframe")
            lips[sub.index] = (-1, -1)
            continue

        # ✅ SINGLE SPEAKER: One face detected
        if len(face_rects) == 1:
            print(f"✅ Single speaker detected")
            rect = face_rects[0]
            
            try:
                landmark = landmark_detector(gray, rect)
                lip_center = landmark.part(65)  # Bottom lip center point
                
                # Convert to panel coordinates
                x, y = convert_to_css_pixel(
                    lip_center.x, 
                    lip_center.y, 
                    crop_coords[sub.index - 1]
                )
                
                lips[sub.index] = (x, y)
                print(f"   Lip position: ({x:.1f}, {y:.1f})")
                
            except Exception as e:
                print(f"❌ Landmark detection failed: {e}")
                lips[sub.index] = (-1, -1)
            
            continue

        # ✅ MULTI-SPEAKER: Multiple faces detected
        if len(face_rects) > 1:
            print(f"👥 Multiple speakers detected: {len(face_rects)} faces")
            origin = (crop_coords[sub.index - 1][0], crop_coords[sub.index - 1][2])  # (left, top)
            
            # Call enhanced multi-speaker detection
            lip_coords = get_multi_speaker_lips(sub, video, face_rects)
            
            if lip_coords == (-1, -1):
                print(f"⚠️ Multi-speaker detection failed")
                lips[sub.index] = (-1, -1)
            else:
                # Convert from absolute video coordinates to panel coordinates
                x = lip_coords[0] - (origin[0] + black_x)
                y = lip_coords[1] - (origin[1] + black_y)
                x, y = convert_to_css_pixel(x, y, crop_coords[sub.index - 1])
                
                lips[sub.index] = (x, y)
                print(f"   Active speaker lip position: ({x:.1f}, {y:.1f})")
            
            continue
    
    print(f"\n{'='*80}")
    print(f"LIP DETECTION COMPLETE")
    print(f"Total subtitles: {len(lips)}")
    print(f"Successful detections: {sum(1 for pos in lips.values() if pos != (-1, -1))}")
    print(f"{'='*80}\n")
    
    return lips


def get_multi_speaker_lips(sub,video, keyframe_face_rects):
    """
    Enhanced multi-speaker detection with robust speaker identification.
    Analyzes lip movement across video frames to identify the active speaker.
    """
    start_time = sub.start.total_seconds()
    end_time = sub.end.total_seconds()
    keyframe_path = f"frames/final/frame{sub.index:03}.png"

    vid = cv2.VideoCapture(video)
    frames_per_sec = vid.get(cv2.CAP_PROP_FPS)

    select_index = max(1, floor(frames_per_sec / SAMPLE_RATE))
    start_frame = int(start_time * frames_per_sec)
    end_frame = int(end_time * frames_per_sec)

    vid.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    print(f"\n{'='*60}")
    print(f"Multi-Speaker Detection for Subtitle {sub.index}")
    print(f"FPS: {frames_per_sec}, Select index: {select_index}")
    print(f"Frames: {start_frame} to {end_frame} ({end_frame - start_frame} frames)")
    print(f"{'='*60}")

    # Frame buffers
    frame_buffer = []
    frame_buffer_color = []
    current_frame = start_frame
    total_frames_selected = 0

    # Extract frames for analysis
    while current_frame < end_frame:
        success, frame = vid.read()
        if not success:
            break
        if current_frame % select_index == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame_buffer.append(gray)
            frame_buffer_color.append(frame)
            total_frames_selected += 1
        current_frame += 1
    vid.release()

    if total_frames_selected < 2:
        print("⚠️ Insufficient frames for analysis")
        return (-1, -1)

    # ✅ Enhanced tracking data structures
    face_tracker = {}  # {face_id: {position, lip_coords, motion_count, consistency_score}}
    frame_faces = []   # List of faces detected in each frame
    
    print(f"\n📊 Analyzing {total_frames_selected} frames...")

    # First pass: Track faces across frames and build face profiles
    for (i, image) in enumerate(frame_buffer):
        face_rects = face_detector(image, 1)
        
        if len(face_rects) < 1:
            print(f"  Frame {i}: No faces detected")
            frame_faces.append([])
            continue

        # Sort faces left-to-right for consistent ordering
        face_rects = sorted(face_rects, key=lambda rect: rect.left())
        
        frame_face_data = []
        for rect in face_rects:
            face_data = {
                'rect': rect,
                'center_x': rect.left() + rect.width() // 2,
                'center_y': rect.top() + rect.height() // 2,
                'area': rect.area(),
                'landmarks': None,
                'lip_distance': 0
            }
            
            # Get facial landmarks
            try:
                landmark = landmark_detector(image, rect)
                face_data['landmarks'] = landmark
                
                # Calculate lip opening (vertical distance)
                part_61 = (landmark.part(61).x, landmark.part(61).y)
                part_67 = (landmark.part(67).x, landmark.part(67).y)
                part_62 = (landmark.part(62).x, landmark.part(62).y)
                part_66 = (landmark.part(66).x, landmark.part(66).y)
                part_63 = (landmark.part(63).x, landmark.part(63).y)
                part_65 = (landmark.part(65).x, landmark.part(65).y)
                
                A = dist(part_61, part_67)
                B = dist(part_62, part_66)
                C = dist(part_63, part_65)
                face_data['lip_distance'] = (A + B + C) / 3.0
                face_data['lip_coords'] = part_65  # Bottom lip center
                
            except Exception as e:
                print(f"  ⚠️ Landmark detection failed for face in frame {i}: {e}")
                continue
                
            frame_face_data.append(face_data)
        
        frame_faces.append(frame_face_data)
        print(f"  Frame {i}: {len(frame_face_data)} face(s) detected")

    # Second pass: Match faces across frames and track lip motion
    print(f"\n🔍 Tracking speakers across frames...")
    
    # Initialize face IDs based on spatial position (left-to-right)
    if len(frame_faces[0]) > 0:
        for idx, face_data in enumerate(frame_faces[0]):
            face_tracker[idx] = {
                'position_x': face_data['center_x'],
                'position_y': face_data['center_y'],
                'lip_coords': face_data.get('lip_coords', None),
                'lip_distances': [face_data['lip_distance']],
                'motion_count': 0,
                'frame_count': 1,
                'area': face_data['area']
            }

    # Track lip movement changes across frames
    for i in range(1, len(frame_faces)):
        if len(frame_faces[i]) == 0:
            continue
            
        # Match current frame faces to tracked faces
        for curr_face in frame_faces[i]:
            best_match_id = None
            min_distance = float('inf')
            
            # Find closest tracked face (spatial matching)
            for face_id, tracked in face_tracker.items():
                spatial_dist = sqrt(
                    (curr_face['center_x'] - tracked['position_x'])**2 +
                    (curr_face['center_y'] - tracked['position_y'])**2
                )
                
                if spatial_dist < min_distance and spatial_dist < 100:  # Threshold for same person
                    min_distance = spatial_dist
                    best_match_id = face_id
            
            # Update tracked face or create new entry
            if best_match_id is not None:
                tracked = face_tracker[best_match_id]
                prev_lip_dist = tracked['lip_distances'][-1]
                curr_lip_dist = curr_face['lip_distance']
                
                # Check for significant lip movement
                if abs(curr_lip_dist - prev_lip_dist) > THETA1:
                    tracked['motion_count'] += 1
                
                tracked['lip_distances'].append(curr_lip_dist)
                tracked['frame_count'] += 1
                tracked['lip_coords'] = curr_face.get('lip_coords', tracked['lip_coords'])
                
            else:
                # New face appeared mid-dialogue
                new_id = len(face_tracker)
                face_tracker[new_id] = {
                    'position_x': curr_face['center_x'],
                    'position_y': curr_face['center_y'],
                    'lip_coords': curr_face.get('lip_coords', None),
                    'lip_distances': [curr_face['lip_distance']],
                    'motion_count': 0,
                    'frame_count': 1,
                    'area': curr_face['area']
                }

    # Third pass: Identify the active speaker
    print(f"\n🎤 Speaker Analysis:")
    print(f"{'Face ID':<10} {'Position':<15} {'Motion':<10} {'Frames':<10} {'Motion %':<10}")
    print(f"{'-'*60}")
    
    active_speaker_id = None
    max_motion_ratio = 0
    
    for face_id, tracked in face_tracker.items():
        motion_ratio = tracked['motion_count'] / max(tracked['frame_count'] - 1, 1)
        position = f"({tracked['position_x']}, {tracked['position_y']})"
        
        print(f"{face_id:<10} {position:<15} {tracked['motion_count']:<10} {tracked['frame_count']:<10} {motion_ratio*100:.1f}%")
        
        # Check if this face has significant motion and appears in enough frames
        if motion_ratio > THETA2 and tracked['frame_count'] >= (total_frames_selected * 0.3):
            if motion_ratio > max_motion_ratio:
                max_motion_ratio = motion_ratio
                active_speaker_id = face_id

    # ✅ Return the lip coordinates of the identified speaker
    if active_speaker_id is not None:
        speaker = face_tracker[active_speaker_id]
        print(f"\n✅ Speaker identified: Face {active_speaker_id}")
        print(f"   Position: ({speaker['position_x']}, {speaker['position_y']})")
        print(f"   Motion ratio: {max_motion_ratio*100:.1f}%")
        
        if speaker['lip_coords'] is not None:
            return speaker['lip_coords']
    
    # ✅ Fallback: Use the largest face (likely main character)
    print(f"\n⚠️ No clear speaker detected, using largest face as fallback")
    largest_face_id = max(face_tracker.keys(), key=lambda fid: face_tracker[fid]['area'])
    largest_face = face_tracker[largest_face_id]
    
    if largest_face['lip_coords'] is not None:
        print(f"   Using Face {largest_face_id} (largest)")
        return largest_face['lip_coords']
    
    print(f"❌ Unable to determine speaker")
    return (-1, -1)




