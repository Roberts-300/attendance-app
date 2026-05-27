from flask import Flask, render_template, request, jsonify, Response
import face_recognition
import cv2
import numpy as np
import sqlite3
import pickle
import os
import base64
from datetime import date

app = Flask(__name__)

# ── Folders & DB ──────────────────────────────────────────
os.makedirs("encodings", exist_ok=True)
os.makedirs("static", exist_ok=True)

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            date TEXT,
            status TEXT,
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ── Helpers ───────────────────────────────────────────────
def load_all_encodings():
    known_encodings = []
    known_names = []
    for file in os.listdir("encodings"):
        if file.endswith(".pkl"):
            name = file.replace(".pkl", "")
            with open(f"encodings/{file}", "rb") as f:
                encoding = pickle.load(f)
            known_encodings.append(encoding)
            known_names.append(name)
    return known_encodings, known_names

def get_all_members():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, name FROM members")
    members = c.fetchall()
    conn.close()
    return members

# ── Routes ────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/scan")
def scan():
    return render_template("scan.html")

@app.route("/results")
def results():
    return render_template("results.html")

# ── API: Register member ───────────────────────────────────
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    name = data.get("name", "").strip()
    image_data = data.get("image")  # base64 string

    if not name or not image_data:
        return jsonify({"success": False, "error": "Name and photo required."})

    # Decode base64 image
    header, encoded = image_data.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Get face encoding
    encodings = face_recognition.face_encodings(rgb)
    if len(encodings) == 0:
        return jsonify({"success": False, "error": "No face detected. Try again."})

    encoding = encodings[0]

    # Save to file
    with open(f"encodings/{name}.pkl", "wb") as f:
        pickle.dump(encoding, f)

    # Save to DB
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO members (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": f"{name} registered successfully!"})

# ── API: Get members list ──────────────────────────────────
@app.route("/api/members")
def api_members():
    members = get_all_members()
    return jsonify([{"id": m[0], "name": m[1]} for m in members])

# ── API: Delete member ────────────────────────────────────
@app.route("/api/delete/<name>", methods=["DELETE"])
def api_delete(name):
    enc_path = f"encodings/{name}.pkl"
    if os.path.exists(enc_path):
        os.remove(enc_path)
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ── API: Scan frame for attendance ────────────────────────
@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.get_json()
    image_data = data.get("image")
    stream_url = data.get("stream_url", "")

    known_encodings, known_names = load_all_encodings()
    if not known_encodings:
        return jsonify({"success": False, "error": "No members registered yet."})

    # Decode frame
    if image_data:
        header, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    else:
        return jsonify({"success": False, "error": "No image received."})

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Detect faces
    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(rgb, face_locations)

    present_names = set()
    for face_enc in face_encodings:
        matches = face_recognition.compare_faces(known_encodings, face_enc, tolerance=0.5)
        distances = face_recognition.face_distance(known_encodings, face_enc)
        if len(distances) > 0:
            best_idx = np.argmin(distances)
            if matches[best_idx]:
                present_names.add(known_names[best_idx])

    all_names = set(known_names)
    absent_names = all_names - present_names

    # Save to DB
    today = str(date.today())
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    for name in all_names:
        c.execute("SELECT id FROM members WHERE name = ?", (name,))
        row = c.fetchone()
        if row:
            status = "Present" if name in present_names else "Absent"
            c.execute(
                "INSERT INTO attendance (member_id, date, status) VALUES (?, ?, ?)",
                (row[0], today, status)
            )
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "present": sorted(list(present_names)),
        "absent": sorted(list(absent_names)),
        "total": len(all_names),
        "faces_detected": len(face_locations)
    })

# ── API: Attendance history ────────────────────────────────
@app.route("/api/history")
def api_history():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        SELECT m.name, a.date, a.status
        FROM attendance a
        JOIN members m ON a.member_id = m.id
        ORDER BY a.date DESC
    """)
    rows = c.fetchall()
    conn.close()
    return jsonify([{"name": r[0], "date": r[1], "status": r[2]} for r in rows])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
