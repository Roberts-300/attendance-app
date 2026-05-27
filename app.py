from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import sqlite3
import os
import base64
import pickle
from datetime import date

app = Flask(__name__)
os.makedirs("encodings", exist_ok=True)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
recognizer = cv2.face.LBPHFaceRecognizer_create()

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER, date TEXT, status TEXT,
        FOREIGN KEY(member_id) REFERENCES members(id))""")
    conn.commit()
    conn.close()

init_db()

def decode_image(image_data):
    header, encoded = image_data.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

def get_all_members():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, name FROM members")
    members = c.fetchall()
    conn.close()
    return members

def train_recognizer():
    faces, labels, label_map = [], [], {}
    for mid, name in get_all_members():
        path = f"encodings/{name}.pkl"
        if os.path.exists(path):
            with open(path, "rb") as f:
                faces.append(pickle.load(f))
            labels.append(mid)
            label_map[mid] = name
    if faces:
        recognizer.train(faces, np.array(labels))
    return label_map

@app.route("/")
def index(): return render_template("index.html")
@app.route("/register")
def register(): return render_template("register.html")
@app.route("/scan")
def scan(): return render_template("scan.html")
@app.route("/results")
def results(): return render_template("results.html")

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    name = data.get("name", "").strip()
    image_data = data.get("image")
    if not name or not image_data:
        return jsonify({"success": False, "error": "Name and photo required."})
    img = decode_image(image_data)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return jsonify({"success": False, "error": "No face detected."})
    x, y, w, h = faces[0]
    face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
    with open(f"encodings/{name}.pkl", "wb") as f:
        pickle.dump(face_roi, f)
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO members (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"{name} registered!"})

@app.route("/api/members")
def api_members():
    return jsonify([{"id": m[0], "name": m[1]} for m in get_all_members()])

@app.route("/api/delete/<name>", methods=["DELETE"])
def api_delete(name):
    path = f"encodings/{name}.pkl"
    if os.path.exists(path): os.remove(path)
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.get_json()
    image_data = data.get("image")
    members = get_all_members()
    if not members:
        return jsonify({"success": False, "error": "No members registered."})
    label_map = train_recognizer()
    if not label_map:
        return jsonify({"success": False, "error": "No face data found."})
    img = decode_image(image_data)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    present_names = set()
    for (x, y, w, h) in faces:
        face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
        label, confidence = recognizer.predict(face_roi)
        if confidence < 100 and label in label_map:
            present_names.add(label_map[label])
    all_names = set(m[1] for m in members)
    absent_names = all_names - present_names
    today = str(date.today())
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    for name in all_names:
        c.execute("SELECT id FROM members WHERE name = ?", (name,))
        row = c.fetchone()
        if row:
            status = "Present" if name in present_names else "Absent"
            c.execute("INSERT INTO attendance (member_id, date, status) VALUES (?, ?, ?)",
                (row[0], today, status))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "present": sorted(present_names),
        "absent": sorted(absent_names), "total": len(all_names),
        "faces_detected": len(faces)})

@app.route("/api/history")
def api_history():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""SELECT m.name, a.date, a.status FROM attendance a
        JOIN members m ON a.member_id = m.id ORDER BY a.date DESC""")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"name": r[0], "date": r[1], "status": r[2]} for r in rows])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
