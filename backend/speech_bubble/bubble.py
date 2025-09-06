import math
import json
import srt
import pickle
from backend.speech_bubble.lip_detection import get_lips
from backend.speech_bubble.bubble_placement import get_bubble_position
from backend.speech_bubble.bubble_shape import get_bubble_type
from backend.class_def import bubble
import threading


def bubble_create(video, crop_coords, black_x, black_y):

    bubbles = []


    # def bubble_create(bubble_cord,lip_cord,page_template):
    data=""
    with open("test1.srt") as f:
        data=f.read()
    subs=srt.parse(data)


    # Reading CAM data from dump
    CAM_data = None
    with open('CAM_data.pkl', 'rb') as f:
        CAM_data = pickle.load(f)

    lips = get_lips(video, crop_coords,black_x,black_y)
    # Dumping lips
    with open('lips.pkl', 'wb') as f:
        pickle.dump(lips, f)

    # # Reading lips
    # lips=None
    # with open('lips.pkl', 'rb') as f:
    #     lips = pickle.load(f)
    
    # emotion_thread.join()
    # print("Detected emotions:", emotions)


    for sub in subs:
        lip_x = lips[sub.index][0]
        lip_y = lips[sub.index][1]

        idx=min(sub.index-1,len(CAM_data)-1)
        idx_crop = min(idx, len(crop_coords) - 1)
        idx_cam = min(idx, len(CAM_data) - 1)
        
        # Determine if this is a normal page or last page
        # You'll need to pass this information through the pipeline
        is_normal_page = True  # This needs to be determined based on your logic
        
        bubble_x, bubble_y = get_bubble_position(crop_coords[idx_crop], CAM_data[idx_cam], is_normal_page)

        dialogue = sub.content
        emotion = get_bubble_type(dialogue)
        print(f'||emotion:{emotion}||')


        temp = bubble(bubble_x, bubble_y,lip_x,lip_y,sub.content,emotion)
        bubbles.append(temp)

    return bubbles









