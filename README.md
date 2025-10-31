# Real-Time Game Statistics

This GitHub repository automates dataset management for our **real-time soccer game analytics system**.  
It merges image annotations from multiple team members, compresses the data, and uploads the latest version to **Roboflow** automatically using **GitHub Actions**.

---

## Repository Structure

```
/realtimegamestatistics/
├── annotations/                # Each member stores their own labeled data here
│   ├── member1/
│   │   ├── images/
│   │   └── labels/
│   ├── member2/
│   └── ...
│
├── merged_dataset/             # Automatically created merged dataset (local)
├── merge_and_upload.py         # Script that merges, zips, and uploads to Roboflow
│
└── .github/
    └── workflows/
        └── merge-upload.yml    # GitHub Action that runs the script automatically
```

---

## How It Works

### Data Collection
Each team member annotates soccer game images locally (using Roboflow, LabelImg, or another tool) and saves their work under:

```
annotations/member_name/images/
annotations/member_name/labels/
```
Each label file must share the same base name as its image.

---

### Scripts

#### `merge_and_upload.py`
This script:
- Merges all member folders into a single unified dataset (`merged_dataset/`).
- Ensures unique filenames to avoid collisions.
- Zips the dataset into `merged_dataset.zip`.
- Uploads the zipped dataset to your Roboflow project using the Roboflow API.

The script automatically uses your **private API key** from GitHub Secrets and your project’s **WORKSPACE** and **PROJECT** slugs from Roboflow.

---

#### `.github/workflows/merge-upload.yml`
This GitHub Actions workflow runs the script automatically whenever new annotations are pushed.

It:
- Checks out the repo.
- Installs dependencies (`roboflow`).
- Runs `merge_and_upload.py` using your secret Roboflow key.

**Trigger conditions:**
- Any new commits in `annotations/**`
- Manual trigger via the GitHub Actions tab
