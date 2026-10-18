from ppadb.client import Client
import numpy as np
import cv2
import matplotlib.pyplot as plt
from PIL import Image, ImageFilter
import torch
import torchvision.transforms as transforms
from PIL import Image
import torch.nn.functional as F
import torch.nn as nn
import uuid
from datetime import datetime
import os

from config import class_labels, shape_classes, cell_points




class ShapeClassifier(nn.Module):
    def __init__(self, num_classes):
        super(ShapeClassifier, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.fc1 = nn.Linear(64 * 16 * 16, 128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

model = ShapeClassifier(41) ### number of shapes

def get_single_shape(image, model):

    device = torch.device("cpu")

    transform = transforms.Compose(
        [
            transforms.Resize((64, 64)),
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,)),
        ]
    )

    image = Image.open(image).convert("RGB")
    image = transform(image).unsqueeze(0) 

    image = image.to(device)
    model.eval()

    with torch.no_grad():
        output = model(image)
        probabilities = F.softmax(output, dim=1)
        predicted_class = torch.argmax(probabilities, dim=1).item()

    return class_labels[predicted_class]


def get_shapes(image):
    if image is None:
        raise Exception("No new image to process.")

    image_np = np.frombuffer(image, dtype=np.uint8)
    image_cv2 = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    if image_cv2 is None:
        raise RuntimeError("Failed to decode image. Ensure ADB screenshot works.")

    y1, y2 = 1600, 2000
    shapes_region = image_cv2[y1:y2, :]

    h, w, _ = shapes_region.shape
    overlap = int(w * 0.05)
    side_width = int((w - (w // 3)) // 2)
    middle_width = w - (2 * side_width)

    sections = [
        shapes_region[:, 0 : side_width + overlap],
        shapes_region[:, side_width : side_width + middle_width],
        shapes_region[:, side_width + middle_width - overlap : w],
    ]

    save_folder = "shapes_dataset/"
    os.makedirs(save_folder, exist_ok=True)
    random_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_paths = []
    for i, section in enumerate(sections):
        filename = os.path.join(
            save_folder, f"shape_{timestamp}_{random_id}_part{i+1}.png"
        )
        cv2.imwrite(filename, section)
        file_paths.append(filename)

    return tuple(file_paths) 


def get_board(image):

    if image:
        image = cv2.imread("screen.png")  ###3
    else:
        raise Exception("No new image to process.")

    empty_color = np.array([66, 36, 25])
    tolerance = 15

    cell_status = []

    for i, (x, y) in enumerate(cell_points):
        sample_offsets = [(-3, 0), (3, 0), (0, -3), (0, 3), (0, 0)]
        sampled_colors = []

        for dx, dy in sample_offsets:
            sx, sy = min(image.shape[1] - 1, max(0, x + dx)), min(
                image.shape[0] - 1, max(0, y + dy)
            )
            sampled_colors.append(image[sy, sx])

        sampled_colors = np.array(sampled_colors)

        median_color = np.median(sampled_colors, axis=0).astype(int)

        is_empty = np.all(np.abs(median_color - empty_color) < tolerance)
        cell_status.append(1 if not is_empty else 0) 

        status = "EMPTY" if is_empty else "OCCUPIED"

        marker_color = (0, 255, 0) if is_empty else (0, 0, 255)
        cv2.circle(image, (x, y), 5, marker_color, -1)

    GRID_COLS = 8
    grid_matrix = np.array(cell_status, dtype=int).reshape(-1, GRID_COLS)

    return grid_matrix


def print_board(grid_matrix):
    for row in grid_matrix:
        print("".join("🟥" if cell == 1 else "  " for cell in row)) 

def print_shape(shape_name):
    if shape_name not in shape_classes:
        raise ValueError(f"Shape '{shape_name}' not found.")

    shape = shape_classes[shape_name]["shape"]

    # Convert set to NumPy array if necessary
    if isinstance(shape, set):
        shape = sorted(shape, key=lambda x: (len(x), x))
        shape = np.array(shape)  # Convert back to NumPy array

    # Ensure shape is a NumPy array
    if not isinstance(shape, np.ndarray):
        shape = np.array(shape)

    for row in shape:
        print("".join("🟥" if cell == 1 else "  " for cell in row))


def print_shapes_inline(shape1_name, shape2_name, shape3_name):
    shapes = []
    
    for shape_name in [shape1_name, shape2_name, shape3_name]:
        if shape_name not in shape_classes:
            raise ValueError(f"Shape '{shape_name}' not found.")
        shape = shape_classes[shape_name]["shape"]
        
        if isinstance(shape, set):
            shape = sorted(shape, key=lambda x: (len(x), x))
            shape = np.array(shape) 

        shapes.append(shape)

    max_height = max(shape.shape[0] for shape in shapes)

    normalized_shapes = []
    for shape in shapes:
        height, width = shape.shape
        if height < max_height:
            padding = np.zeros((max_height - height, width), dtype=int)
            shape = np.vstack((padding, shape)) 
        normalized_shapes.append(shape)

    for rows in zip(*normalized_shapes):
        print("  ".join("".join("🟥" if cell == 1 else "  " for cell in row) for row in rows))




