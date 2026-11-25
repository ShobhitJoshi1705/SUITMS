import os
import hashlib

folder = r"D:\TrafficViolation\all_images"

hash_dict = {}
duplicates = []

for filename in os.listdir(folder):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        file_path = os.path.join(folder, filename)

        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        if file_hash in hash_dict:
            duplicates.append(file_path)
        else:
            hash_dict[file_hash] = file_path

# Delete duplicates
for dup in duplicates:
    os.remove(dup)

print(f"Duplicates removed: {len(duplicates)}")
print("Duplicate cleanup completed.")
