# FaceTrack — Team Attendance App

Simple face recognition attendance system for small teams (up to ~10 members).

---

## 📁 Folder Structure

```
attendance-app/
├── app.py
├── requirements.txt
├── database.db         ← auto-created on first run
├── encodings/          ← auto-created, stores face data
└── templates/
    ├── base.html
    ├── index.html
    ├── register.html
    ├── scan.html
    └── results.html
```

---

## 🖥️ Requirements

- Python 3.8 or higher
- pip
- CMake (needed for dlib/face_recognition)

---

## ⚙️ Setup Steps

### Step 1 — Install CMake (required for face_recognition)

**Windows:**
- Download from https://cmake.org/download/
- During install, check "Add CMake to system PATH"

**Mac:**
```bash
brew install cmake
```

**Linux/Ubuntu:**
```bash
sudo apt install cmake
```

---

### Step 2 — Install Python libraries

Open terminal/command prompt inside the `attendance-app` folder:

```bash
pip install -r requirements.txt
```

> ⚠️ This may take 5–10 minutes. `dlib` compiles from source.

---

### Step 3 — Run the app

```bash
python app.py
```

Then open your browser and go to:
```
http://localhost:5000
```

---

## 📱 Using Your Phone as Camera

1. Install **IP Webcam** (Android) or **DroidCam** (iOS/Android)
2. Connect phone and laptop to the **same WiFi**
3. Open the app → tap **Start Server**
4. Note the URL shown (e.g. `http://192.168.1.5:8080/video`)
5. In the Scan page → select **Phone Stream** → paste the URL

---

## 🚀 How to Use

1. **Register** — Go to Register page, enter name, take photo
2. **Scan** — Go to Scan page, start camera, click Scan Now
3. **Results** — View who is present/absent, export CSV

---

## 🔧 Troubleshooting

| Problem | Fix |
|--------|-----|
| `No face detected` | Better lighting, face closer to camera |
| `dlib install fails` | Make sure CMake is installed first |
| Phone stream not connecting | Check both devices on same WiFi |
| Wrong person recognized | Re-register with clearer photo |
