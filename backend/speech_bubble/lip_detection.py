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

def refine_lip_position_with_proximity(sub_index, video, crop_coords, black_x, black_y, bubble_position, save_debug=True):
    """
    Refine lip position for a specific subtitle by considering bubble position.
    Used for multi-speaker correction.
    
    Args:
        save_debug: If True, saves annotated debug image showing all faces and selected lip
    """
    keyframe_path = f"frames/final/frame{sub_index:03}.png"
    keyframe = cv2.imread(keyframe_path)
    
    if keyframe is None:
        return (-1, -1)
    
    gray = cv2.cvtColor(keyframe, cv2.COLOR_BGR2GRAY)
    face_rects = face_detector(gray, 1)
    
    if len(face_rects) <= 1:
        # Not a multi-speaker scene, no refinement needed
        return None
    
    print(f"✅ Refining lip position for frame {sub_index} with {len(face_rects)} faces")
    
    # Detect all face landmarks and find closest to bubble
    closest_lip = None
    min_distance = float('inf')
    closest_rect = None
    all_lips = []  # For debugging
    
    for rect in face_rects:
        landmark = landmark_detector(gray, rect)
        lip_x_raw = landmark.part(65).x
        lip_y_raw = landmark.part(65).y
        
        # Calculate distance from this lip to bubble position
        distance = sqrt(
            (lip_x_raw - bubble_position[0])**2 + 
            (lip_y_raw - bubble_position[1])**2
        )
        
        all_lips.append((lip_x_raw, lip_y_raw, distance))
        
        if distance < min_distance:
            min_distance = distance
            closest_lip = (lip_x_raw, lip_y_raw)
            closest_rect = rect
    
    if closest_lip:
        # Save debug visualization
        if save_debug:
            debug_img = keyframe.copy()
            
            # Draw all detected faces in red
            for rect in face_rects:
                x1, y1 = rect.left(), rect.top()
                x2, y2 = rect.right(), rect.bottom()
                cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            
            # Draw selected face in green
            if closest_rect:
                x1, y1 = closest_rect.left(), closest_rect.top()
                x2, y2 = closest_rect.right(), closest_rect.bottom()
                cv2.rectangle(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 3)
            
            # Draw all lip positions
            for lip_x_raw, lip_y_raw, dist in all_lips:
                cv2.circle(debug_img, (int(lip_x_raw), int(lip_y_raw)), 5, (0, 0, 255), -1)
                cv2.putText(debug_img, f"{dist:.0f}", (int(lip_x_raw) + 10, int(lip_y_raw)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # Draw selected lip in green
            cv2.circle(debug_img, (int(closest_lip[0]), int(closest_lip[1])), 8, (0, 255, 0), -1)
            
            # Draw bubble position reference
            bx, by = int(bubble_position[0]), int(bubble_position[1])
            cv2.circle(debug_img, (bx, by), 10, (255, 0, 0), 2)
            cv2.putText(debug_img, "Bubble", (bx + 15, by), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            
            # Save debug image
            debug_dir = "debug_lip_detection"
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, f"frame{sub_index:03}_refined.png")
            cv2.imwrite(debug_path, debug_img)
            print(f"⚙️ Debug image saved: {debug_path}")
        
        # Convert to CSS pixels
        origin = (crop_coords[sub_index - 1][0], crop_coords[sub_index - 1][2])
        x = closest_lip[0] - (origin[0] + black_x)
        y = closest_lip[1] - (origin[1] + black_y)
        x, y = convert_to_css_pixel(x, y, crop_coords[sub_index - 1])
        print(f"✅ Refined lip position: ({x:.1f}, {y:.1f}) at distance {min_distance:.1f}")
        return (x, y)
    
    return None


#crop_coords contain left,right,top,bottom of each frame
def get_lips(video, crop_coords, black_x, black_y):
    print(crop_coords)
    data=""
    with open("test1.srt") as f:
        data = f.read()
    subs = srt.parse(data)

    lips = {}
    for sub in subs:  
        keyframe_path = f"frames/final/frame{sub.index:03}.png"
        keyframe = cv2.imread(keyframe_path)
        gray = cv2.cvtColor(keyframe,cv2.COLOR_BGR2GRAY)   # Convert image into grayscale
        face_rects = face_detector(gray,1)             # Detect face
        print("\nsub:",sub.index)
        if sub.content == "((action-scene))":
            print("skipping action scene")
            lips[sub.index] = (-1,-1)
            continue

        if len(face_rects) < 1:                 # No face detected
            print("No face detected: ",sub)
            lips[sub.index] = (-1,-1)
            continue

        if len(face_rects) == 1:                # 1 face detected: Extract from keyframe itself
            rect = face_rects[0]
            landmark = landmark_detector(gray, rect)   # Detect face landmarks
            x,y = convert_to_css_pixel(landmark.part(65).x, landmark.part(65).y, crop_coords[sub.index - 1])
            lips[sub.index] = (x,y)
            continue

            
        if len(face_rects) > 1:                  # Too many face detected
            print("Too many face: sub_",sub.index,": ", len(face_rects))
            origin = (crop_coords[sub.index - 1][0] , crop_coords[sub.index - 1][2] ) # (left,top)
            lip_coords = get_multi_speaker_lips(sub,video,face_rects)
            if lip_coords == (-1,-1):
                lips[sub.index] = (-1,-1)
            else:
                x = lip_coords[0] - (origin[0] + black_x)
                y = lip_coords[1] - (origin[1] + black_y)
                x , y = convert_to_css_pixel(x,y,crop_coords[sub.index - 1])
                lips[sub.index] = (x,y)
            continue
    print(lips)
    return lips


def get_multi_speaker_lips(sub, video, keyframe_face_rects, bubble_position=None):
    start_time = sub.start.total_seconds()
    end_time = sub.end.total_seconds()
    keyframe_path = f"frames/final/frame{sub.index:03}.png"

    vid = cv2.VideoCapture(video)       # Read video
    frames_per_sec = vid.get(cv2.CAP_PROP_FPS)  # Number of frames per second
    # total_frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT)) 
    # frames_count = total_frames // frameRate  

    # Calculate the frame skip value
    select_index = floor(frames_per_sec / SAMPLE_RATE)  # Select every (skip_rate)'th position frames to get the SAMPLE_RATE number of frames per second
    start_frame = int(start_time * frames_per_sec)
    end_frame = int(end_time * frames_per_sec)

    vid.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    print("FPS,  select index = ", frames_per_sec, select_index)

    # Initialize frame counter
    current_frame = start_frame
    total_frames_selected = 0

    # Parse into frames 
    frame_buffer = []               # A list to hold frame images
    frame_buffer_color = []         # A list to hold original frame images
    while(current_frame<end_frame):
        success, frame = vid.read()                # Read frame
        if not success:
            break 
        if current_frame % select_index == 0:                          # Break if no frame to read left
            gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)   # Convert image into grayscale
            frame_buffer.append(gray)                  # Add image to the frame buffer
            frame_buffer_color.append(frame)
            total_frames_selected += 1
        current_frame += 1
    vid.release()

    prev_lip_dist = {}      #2D[i][j]
    lip_motion_count = {}   #1D[j]
    lip_coords = {}         #1D[j]
    avg_gap = {}            #2D[i][j]

    start_flag = False      #To skip the lip distance calculation for first frame

    for (i, image) in enumerate(frame_buffer):          # Iterate on frame buffer
        face_rects = face_detector(image,1)             # Detect face
        if len(face_rects) < 1:                 # No face detected
            print("No face detected: frame ",i)
            continue
        if len(face_rects) >= 1:                  # Too many face detected

            # Check if area of the first face rectangle is close to keyframe
            if not similar_to_keyframe(face_rects, keyframe_face_rects):
                print("frame not similar: ",i)
                continue

            largest_face = max(face_rects, key=lambda rect: rect.area())
            print("largest face: ", largest_face)

            avg_gap[i] = {}
            prev_lip_dist[i] = {}
            for (j,rect) in enumerate(face_rects):
                if (rect.area() / largest_face.area()) < FACE_AREA:     #Consider lip only if face area crosses a threshold(ROI)
                    print("Lip skipped: ", j, rect)
                    continue

                prev_lip_dist[i][j] = 0
                landmark = landmark_detector(image, rect)   # Detect face landmarks
                # landmark = shape_to_list(landmark)

                part_61 = (landmark.part(61).x,landmark.part(61).y)
                part_67 = (landmark.part(67).x,landmark.part(67).y)
                part_62 = (landmark.part(62).x,landmark.part(62).y)
                part_66 = (landmark.part(66).x,landmark.part(66).y)
                part_63 = (landmark.part(63).x,landmark.part(63).y)
                part_65 = (landmark.part(65).x,landmark.part(65).y)
                A = dist(part_61, part_67)
                B = dist(part_62, part_66)
                C = dist(part_63, part_65)

                avg_gap[i][j] = (A + B + C) / 3.0

                # Store lip coordinate if encountered for first time
                if j not in lip_coords:
                    lip_coords[j] = part_65

                # Loop runs for the first time
                if start_flag==False:
                    prev_lip_dist[i][j] = avg_gap[i][j]
                    start_flag = True
                    continue
                
                # Check if lip distance between continous frame is above threshold, if so increase lip count
                print("Difference for frame {0}, lip {1}: {2}".format( i, j, abs(avg_gap[i][j] - prev_lip_dist[i][j])) )
                if abs(avg_gap[i][j] - prev_lip_dist[i][j]) > THETA1:
                    lip_motion_count[j] = lip_motion_count.get(j,0) + 1
                prev_lip_dist[i][j] = avg_gap[i][j]

   
    print("Lip motion count, total_frames_selected = ", lip_motion_count, total_frames_selected)
    
    # ✅ IMPROVED: Choose speaker based on both lip movement AND proximity to bubble
    try:
        if not lip_motion_count:
            # No lip motion detected at all
            if bubble_position and lip_coords:
                # Fallback: Choose face closest to bubble position
                print("⚠️ No lip motion detected, using proximity-based selection")
                closest_face = min(
                    lip_coords.items(),
                    key=lambda item: sqrt(
                        (item[1][0] - bubble_position[0])**2 + 
                        (item[1][1] - bubble_position[1])**2
                    )
                )
                return closest_face[1]
            return (-1, -1)
        
        # Find faces with significant lip movement
        active_speakers = [
            idx for idx, count in lip_motion_count.items()
            if count / (total_frames_selected - 1) > THETA2
        ]
        
        if not active_speakers:
            print("⚠️ No speakers passed motion threshold")
            # Fallback: Use face with most movement, or closest to bubble
            if bubble_position and lip_coords:
                closest_face = min(
                    lip_motion_count.items(),
                    key=lambda item: sqrt(
                        (lip_coords[item[0]][0] - bubble_position[0])**2 + 
                        (lip_coords[item[0]][1] - bubble_position[1])**2
                    )
                )
                return lip_coords[closest_face[0]]
            return (-1, -1)
        
        if len(active_speakers) == 1:
            # Single active speaker detected
            print(f"✅ Single speaker detected: face {active_speakers[0]}")
            return lip_coords[active_speakers[0]]
        
        # Multiple active speakers - choose based on proximity to bubble if available
        if bubble_position:
            print(f"⚠️ Multiple speakers detected: {active_speakers}, using proximity")
            closest_speaker = min(
                active_speakers,
                key=lambda idx: sqrt(
                    (lip_coords[idx][0] - bubble_position[0])**2 + 
                    (lip_coords[idx][1] - bubble_position[1])**2
                )
            )
            print(f"✅ Selected speaker {closest_speaker} (closest to bubble)")
            return lip_coords[closest_speaker]
        else:
            # No bubble position available, use most active speaker
            max_lip_index = max(lip_motion_count, key=lip_motion_count.get)
            print(f"✅ Selected speaker {max_lip_index} (most lip movement)")
            return lip_coords[max_lip_index]
            
    except ValueError:
        return (-1, -1)
    except ZeroDivisionError:
        return (-1, -1)




