import os
import shutil
import uuid

# Change this to your raw_data path
base_path = r"D:\TrafficViolation\raw_data"

# Destination folder
destination = r"D:\TrafficViolation\all_images"
os.makedirs(destination, exist_ok=True)

# Image extensions to consider
valid_extensions = ('.jpg', '.jpeg', '.png')

count = 0

# Walk through all subfolders
for root, dirs, files in os.walk(base_path):
    for file in files:
        if file.lower().endswith(valid_extensions):
            source_path = os.path.join(root, file)
            
            # Generate unique filename
            new_filename = str(uuid.uuid4()) + os.path.splitext(file)[1]
            dest_path = os.path.join(destination, new_filename)
            
            shutil.copy2(source_path, dest_path)
            count += 1

print(f"Total images copied: {count}")
print("All images merged successfully into all_images folder.")
