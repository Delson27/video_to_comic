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

    def __init__(self,bubble_offset_x,bubble_offset_y,lip_x,lip_y,dialog,emotion,bubble_width=None,bubble_height=None):

        # Use dynamic sizes if provided, otherwise use defaults
        if bubble_width is None or bubble_height is None:
            # Calculate dynamic size based on text length
            bubble_width, bubble_height = self._calculate_bubble_size(dialog)
        
        self.bubble_width = bubble_width
        self.bubble_height = bubble_height
        tail_centre_x = bubble_width / 2
        tail_centre_y = bubble_height / 2
        self.dialog = dialog
        self.emotion = emotion

        self.bubble_offset_x = bubble_offset_x
        self.bubble_offset_y = bubble_offset_y
        # Provide aliases expected by other modules (bubble_x/bubble_y and lip_x/lip_y)
        self.bubble_x = bubble_offset_x
        self.bubble_y = bubble_offset_y
        self.lip_x = lip_x
        self.lip_y = lip_y
        
        angle = 0
         
        print(f"lipx = {lip_x} and lipy = {lip_y}")
        # If lip wasn't detected

        if(lip_x==-1 and lip_y == -1):
            angle = 0
            self.tail_offset_x = None
            self.tail_offset_y = None
        else:
            dx = lip_x - bubble_offset_x
            dy = lip_y - bubble_offset_y
            angle = np.arctan2(dy, dx)
            print(angle)

            tail_offset_x = None
            tail_offset_y = None

            self.tail_deg=np.degrees(angle)

            self.tail_offset_x = 80 * np.cos(angle)
            self.tail_offset_y = 80 * np.sin(angle)

    def _calculate_bubble_size(self, text):
        """
        Calculate optimal bubble size based on text length.
        Returns (width, height) tuple.
        """
        if not text or text.strip() == "":
            return 120, 60  # Minimum size for empty text
        
        # Remove action scene markers
        if text == "((action-scene))":
            return 120, 60
        
        # Character count
        char_count = len(text)
        
        # Base sizes (minimum)
        MIN_WIDTH = 100
        MIN_HEIGHT = 50
        MAX_WIDTH = 220  # Slightly larger than old fixed 200px
        MAX_HEIGHT = 110  # Slightly larger than old fixed 94px
        
        # Estimate required dimensions
        # Average character width at 10px font ≈ 6px
        # Assume max ~25 characters per line for readability
        chars_per_line = 25
        estimated_lines = max(1, char_count // chars_per_line)
        
        # Calculate width (based on text, but capped)
        if char_count <= chars_per_line:
            # Short text: width proportional to length
            width = max(MIN_WIDTH, min(char_count * 7 + 20, MAX_WIDTH))
        else:
            # Long text: use max width
            width = MAX_WIDTH
        
        # Calculate height (based on estimated lines)
        line_height = 14  # pixels per line (font-size 10px + spacing)
        padding = 20  # Top and bottom padding
        height = max(MIN_HEIGHT, min(estimated_lines * line_height + padding, MAX_HEIGHT))
        
        # Ensure oval shape (width should be > height for speech bubbles)
        if height > width * 0.8:
            height = int(width * 0.6)  # Maintain oval ratio
        
        # Round to nearest 5 for cleaner values
        width = round(width / 5) * 5
        height = round(height / 5) * 5
        
        return width, height


class Page:
    def __init__(self,panels,bubbles):
        self.panels = []
        self.bubbles = []

        # Safety check: ensure we don't exceed the length of either list
        max_length = min(len(panels), len(bubbles))
        
        for i in range(max_length):
            self.panels.append(panels[i].__dict__)  # Convert panel objects to dicts
            self.bubbles.append(bubbles[i].__dict__)