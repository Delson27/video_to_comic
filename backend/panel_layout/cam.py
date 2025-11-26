"""
Simplified module for getting frame coordinates.
Previously used ResNet-18 + SmoothGrad-CAM++ for ROI detection,
but coordinates were ignored in favor of full-frame display.
Now returns full frame dimensions directly for performance.
"""
from PIL import Image

def get_coordinates(img_path):
    """
    Returns full frame coordinates (no cropping).
    
    Previously computed ROI using ResNet-18 + CAM, but the output
    was ignored in centroid_crop() which uses full frame dimensions.
    Now directly returns full frame bounds for better performance.
    
    Args:
        img_path: Path to the image file
        
    Returns:
        tuple: (left, right, top, bottom) coordinates spanning the full frame
    """
    # Simply get image dimensions
    img = Image.open(img_path)
    width, height = img.size
    
    # Return full frame coordinates (no cropping)
    left = 0
    right = width
    top = 0
    bottom = height
    
    return left, right, top, bottom