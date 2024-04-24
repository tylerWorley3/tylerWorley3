import cv2
import numpy as np
from PIL import Image, ImageDraw

# Function to draw our lines
def draw_lines(img, lines, color=[255, 0, 0], thickness=3):
    if lines is not None:
        for line in lines:
            for x1, y1, x2, y2 in line:
                cv2.line(img, (x1, y1), (x2, y2), color, thickness)

image_path = 'Sidewalk/Sidewalk_Img.png'

# Reload the image in case the previous step altered the original
image_cv2 = cv2.imread(image_path)

# Convert to grayscale for edge detection
gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)

# Apply GaussianBlur to help with edge detection
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# Apply Canny edge detector
edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

# Now let's focus on the specific area where the sidewalk edge should be
# We can mask out the top part of the image to avoid detecting tree branches and far edges
height, width = edges.shape
mask = np.zeros_like(edges)
polygon_vertices = [
    (int(0.01 * width), height),  # Bottom-left corner, slightly inwards
    (int(0.01 * width), int(1 * height)),  # Move up along the left edge
    (int(0.45 * width), int(0.55 * height)),  # Continue along the curve
    (int(0.6 * width), int(0.52 * height)),  # Approach the right edge
    #(width, int(0.5 * height)),  # Top-right corner, middle height
    (width, height)  # Bottom-right corner
]

# Create an entirely black mask
mask = np.zeros_like(gray)

# Fill the ROI in the mask with white
cv2.fillPoly(mask, np.array([polygon_vertices], np.int32), 255)

# Bitwise operation to keep only the ROI in the original image
masked_image = cv2.bitwise_and(gray, mask)

# Apply Canny edge detection on the masked image
roi_edges = cv2.Canny(masked_image, 50, 150, apertureSize=3)

# Detect lines using HoughLinesP in the ROI
roi_lines = cv2.HoughLinesP(roi_edges, 1, np.pi / 180, threshold=50, minLineLength=50, maxLineGap=50)

# Draw the lines found in the ROI on the original (colored) image
sidewalk_roi_edges_img = image_cv2.copy()
draw_lines(sidewalk_roi_edges_img, roi_lines, color=[0, 0, 255], thickness=2)

# Convert the image to RGB before saving with PIL
sidewalk_roi_edges_img_rgb = cv2.cvtColor(sidewalk_roi_edges_img, cv2.COLOR_BGR2RGB)
sidewalk_roi_image_with_edges = Image.fromarray(sidewalk_roi_edges_img_rgb)

# Save the resulting image
roi_edge_detected_image_path = 'sidewalk_roi_image_with_edges2.png'
sidewalk_roi_image_with_edges.save(roi_edge_detected_image_path)

roi_edge_detected_image_path