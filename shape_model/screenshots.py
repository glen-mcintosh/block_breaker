"""Original experiments from shape_model/screenshots.ipynb, in their original cell order.

Run from shape_model.
Execution preserves the original capture, plotting, and file-writing behavior.
"""

def main():
    # Former notebook cell 1
    import os
    import uuid
    import numpy as np
    import cv2
    import matplotlib.pyplot as plt
    from datetime import datetime
    from ppadb.client import Client as AdbClient

    # **Connect to ADB device**
    adb = AdbClient(host="127.0.0.1", port=5037)
    device = adb.devices()[0]  # Get the first connected device

    # **Take a screenshot from the device**
    image_bytes = device.screencap()

    # **Ensure valid image data**
    if not image_bytes:
        raise RuntimeError("Failed to capture screenshot from device.")

    # **Convert to NumPy array & decode with OpenCV**
    image_np = np.frombuffer(image_bytes, dtype=np.uint8)  # Convert bytes to NumPy array
    image_cv2 = cv2.imdecode(image_np, cv2.IMREAD_COLOR)  # Decode image for OpenCV

    # **Ensure the image is correctly loaded**
    if image_cv2 is None:
        raise RuntimeError("Failed to decode image. Ensure ADB screenshot works.")

    # **Define the region to crop (Adjust Y-range based on game)**
    y1, y2 = 1600, 2000  # Adjust these values to capture the shapes
    shapes_region = image_cv2[y1:y2, :]  # Crop using NumPy slicing

    # **Split the image into 3 vertical sections**
    h, w, _ = shapes_region.shape

    # **Define new split logic (Make middle skinnier but keep full height)**
    overlap = int(w * 0.0)  # 5% overlap into middle section
    side_width = int((w - (w // 3)) // 2)  # Calculate left/right width correctly
    middle_width = w - (2 * side_width)  # Ensure middle is smaller

    # **Manually define three sections with correct overlaps**
    sections = [
        shapes_region[:, 0:side_width + overlap],  # Left section (slightly extends into middle)
        shapes_region[:, side_width:side_width + middle_width],  # Middle section (narrowest)
        shapes_region[:, side_width + middle_width - overlap:w]  # Right section (slightly extends into middle)
    ]

    # **Convert BGR to RGB for Notebook Display**
    sections_rgb = [cv2.cvtColor(sec, cv2.COLOR_BGR2RGB) for sec in sections]

    # **Generate a unique filename base**
    save_folder = "shapes_dataset/"
    os.makedirs(save_folder, exist_ok=True)  # Create folder if it doesn't exist

    random_id = uuid.uuid4().hex[:8]  # Short unique ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Timestamp

    # **Save the three sections separately**
    for i, section in enumerate(sections):
        filename = os.path.join(save_folder, f"shape_{timestamp}_{random_id}_part{i+1}.png")
        cv2.imwrite(filename, section)
        print(f"Saved section {i+1}: {filename}")

    # **Display all three sections inside the notebook**
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    titles = ["Left", "Middle", "Right"]

    for i, ax in enumerate(axes):
        ax.imshow(sections_rgb[i])
        ax.axis("off")
        ax.set_title(f"{titles[i]} Section")

    plt.show()



    # Former notebook cell 2
    import torch
    import torchvision.transforms as transforms
    import torchvision.datasets as datasets
    from torch.utils.data import DataLoader, random_split

    # **Check if GPU is available**
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # **Define transformations**
    transform = transforms.Compose([
        transforms.Resize((64, 64)),  # Resize images to match model input
        transforms.ToTensor(),  # Convert images to PyTorch tensors
        transforms.Normalize((0.5,), (0.5,))  # Normalize pixel values
    ])

    # **Dataset Path (Update this if needed)**
    dataset_path = "shapes/"

    # **Load dataset**
    full_dataset = datasets.ImageFolder(root=dataset_path, transform=transform)

    # **Split dataset into Training (80%) & Validation (20%)**
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    # **Create DataLoaders**
    BATCH_SIZE = 32  # Adjust based on memory
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # **Print class labels (for debugging)**
    print("Shape Classes:", full_dataset.classes)


    import torch.nn as nn
    import torch.optim as optim

    # **Define CNN Model**
    class ShapeClassifier(nn.Module):
        def __init__(self, num_classes):
            super(ShapeClassifier, self).__init__()
            self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
            self.pool = nn.MaxPool2d(2, 2)
            self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
            self.fc1 = nn.Linear(64 * 16 * 16, 128)  # Adjust based on image size
            self.fc2 = nn.Linear(128, num_classes)  # Output classes based on dataset

        def forward(self, x):
            x = self.pool(torch.relu(self.conv1(x)))
            x = self.pool(torch.relu(self.conv2(x)))
            x = x.view(x.size(0), -1)  # Flatten before FC layer
            x = torch.relu(self.fc1(x))
            x = self.fc2(x)
            return x

    # **Initialize Model**
    num_classes = len(full_dataset.classes)  # Get number of shape classes
    model = ShapeClassifier(num_classes).to(device)

    # **Define Loss Function & Optimizer**
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005)

    # **Training Loop**
    EPOCHS = 20  # Adjust as needed
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

        print(f"Epoch [{epoch+1}/{EPOCHS}], Loss: {running_loss / len(train_loader):.4f}")

    print("Training Complete!")


    # **Evaluate Model Accuracy**
    model.eval()
    correct = 0
    total = 0

    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    accuracy = 100 * correct / total
    print(f"Validation Accuracy: {accuracy:.2f}%")




    # Former notebook cell 3
    torch.save(model.state_dict(), "shape_classifier.pth")
    print("Model saved successfully!")


    # Former notebook cell 4
    # Load Model for Inference
    import torch
    import torchvision.transforms as transforms
    from PIL import Image
    import torch.nn.functional as F

    # **Load the trained model**
    model = ShapeClassifier(num_classes).to(device)  # Match input device
    model.load_state_dict(torch.load("shape_classifier.pth"))
    model.eval()  # Set to evaluation mode
    print("Model loaded successfully!")

    # **Define the function to predict an image**
    def predict_image(image_path, model):
    
    
        transform = transforms.Compose([
            transforms.Resize((64, 64)),
            transforms.ToTensor(),
            transforms.Normalize((0.5,), (0.5,))
        ])
    
        image = Image.open(image_path).convert('RGB')
        image = transform(image).unsqueeze(0)  # Add batch dimension

        # Move model & image to the correct device
        image = image.to(device)
        model.eval()

        # Make prediction
        with torch.no_grad():
            output = model(image)
            probabilities = F.softmax(output, dim=1)
            predicted_class = torch.argmax(probabilities, dim=1).item()

        # **Define class labels**
        class_labels = sorted([
            'zig_1', 't_left', 'rec_3x2_v', 't_down', 't_right', 't_up', 'zig_2', 'zig_3', 'zig_4',
            'line_5_v', 'ang_3_left_down', 'ang_3_left_up', 'ang_3_right_down', 'ang_3_right_up',
            'line_4_h', 'line_4_v', 'line_5_h', 'rec_3x2_h', 'line_2_h', 'line_3_h', 'line_3_v',
            'ang_2_left_up', 'ang_2_right_up', 'ang_2_left_down', 'ang_2_right_down', 'square_2',
            'l_1', 'l_2', 'l_3', 'l_4', 'l_inv_1', 'l_inv_2', 'l_inv_3', 'l_inv_4',
            'sla_right_3', 'sla_right_2', 'sla_left_3', 'sla_left_2', 'zz_single',
            'square_3', 'line_2_v'
        ])   

        # **Print the predicted class**
        print(f"Predicted Shape for {image_path}: {class_labels[predicted_class]}")

    # **Example usage**
    test_images = [
        "../test_shapes/test_ang_2_left_down.png",
        "../test_shapes/test_ang_2_left_up.png",
        "../test_shapes/test_ang_2_right_down.png",
        "../test_shapes/test_ang_2_right_up.png",
        "../test_shapes/test_ang_3_left_down.png",
        "../test_shapes/test_ang_3_left_up.png",
        "../test_shapes/test_ang_3_right_up.png",
        "../test_shapes/test_ang_3_right_down.png"
    ]

    # **Run predictions**
    for img in test_images:
        predict_image(img, model)



    # Former notebook cell 5



    # Former notebook cell 6
    import os

    # Define the directory path
    directory = "shapes/"

    # Get all subfolder names
    subfolders = [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]

    print(subfolders)


if __name__ == "__main__":
    main()
