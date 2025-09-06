# Import necessary libraries
import cv2
import numpy as np
from matplotlib import pyplot as plt
import os

def cartoonize(img_path):
    # Opens an image with cv2
    img = cv2.imread(img_path)

  # Convert to RGB for consistent processing
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Apply bilateral filter for smooth color regions
    img_bf = cv2.bilateralFilter(img_rgb, d=9, sigmaColor=75, sigmaSpace=75)

    # Convert to grayscale for edge detection
    img_gray = cv2.cvtColor(img_bf, cv2.COLOR_RGB2GRAY)

    # Apply Gaussian blur to reduce noise
    img_blur = cv2.GaussianBlur(img_gray, (5, 5), 0)

    # Use adaptive thresholding for cleaner edges
    img_edges = cv2.adaptiveThreshold(
        img_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, blockSize=9, C=2
    )

    # Dilate edges to make them bolder
    kernel = np.ones((3, 3), np.uint8)
    img_edges = cv2.dilate(img_edges, kernel, iterations=1)

    # Invert the edge mask for better outline effect
    img_edges_inv = cv2.bitwise_not(img_edges)

    # Color quantization using K-means
    img_reshaped = img_bf.reshape((-1, 3))
    img_reshaped = np.float32(img_reshaped)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    K = 12  # Adjusted for smoother colors
    _, label, center = cv2.kmeans(img_reshaped, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

    # Convert back to uint8 and reshape
    center = np.uint8(center)
    img_quantized = center[label.flatten()].reshape(img_bf.shape)

    # Convert edge mask to RGB and adjust for overlay
    img_edges_rgb = cv2.cvtColor(img_edges_inv, cv2.COLOR_GRAY2RGB)
    # Scale edges to create a colored outline effect
    img_edges_rgb = cv2.convertScaleAbs(img_edges_rgb, alpha=0.5, beta=0)

    # Combine quantized image with edges using addition to preserve colors
    cartoon = cv2.addWeighted(img_quantized, 0.7, img_edges_rgb, 0.3, 0.0)

    # Convert back to BGR for saving
    cartoon_bgr = cv2.cvtColor(cartoon, cv2.COLOR_RGB2BGR)

    # Save the image
    cv2.imwrite(img_path, cartoon_bgr)

# cartoonize()
    
def style_frames():
    for image in os.listdir("frames/final"):
        frame_path = os.path.join("frames",'final',image)
        cartoonize(frame_path)