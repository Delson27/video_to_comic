import math
import numpy as np
class panel:
    def __init__(self,image,row_span,col_span):
       self.image = image
       self.row_span = row_span
       self.col_span = col_span


# class bubble:

#     def __init__(self,bubble_offset_x,bubble_offset_y,lip_x,lip_y,dialog):

#         bubble_width=200
#         bubble_height=94
#         tail_centre_x=100
#         tail_centre_y=47
#         self.dialog = dialog

#         self.bubble_offset_x = bubble_offset_x
#         self.bubble_offset_y = bubble_offset_y
        
#         temp = 0
#         angle = 0
#         try:
#             temp = math.degrees(math.atan((bubble_offset_y-lip_y) / (bubble_offset_x-lip_x)))
#         except ZeroDivisionError:
#             temp = 45

#         if(bubble_offset_y>lip_y):
#             # tail top
#             if(bubble_offset_x>lip_x):
#                 #tail left
#                 angle=180-temp
#             elif(bubble_offset_x<lip_x):
#                 #tail right
#                 angle=180-temp
#         elif(bubble_offset_y<=lip_y):
#             #tail bottom
#             if(bubble_offset_x>lip_x):
#                 #tail left
#                 angle=-temp
#             elif(bubble_offset_x<lip_x):
#                 #tail right
#                 angle=360-temp

#         print(angle)
#         tail_offset_x = None
#         tail_offset_y = None

#         self.tail_deg=angle

#         if(bubble_offset_y>lip_y):
#             # tail top
#             if(bubble_offset_x>lip_x):
#                 #tail left
#                 tail_offset_x=tail_centre_x-50
#                 tail_offset_y=tail_centre_y-23
#             elif(bubble_offset_x<lip_x):
#                 #tail right
#                 tail_offset_x=tail_centre_x+50
#                 tail_offset_y=tail_centre_y-23
#         elif(bubble_offset_y<=lip_y):
#             #tail bottom
#             if(bubble_offset_x>lip_x):
#                 #tail left
#                 tail_offset_x=tail_centre_x-50
#                 tail_offset_y=tail_centre_y+23
#             elif(bubble_offset_x<lip_x):
#                 #tail right
#                 tail_offset_x=tail_centre_x+50
#                 tail_offset_y=tail_centre_y+23

#         self.tail_offset_x = tail_offset_x
#         self.tail_offset_y = tail_offset_y

class bubble:

    def __init__(
        self,
        bubble_offset_x,
        bubble_offset_y,
        lip_x,
        lip_y,
        dialog,
        emotion,
        bubble_width,
        bubble_height,
        panel_type,
        panel_width,
        panel_height,
    ):

        self.dialog = dialog
        self.emotion = emotion

        # Base bubble placement (in CSS pixels calculated on backend)
        self.bubble_offset_x = bubble_offset_x
        self.bubble_offset_y = bubble_offset_y
        self.bubble_x = bubble_offset_x
        self.bubble_y = bubble_offset_y

        # Lip coordinates for tail placement
        self.lip_x = lip_x
        self.lip_y = lip_y

        # Persist panel metadata so front-end can rescale positions when layout changes
        self.panel_type = panel_type
        self.panel_width = panel_width
        self.panel_height = panel_height

        # Persist bubble size calculated on backend (used for responsive scaling)
        self.bubble_width = bubble_width
        self.bubble_height = bubble_height

        print(f"lipx = {lip_x} and lipy = {lip_y}")

        if lip_x == -1 and lip_y == -1:
            # Missing lip detection – hide tail
            self.tail_offset_x = None
            self.tail_offset_y = None
            self.tail_deg = 0
        else:
            dx = lip_x - bubble_offset_x
            dy = lip_y - bubble_offset_y
            angle = np.arctan2(dy, dx)
            print(angle)

            self.tail_deg = np.degrees(angle)

            # Store tail offsets relative to bubble origin (will be rescaled on front-end)
            tail_length = 80
            self.tail_offset_x = tail_length * np.cos(angle)
            self.tail_offset_y = tail_length * np.sin(angle)
            self.tail_length = tail_length


class Page:
    def __init__(self,panels,bubbles):
        self.panels = []
        self.bubbles = []

        # Safety check: ensure we don't exceed the length of either list
        max_length = min(len(panels), len(bubbles))
        
        for i in range(max_length):
            self.panels.append(panels[i].__dict__)  # Convert panel objects to dicts
            self.bubbles.append(bubbles[i].__dict__)