# Annotation Progress Tracker Spreadsheet:
https://docs.google.com/spreadsheets/d/11xHF4m3nwdMaOhU0I3eYglJJ1yJcFLXcJ8fwwgNiOz0/edit?gid=0#gid=0

# GitHub Desktop
1. Install GitHub Desktop

2. Click “File → Clone Repository” and paste your repo link:
https://github.com/ElleOwO/realtimegamestatistics.git

3. It’ll download the repo to your computer.

4. When you finish annotating, drag your new files into your local annotations folder.

5. Open GitHub Desktop:

  - You’ll see your changes listed.

  - Add a short description like "Added annotations for frames 0–99."

  - Click Commit to main → Push origin.

  - That sends your changes to GitHub for everyone to see.

# RTGS Team Setup Guide

How to set up Git and work only in your own folder
1. Clone the Repository
  1. Go to your GitHub Desktop or Terminal.
  2. Clone the project using this link:
   https://github.com/ElleOwO/realtimegamestatistics.git
  3. Navigate into the folder after it downloads.
2. Create Your Personal Folder
    Inside the 'annotations' folder, make your own folder using your name.
    Example:
    annotations/lyinmya/
    annotations/alex/
    annotations/priya/
3. Set Up Your Local .gitignore
  1. Open the project folder.
  2. Create a file named '.gitignore' (if it doesn't exist).
  3. Add the following lines (replace 'yourname' with your folder name):
   annotations/*
   !annotations/yourname/**
  This makes Git track only your folder and ignore others.
4. Keep Your .gitignore Local
  -- Do not commit your .gitignore file!
  This should stay on your computer only.
  If you accidentally added it, run:
   git rm --cached .gitignore
5. Verify It Works
  Run 'git status' in your terminal.
  You should only see your files (e.g., annotations/lyinmya/...).
  If you see other people's folders, check your .gitignore lines again.
6. Optional: Local Exclude File
  You can also edit '.git/info/exclude' and add the same lines there.
  This works like .gitignore but is always local (never synced).
# When pushing commits:
1. Instead of git add *, each member should do:

```
git add annotations/theirname/

Or even more specific:

git add annotations/lyinmya/images/
git add annotations/lyinmya/labels/
```
That’s the safest way. It only stages their folder.

# GitHub Actions behind the scenes
Whenever someone uploads new annotations:

GitHub Actions runs a workflow automatically (merge-upload.yml).

It merges everyone’s data and uploads it to Roboflow.

You don’t have to do anything special — it happens automatically in the background.

# Real-Time Game Statistics

This GitHub repository automates dataset management for our **real-time soccer game analytics system**.  
It merges image annotations from multiple team members, compresses the data, and uploads the latest version to **Roboflow** automatically using **GitHub Actions**.

---

## Repository Structure

```
/realtimegamestatistics/
├── annotations/                     # Each member stores their own labeled data here
│   ├── member1/
│   │   ├── images/                  # Labeled images (e.g., frame1.png)
│   │   └── labels/                  # Corresponding YOLO annotation files (e.g., frame1.txt)
│   ├── member2/
│   └── ...
│
├── merged_dataset/                  # Auto-created by merge_and_upload.py after merging all member folders
│   ├── images/                      # Combined images from all annotators
│   └── labels/                      # Combined label files
│
├── merge_and_upload.py              # Python script to merge and upload datasets to Roboflow
│                                    # 1. Collects all member data
│                                    # 2. Merges into merged_dataset/
│                                    # 3. Uploads each image individually to Roboflow
│
├── .github/
│   └── workflows/
│       └── merge-upload.yml         # GitHub Action that runs the script automatically
│                                    # - Installs dependencies
│                                    # - Merges annotations
│                                    # - Uploads images to Roboflow
│
└── .gitignore                       # Prevents system files, venvs, and merged outputs from being committed

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
How it works

Merges all member annotation folders (annotations/memberX/images and annotations/memberX/labels) into merged_dataset/.

Uploads every image inside merged_dataset/images to Roboflow individually.

Each image upload will automatically include its YOLO-style label if the file names match (e.g., frame123.png and frame123.txt).

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
