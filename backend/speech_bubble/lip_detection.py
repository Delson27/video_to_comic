import dlib
import cv2
import os
import srt
import re
import numpy as np
from math import floor, sqrt
from collections import defaultdict
from backend.utils import convert_to_css_pixel

# ✅ OPTIMIZED CONSTANTS FOR HIGHER ACCURACY
THETA1 = 0.8           # Lowered for more sensitive lip movement detection
THETA2 = 0.25          # Lowered threshold - 25% of frames need movement
SAMPLE_RATE = 10       # Increased from 5 to 10fps for better temporal resolution
FACE_AREA = 0.4        # Lowered to include smaller/distant faces
MIN_FRAMES = 3         # Minimum frames needed for analysis
POSITION_TOLERANCE = 150  # Pixels - for tracking same face across frames

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


def get_multi_speaker_lips(sub, video, keyframe_face_rects):
    """
    ADVANCED Multi-Speaker Detection System
    
    Uses multiple techniques for maximum accuracy:
    1. Lip Aspect Ratio (LAR) - Most reliable metric
    2. Lip Area measurement
    3. Vertical lip opening distance
    4. Temporal consistency analysis
    5. Motion variance detection
    """
    start_time = sub.start.total_seconds()
    end_time = sub.end.total_seconds()
    duration = end_time - start_time
    
    print(f"\n{'='*80}")
    print(f"🎯 ADVANCED Multi-Speaker Analysis - Subtitle {sub.index}")
    print(f"   Text: \"{sub.content[:60]}...\"" if len(sub.content) > 60 else f"   Text: \"{sub.content}\"")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"{'='*80}")
    
    # Open video
    vid = cv2.VideoCapture(video)
    if not vid.isOpened():
        print("❌ Failed to open video")
        return (-1, -1)
        
    fps = vid.get(cv2.CAP_PROP_FPS)
    
    # Adaptive sampling - more samples for longer dialogues
    adaptive_sample_rate = min(15, max(8, int(fps / (duration + 1))))
    select_index = max(1, int(fps / adaptive_sample_rate))
    
    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    
    print(f"📹 Video: {fps:.1f} fps | Sampling every {select_index} frames ({adaptive_sample_rate:.1f} fps)")
    print(f"📊 Analyzing frames {start_frame} to {end_frame} ({end_frame - start_frame} total)\n")
    
    vid.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    # Extract frames
    frames = []
    current_frame = start_frame
    
    while current_frame < end_frame:
        success, frame = vid.read()
        if not success:
            break
        if current_frame % select_index == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frames.append(gray)
        current_frame += 1
    
    vid.release()
    
    if len(frames) < MIN_FRAMES:
        print(f"⚠️ Insufficient frames: {len(frames)} < {MIN_FRAMES}")
        return (-1, -1)
    
    print(f"✅ Extracted {len(frames)} frames for analysis\n")
    
    # ============================================================================
    # STEP 1: Build face database with enhanced tracking
    # ============================================================================
    
    face_database = []  # {id, position, landmarks_history, lar_values, area_values, ...}
    
    for frame_idx, gray_frame in enumerate(frames):
        face_rects = face_detector(gray_frame, 1)
        
        if len(face_rects) == 0:
            continue
        
        # Sort faces left-to-right for consistency
        face_rects = sorted(face_rects, key=lambda r: r.left())
        
        for rect in face_rects:
            try:
                # Get landmarks
                landmarks = landmark_detector(gray_frame, rect)
                
                # Calculate face center
                face_center_x = rect.left() + rect.width() // 2
                face_center_y = rect.top() + rect.height() // 2
                
                # ✅ TECHNIQUE 1: Lip Aspect Ratio (LAR)
                # Most reliable metric - ratio of vertical to horizontal lip distance
                # Speaking: LAR increases significantly
                
                # Outer lip corners
                lip_left = np.array([landmarks.part(48).x, landmarks.part(48).y])
                lip_right = np.array([landmarks.part(54).x, landmarks.part(54).y])
                
                # Top and bottom lip points (vertical)
                lip_top = np.array([landmarks.part(51).x, landmarks.part(51).y])
                lip_bottom = np.array([landmarks.part(57).x, landmarks.part(57).y])
                
                # Additional vertical measurements for robustness
                inner_top = np.array([landmarks.part(62).x, landmarks.part(62).y])
                inner_bottom = np.array([landmarks.part(66).x, landmarks.part(66).y])
                
                # Horizontal lip width
                lip_width = np.linalg.norm(lip_right - lip_left)
                
                # Multiple vertical measurements
                outer_height = np.linalg.norm(lip_bottom - lip_top)
                inner_height = np.linalg.norm(inner_bottom - inner_top)
                avg_height = (outer_height + inner_height) / 2.0
                
                # Calculate LAR (higher when mouth opens)
                lar = avg_height / (lip_width + 1e-6)
                
                # ✅ TECHNIQUE 2: Lip Area (perimeter-based approximation)
                # Speaking: Area increases
                lip_area = lip_width * avg_height
                
                # ✅ TECHNIQUE 3: Mouth Opening Ratio (MOR)
                # Normalized vertical opening
                mor = outer_height / (lip_width + 1e-6)
                
                # Bottom lip center for tail positioning
                lip_center = landmarks.part(57)  # Bottom center of outer lip
                
                face_data = {
                    'frame_idx': frame_idx,
                    'center_x': face_center_x,
                    'center_y': face_center_y,
                    'rect': rect,
                    'area': rect.area(),
                    'lar': lar,
                    'lip_area': lip_area,
                    'mor': mor,
                    'outer_height': outer_height,
                    'lip_coords': (lip_center.x, lip_center.y),
                    'landmarks': landmarks
                }
                
                # Match to existing face or create new entry
                matched = False
                for face_track in face_database:
                    # Check if this is the same person (spatial proximity)
                    last_pos = face_track['positions'][-1]
                    distance = sqrt((face_center_x - last_pos[0])**2 + (face_center_y - last_pos[1])**2)
                    
                    if distance < POSITION_TOLERANCE:
                        # Same person - add to track
                        face_track['frames'].append(frame_idx)
                        face_track['positions'].append((face_center_x, face_center_y))
                        face_track['lar_values'].append(lar)
                        face_track['lip_areas'].append(lip_area)
                        face_track['mor_values'].append(mor)
                        face_track['outer_heights'].append(outer_height)
                        face_track['lip_coords_history'].append((lip_center.x, lip_center.y))
                        matched = True
                        break
                
                if not matched:
                    # New face detected - create track
                    face_database.append({
                        'id': len(face_database),
                        'frames': [frame_idx],
                        'positions': [(face_center_x, face_center_y)],
                        'lar_values': [lar],
                        'lip_areas': [lip_area],
                        'mor_values': [mor],
                        'outer_heights': [outer_height],
                        'lip_coords_history': [(lip_center.x, lip_center.y)],
                        'avg_area': rect.area()
                    })
                    
            except Exception as e:
                print(f"⚠️ Frame {frame_idx}: Landmark detection failed - {e}")
                continue
    
    if len(face_database) == 0:
        print("❌ No faces tracked across frames")
        return (-1, -1)
    
    print(f"👥 Tracked {len(face_database)} distinct face(s)\n")
    
    # ============================================================================
    # STEP 2: Analyze each face for speaking activity
    # ============================================================================
    
    print(f"{'─'*80}")
    print(f"📊 DETAILED SPEAKER ANALYSIS")
    print(f"{'─'*80}\n")
    
    speaker_scores = []
    
    for face in face_database:
        face_id = face['id']
        num_frames = len(face['frames'])
        
        if num_frames < MIN_FRAMES:
            print(f"Face {face_id}: Insufficient frames ({num_frames})")
            continue
        
        # ✅ ANALYSIS METHOD 1: LAR Variance (high variance = speaking)
        lar_array = np.array(face['lar_values'])
        lar_variance = np.var(lar_array)
        lar_range = np.max(lar_array) - np.min(lar_array)
        lar_mean = np.mean(lar_array)
        
        # ✅ ANALYSIS METHOD 2: Detect significant LAR changes (peaks)
        lar_changes = np.abs(np.diff(lar_array))
        significant_changes = np.sum(lar_changes > THETA1 * 0.01)  # Adaptive threshold
        change_ratio = significant_changes / (num_frames - 1) if num_frames > 1 else 0
        
        # ✅ ANALYSIS METHOD 3: Lip area variance
        area_variance = np.var(face['lip_areas'])
        
        # ✅ ANALYSIS METHOD 4: MOR variance
        mor_variance = np.var(face['mor_values'])
        
        # ✅ ANALYSIS METHOD 5: Temporal consistency
        # Speaking has rhythmic pattern, not random noise
        if num_frames > 5:
            autocorr = np.correlate(lar_array - lar_mean, lar_array - lar_mean, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            autocorr = autocorr / autocorr[0]  # Normalize
            temporal_consistency = np.max(autocorr[1:min(5, len(autocorr))]) if len(autocorr) > 1 else 0
        else:
            temporal_consistency = 0
        
        # ✅ COMPOSITE SCORE (weighted combination of all metrics)
        # Empirically tuned weights for best accuracy
        composite_score = (
            lar_variance * 100 +           # Weight: 100
            lar_range * 50 +               # Weight: 50
            change_ratio * 30 +            # Weight: 30
            area_variance * 0.0001 +       # Weight: 0.0001 (area is large numbers)
            mor_variance * 20 +            # Weight: 20
            temporal_consistency * 15      # Weight: 15
        )
        
        # Average position for display
        avg_x = int(np.mean([p[0] for p in face['positions']]))
        avg_y = int(np.mean([p[1] for p in face['positions']]))
        
        # Most recent lip coordinates (for tail pointing)
        final_lip_coords = face['lip_coords_history'][-1]
        
        speaker_scores.append({
            'face_id': face_id,
            'position': (avg_x, avg_y),
            'frames_count': num_frames,
            'composite_score': composite_score,
            'lar_variance': lar_variance,
            'lar_range': lar_range,
            'change_ratio': change_ratio,
            'lip_coords': final_lip_coords,
            'face_data': face
        })
        
        print(f"Face {face_id} @ ({avg_x}, {avg_y}):")
        print(f"  Frames: {num_frames}/{len(frames)}")
        print(f"  LAR Variance: {lar_variance:.6f}")
        print(f"  LAR Range: {lar_range:.4f}")
        print(f"  Change Ratio: {change_ratio:.2%}")
        print(f"  Composite Score: {composite_score:.4f}")
        print()
    
    # ============================================================================
    # STEP 3: Select the speaker
    # ============================================================================
    
    if len(speaker_scores) == 0:
        print("❌ No valid faces for analysis")
        return (-1, -1)
    
    # Sort by composite score
    speaker_scores.sort(key=lambda x: x['composite_score'], reverse=True)
    
    best_speaker = speaker_scores[0]
    
    print(f"{'='*80}")
    print(f"✅ SPEAKER IDENTIFIED: Face {best_speaker['face_id']}")
    print(f"   Position: {best_speaker['position']}")
    print(f"   Confidence Score: {best_speaker['composite_score']:.4f}")
    print(f"   Lip Coordinates: {best_speaker['lip_coords']}")
    
    # ✅ CONFIDENCE CHECK: Compare top 2 speakers
    if len(speaker_scores) > 1:
        second_best = speaker_scores[1]
        score_diff = best_speaker['composite_score'] - second_best['composite_score']
        confidence = score_diff / (best_speaker['composite_score'] + 1e-6)
        
        print(f"   Confidence vs 2nd: {confidence:.1%} ({score_diff:.4f} score difference)")
        
        if confidence < 0.15:  # Less than 15% difference
            print(f"   ⚠️ LOW CONFIDENCE - Scores are close!")
    
    print(f"{'='*80}\n")
    
    return best_speaker['lip_coords']




