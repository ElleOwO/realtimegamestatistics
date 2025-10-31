import os
import shutil
import uuid
import zipfile
from roboflow import Roboflow



# ---------- CONFIGURATION ----------
# Paths
BASE_DIR = os.getcwd()
ANNOTATIONS_DIR = os.path.join(BASE_DIR, "annotations")
MERGED_DIR = os.path.join(BASE_DIR, "merged_dataset")

# Roboflow credentials
API_KEY = os.getenv("ROBOFLOW_API_KEY")
WORKSPACE = "rtgs-uifdg"
PROJECT = "rtgs-omuwo"

# -----------------------------------

def merge_datasets():
    """Combine all annotation folders into one merged dataset."""
    images_dir = os.path.join(MERGED_DIR, "images")
    labels_dir = os.path.join(MERGED_DIR, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    member_folders = [
        os.path.join(ANNOTATIONS_DIR, d)
        for d in os.listdir(ANNOTATIONS_DIR)
        if os.path.isdir(os.path.join(ANNOTATIONS_DIR, d))
    ]

    print(f"🔍 Found {len(member_folders)} member folders to merge.")

    for folder in member_folders:
        img_path = os.path.join(folder, "images")
        lbl_path = os.path.join(folder, "labels")

        if not os.path.exists(img_path) or not os.path.exists(lbl_path):
            print(f"Warning: Skipping {folder} (missing images or labels folder)")
            continue

        for img in os.listdir(img_path):
            base, ext = os.path.splitext(img)
            unique_name = f"{base}_{uuid.uuid4().hex[:6]}{ext}"
            shutil.copy(os.path.join(img_path, img), os.path.join(images_dir, unique_name))

            label_file = base + ".txt"
            if os.path.exists(os.path.join(lbl_path, label_file)):
                shutil.copy(
                    os.path.join(lbl_path, label_file),
                    os.path.join(labels_dir, unique_name.replace(ext, ".txt"))
                )

    print("All datasets merged into:", MERGED_DIR)


def zip_dataset():
    """Create a ZIP file from the merged dataset."""
    zip_path = os.path.join(BASE_DIR, "merged_dataset.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(MERGED_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, MERGED_DIR)
                zipf.write(file_path, arcname)
    print("Zipped dataset saved as:", zip_path)
    return zip_path


def upload_to_roboflow(zip_path):
    """Upload the merged dataset to Roboflow."""
    print("Uploading dataset to Roboflow...")
    rf = Roboflow(api_key=API_KEY)
    workspace = rf.workspace(WORKSPACE)
    project = workspace.project(PROJECT)
    dataset = project.upload_dataset(zip_path)
    print(f"Upload complete! Dataset version ID: {dataset.version}")



if __name__ == "__main__":
    merge_datasets()
    zip_path = zip_dataset()
    upload_to_roboflow(zip_path)
