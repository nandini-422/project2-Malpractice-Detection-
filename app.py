from flask import Flask, render_template, request, redirect, url_for, flash, Response, session, jsonify
from flask import request
import sqlite3
import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
import threading
import random
import string
import smtplib
from email.mime.text import MIMEText
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Email Configuration (Replace with your actual email credentials)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'purplevja@gmail.com'
app.config['MAIL_PASSWORD'] = 'pahy quyr cbxq cvmu'
app.config['MAIL_DEFAULT_SENDER'] = 'manikantanimmakayala271@gmail.com'

# Initialize Face Mesh for head tracking
mp_face_mesh = mp.solutions.face_mesh
mp_face_detection = mp.solutions.face_detection
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)
face_detection = mp_face_detection.FaceDetection()

# Camera Setup
cap = cv2.VideoCapture(0)

# Malpractice counter
malpractice_count = 0
stop_video_feed = False  # Flag to stop the video feed
redirect_to_404 = False  # Flag to trigger redirection

# Initialize pyttsx3 engine
engine = pyttsx3.init()

# OTP storage dictionary
otp_storage = {}

def generate_otp():
    return ''.join(random.choices(string.digits, k=4))

def send_otp_email(email, otp):
    try:
        msg = MIMEText(f'Your OTP for registration is: {otp}')
        msg['Subject'] = 'Registration OTP'
        msg['To'] = email
        
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def speak(text):
    def speak_text():
        engine.say(text)
        engine.runAndWait()
        # Set redirect flag after speaking
        global redirect_to_404
        if "malpractice detected" in text.lower() and malpractice_count >= 2:
            redirect_to_404 = True
    threading.Thread(target=speak_text).start()

# Database setup
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Malpractice detection functions
def get_face_orientation(landmarks, img_w, img_h):
    left_eye = landmarks[33]
    right_eye = landmarks[263]
    nose_tip = landmarks[1]

    left_x, left_y = int(left_eye.x * img_w), int(left_eye.y * img_h)
    right_x, right_y = int(right_eye.x * img_w), int(right_eye.y * img_h)
    nose_x, nose_y = int(nose_tip.x * img_w), int(nose_tip.y * img_h)

    eye_diff = right_x - left_x
    nose_diff = nose_x - (left_x + right_x) // 2

    if nose_diff > eye_diff * 0.3:
        return "Right"
    elif nose_diff < -eye_diff * 0.3:
        return "Left"
    else:
        return "Center"

def generate_frames():
    global malpractice_count, stop_video_feed, redirect_to_404
    while not stop_video_feed:
        ret, frame = cap.read()
        if not ret:
            break

        img_h, img_w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Face Detection
        results = face_detection.process(rgb_frame)
        face_count = 0

        if results.detections:
            face_count = len(results.detections)

        # Face Mesh (for rotation detection)
        mesh_results = face_mesh.process(rgb_frame)
        if mesh_results.multi_face_landmarks:
            for face_landmarks in mesh_results.multi_face_landmarks:
                face_orientation = get_face_orientation(face_landmarks.landmark, img_w, img_h)
                if face_orientation in ["Left", "Right"]:
                    malpractice_count += 1
                    cv2.putText(frame, "Malpractice Detected! (Head Turned)", (50, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    speak("Malpractice detected! Head turned.")

        # Malpractice Alerts
        if face_count == 0:
            malpractice_count += 1
            cv2.putText(frame, "Malpractice Detected! (No Face)", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            speak("Malpractice detected! No face detected.")
        elif face_count > 1:
            malpractice_count += 1
            cv2.putText(frame, "Malpractice Detected! (Extra Person)", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            speak("Malpractice detected! Extra person detected.")

        # If malpractice detected twice, stop the exam
        if malpractice_count >= 2:
            cv2.putText(frame, "Exam Submitted Due to Malpractice", (50, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            speak("Exam submitted due to malpractice.")
            stop_video_feed = True
            redirect_to_404 = True
            break

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Question Bank
CORRECT_ANSWERS = {
    'q1': 'Paris',
    'q2': '4',
    'q3': 'Jupiter',
    'q4': 'William Shakespeare',
    'q5': 'H2O',
    'q6': '7',
    'q7': 'Mars',
    'q8': 'Blue Whale',
    'q9': 'Au',
    'q10': 'Photosynthesis'
}

QUESTIONS = [
    ("What is the capital of France?", "q1", "text"),
    ("How many sides does a square have?", "q2", "text"),
    ("Which planet is the largest in our solar system?", "q3", "text"),
    ("Who wrote 'Romeo and Juliet'?", "q4", "text"),
    ("What is the chemical formula for water?", "q5", "text"),
    ("How many continents are there?", "q6", "text"),
    ("Which planet is known as the Red Planet?", "q7", "text"),
    ("What is the largest mammal on Earth?", "q8", "text"),
    ("What is the chemical symbol for gold?", "q9", "text"),
    ("Process by which plants make their own food?", "q10", "text")
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login_register')
def login_register():
    return render_template('login_register.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    email = request.json.get('email')
    otp = generate_otp()
    otp_storage[email] = otp
    if send_otp_email(email, otp):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Failed to send OTP'})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = request.json.get('email')
    user_otp = request.json.get('otp')
    if email in otp_storage and otp_storage[email] == user_otp:
        del otp_storage[email]
        session['otp_verified'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid OTP'})

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
    conn.close()
    if user:
        session['user'] = email
        flash('Login successful!', 'success')
        return redirect(url_for('instructions'))
    else:
        flash('Invalid email or password', 'error')
        return redirect(url_for('login_register'))

@app.route('/register', methods=['POST'])
def register():
    if not session.get('otp_verified'):
        flash('Please verify OTP first', 'error')
        return redirect(url_for('login_register'))
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, password))
        conn.commit()
        session.pop('otp_verified', None)
        flash('Registration successful! Please login.', 'success')
    except sqlite3.IntegrityError:
        flash('Email already exists', 'error')
    finally:
        conn.close()
    return redirect(url_for('login_register'))

@app.route('/instructions')
def instructions():
    if 'user' not in session:
        return redirect(url_for('login_register'))
    return render_template('instructions.html')

@app.route('/malpractice')
def malpractice():
    if 'user' not in session:
        return redirect(url_for('login_register'))
    # Get random questions and pass them to the template
    random_questions = random.sample(QUESTIONS, 5)
    questions_data = [{'text': q[0], 'id': q[1], 'type': q[2]} for q in random_questions]
    return render_template('malpractice.html', questions=questions_data)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/check_malpractice')
def check_malpractice():
    global redirect_to_404
    if redirect_to_404:
        return jsonify({'redirect': True, 'url': url_for('error_404')})
    return jsonify({'redirect': False})

@app.route('/get_questions')
def get_questions():
    random_questions = random.sample(QUESTIONS, 5)
    return jsonify([{'question': q[0], 'id': q[1], 'type': q[2]} for q in random_questions])

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    user_answers = request.form
    score = 0
    feedback = []
    for question, correct_answer in CORRECT_ANSWERS.items():
        user_answer = user_answers.get(question, '').strip()
        if user_answer.lower() == correct_answer.lower():
            score += 1
            feedback.append(f"{question.split('q')[1]}: ✅ Correct!")
        else:
            feedback.append(f"{question.split('q')[1]}: ❌ Incorrect. Correct answer: {correct_answer}.")
    return jsonify({'score': score, 'feedback': feedback})

@app.route('/404')
def error_404():
    return render_template('404.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)