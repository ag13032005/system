import smtplib
import json
from PIL import Image
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
import streamlit as st
import pandas as pd
import numpy as np
import os
import time
import matplotlib.pyplot as plt
import random
from datetime import datetime
from datetime import timedelta
import base64
import hashlib
import pickle
import requests
import sqlite3
# from streamlit_extras.switch_page_button import switch_page
from streamlit_player import st_player
import plotly.express as px
from dotenv import load_dotenv
import re

load_dotenv()
API_KEY = os.getenv("FOREFRONT_API_KEY")

if not API_KEY:
    print("API Key not found. Check your .env file.")
else:
    print(f"Loaded API Key: {API_KEY[:5]}********")

# Configuration
st.set_page_config(
    page_title="AI Learning Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)
def create_default_admin():
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    
    # Check if any admin exists
    c.execute("SELECT COUNT(*) FROM admins")
    admin_count = c.fetchone()[0]
    
    # If no admins exist, create a default admin
    if admin_count == 0:
        print("No admin account found. Creating default admin...")
        default_username = "admin"
        default_password = "admin123"  # You should change this immediately after first login
        default_email = "admin@example.com"
        
        hashed_password = hash_password(default_password)
        try:
            c.execute(
                "INSERT INTO admins (username, password, email, joined_date) VALUES (?, ?, ?, ?)",
                (default_username, hashed_password, default_email, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            print(f"Default admin created. Username: {default_username}, Password: {default_password}")
        except sqlite3.Error as e:
            print(f"Failed to create default admin: {e}")
    
    conn.close()

# === Database Connection ===
def get_connection():
    return sqlite3.connect('learning_platform.db')

# === Admin & User Management Functions ===
def db_create_admin(username, password, email):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM admins WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return False

    joined_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO admins (username, password, email, joined_date) VALUES (?, ?, ?, ?)",
              (username, password, email, joined_date))
    conn.commit()
    conn.close()
    return True

# Database setup
def init_db():
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()

    # Create admins table
    c.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        email TEXT,
        joined_date TEXT
    )
    ''')
    # Add is_temp_password column to admins table if not exists
    try:
        conn.execute("ALTER TABLE admins ADD COLUMN is_temp_password INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists

    
    # Create users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        email TEXT,
        joined_date TEXT,
        profile_photo BLOB      
    )
    ''')
    # Add is_temp_password column to users table if not exists
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_temp_password INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists


    # Create password reset tokens table
    c.execute('''
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        username TEXT PRIMARY KEY,
        token TEXT NOT NULL,
        expiry TEXT NOT NULL,
        FOREIGN KEY (username) REFERENCES users(username)
    )
    ''')

    # Add profile_photo column to users table
    
    try:
        c.execute("SELECT profile_photo FROM users LIMIT 1")
    except sqlite3.OperationalError:
        # Column doesn't exist, so add it
        c.execute("ALTER TABLE users ADD COLUMN profile_photo BLOB")

    # Create courses_enrolled table
    c.execute('''
    CREATE TABLE IF NOT EXISTS courses_enrolled (
        username TEXT,
        course_name TEXT,
        enrolled_date TEXT,
        PRIMARY KEY (username, course_name),
        FOREIGN KEY (username) REFERENCES users(username)
    )
    ''')

    # courses table
    c.execute('''
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    ''')

    # Videos Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        course TEXT,
        url TEXT
    )
    ''')

    # Quizzes Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        course TEXT,
        questions_json TEXT
    )
    ''')

    # Create quiz_scores table
    c.execute('''
    CREATE TABLE IF NOT EXISTS quiz_scores (
        username TEXT,
        course_name TEXT,
        quiz_name TEXT,
        score REAL,
        date_taken TEXT,
        PRIMARY KEY (username, course_name, quiz_name),
        FOREIGN KEY (username) REFERENCES users(username)
    )
    ''')
    
    # Create notes table
    c.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        filename TEXT,
        path TEXT,
        uploaded_by TEXT,
        uploaded_at TEXT,
        FOREIGN KEY (uploaded_by) REFERENCES users(username)
    )
    ''')
    
    # Create videos_watched table
    c.execute('''
    CREATE TABLE IF NOT EXISTS videos_watched (
        username TEXT,
        video_title TEXT,
        course_name TEXT,
        watched_date TEXT,
        PRIMARY KEY (username, video_title),
        FOREIGN KEY (username) REFERENCES users(username)
    )
    ''')
    
    # Create chat_history table
    c.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        role TEXT,
        content TEXT,
        timestamp TEXT,
        FOREIGN KEY (username) REFERENCES users(username)
    )
    ''')

     # Student Queries Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        subject TEXT,
        message TEXT,
        timestamp TEXT
    )
    ''')

    # Admin Replies Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS admin_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_id INTEGER,
        reply TEXT,
        timestamp TEXT
    )
    ''')
    
    conn.commit()
    conn.close()


def db_create_admin(username, email):
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
    hashed_password = hash_password(temp_password)
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO admins (username, password, email, joined_date, is_temp_password) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_password, email, datetime.now().strftime("%Y-%m-%d"), 1)
        )
        conn.commit()
        send_admin_credentials_email(email, username, temp_password)  # ✉️ Send temp password
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True


def db_authenticate(username, password):
    hashed_password = hash_password(password)
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT password, is_temp_password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hashed_password:
        if result[1] == 1:
            st.session_state.force_student_change_password = True
        else:
            st.session_state.force_student_change_password = False
        return True
    return False


def db_update_admin_password(username, new_password):
    hashed_password = hash_password(new_password)
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE admins SET password = ?, is_temp_password = 0 WHERE username = ?", (hashed_password, username))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True

def db_update_user_password(username, new_password):
    hashed_password = hash_password(new_password)
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET password = ?, is_temp_password = 0 WHERE username = ?", (hashed_password, username))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True




def insert_default_courses():
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()

    # Only insert Python Programming if missing
    c.execute("SELECT COUNT(*) FROM courses WHERE name = ?", ("Python Programming",))
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO courses (name) VALUES (?)", ("Python Programming",))

        # Insert videos and quizzes for Python Programming
        c.execute("INSERT INTO videos (title, course, url) VALUES (?, ?, ?)",
                  ("Introduction to Python", "Python Programming", "https://www.youtube.com/watch?v=_uQrJ0TkZlc"))
        c.execute("INSERT INTO videos (title, course, url) VALUES (?, ?, ?)",
                  ("Python Data Structures", "Python Programming", "https://www.youtube.com/watch?v=W8KRzm-HUcc"))

        python_quiz_questions = [
            {"question": "What is Python?", "options": ["A snake", "A programming language", "A database", "A web framework"], "answer": 1},
            {"question": "Which of these is a Python data type?", "options": ["Integer", "Float", "String", "All of the above"], "answer": 3}
        ]
        c.execute("INSERT INTO quizzes (title, course, questions_json) VALUES (?, ?, ?)",
                  ("Python Basics", "Python Programming", json.dumps(python_quiz_questions)))

    # Only insert Machine Learning if missing
    c.execute("SELECT COUNT(*) FROM courses WHERE name = ?", ("Machine Learning",))
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO courses (name) VALUES (?)", ("Machine Learning",))

        # Insert videos and quizzes for Machine Learning
        c.execute("INSERT INTO videos (title, course, url) VALUES (?, ?, ?)",
                  ("Introduction to ML", "Machine Learning", "https://www.youtube.com/watch?v=gmvvaobm7eQ"))
        c.execute("INSERT INTO videos (title, course, url) VALUES (?, ?, ?)",
                  ("Supervised Learning", "Machine Learning", "https://www.youtube.com/watch?v=1NxnPkZM9bc"))

        ml_quiz_questions = [
            {"question": "What is a supervised learning task?", "options": ["Learning without labels", "Learning with labels", "Reinforcement learning", "None of these"], "answer": 1},
            {"question": "Which algorithm is used for classification?", "options": ["Linear Regression", "K-means", "Decision Trees", "PCA"], "answer": 2}
        ]
        c.execute("INSERT INTO quizzes (title, course, questions_json) VALUES (?, ?, ?)",
                  ("ML Fundamentals", "Machine Learning", json.dumps(ml_quiz_questions)))

    conn.commit()
    conn.close()

def db_get_all_students():
    students = []
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT username, email, joined_date FROM users")
    for row in c.fetchall():
        students.append({
            "username": row[0],
            "email": row[1],
            "joined_date": row[2]
        })
    conn.close()
    return students

def db_remove_student(username):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        # Delete from users table
        c.execute("DELETE FROM users WHERE username = ?", (username,))
        # Delete related data
        c.execute("DELETE FROM courses_enrolled WHERE username = ?", (username,))
        c.execute("DELETE FROM quiz_scores WHERE username = ?", (username,))
        c.execute("DELETE FROM videos_watched WHERE username = ?", (username,))
        c.execute("DELETE FROM chat_history WHERE username = ?", (username,))
        # Note: We're not deleting notes to preserve shared content
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True

def db_add_course(course_name):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO courses (name) VALUES (?)", (course_name,))
    conn.commit()
    conn.close()
    load_courses()
    COURSES[course_name] = {"videos": [], "quizzes": []}
    with open('courses.pkl', 'wb') as f:
        pickle.dump(COURSES, f)
    return True
def verify_course_data():
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    
    # Get all distinct courses from database
    c.execute("SELECT DISTINCT course_name FROM courses_enrolled")
    db_courses = {row[0] for row in c.fetchall()}
    
    # Get all courses from COURSES
    app_courses = set(COURSES.keys())
    
    # Find missing courses
    missing_courses = db_courses - app_courses
    
    # Add missing courses with empty structure
    for course in missing_courses:
        if course not in COURSES:
          COURSES[course] = {"videos": [], "quizzes": []}  # Ensure admin-added courses exist in COURSES
          with open('courses.pkl', 'wb') as f:
            pickle.dump(COURSES, f)  # Save to persistent storage

    
    conn.close()
    
    if missing_courses:
        # Save updated courses
        with open('courses.pkl', 'wb') as f:
            pickle.dump(COURSES, f)

def db_add_video_to_course(course_name, video_title, video_url):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("INSERT INTO videos (title, course, url) VALUES (?, ?, ?)", (video_title, course_name, video_url))
    conn.commit()
    conn.close()
    # Update COURSES and pickle
    load_courses()
    COURSES[course_name]["videos"].append({"title": video_title, "url": video_url})
    with open('courses.pkl', 'wb') as f:
        pickle.dump(COURSES, f)
    return True


def db_add_quiz_to_course(course_name, quiz_title, questions):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    
    # Convert questions list to JSON string
    questions_json = json.dumps(questions)
    
    # Insert into quizzes table
    c.execute("INSERT INTO quizzes (title, course, questions_json) VALUES (?, ?, ?)", (quiz_title, course_name, questions_json))
    conn.commit()
    conn.close()
    
    # Update COURSES and pickle
    load_courses()
    if course_name not in COURSES:
        COURSES[course_name] = {"videos": [], "quizzes": []}
    
    COURSES[course_name]["quizzes"].append({
        "title": quiz_title,
        "questions": questions
    })
    
    with open('courses.pkl', 'wb') as f:
        pickle.dump(COURSES, f)
    
    return True


def db_add_video_to_course(course_name, video_title, video_url):
    global COURSES
    if course_name not in COURSES:
        return False
    
    # Check if video already exists
    for video in COURSES[course_name]["videos"]:
        if video["title"] == video_title:
            return False
    
    # Add new video
    COURSES[course_name]["videos"].append({
        "title": video_title,
        "url": video_url
    })
    
    # Save courses to a file for persistence
    with open('courses.pkl', 'wb') as f:
        pickle.dump(COURSES, f)
    
    return True

# --- Course, Video, Quiz Deletion ---
def db_delete_course(course_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM courses WHERE name = ?", (course_name,))
    c.execute("DELETE FROM videos WHERE course = ?", (course_name,))
    c.execute("DELETE FROM quizzes WHERE course = ?", (course_name,))
    conn.commit()
    conn.close()
    
    # Also remove from COURSES dictionary
    load_courses()
    if course_name in COURSES:
        del COURSES[course_name]
        with open('courses.pkl', 'wb') as f:
            pickle.dump(COURSES, f)

def db_delete_video(video_title):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM videos WHERE title = ?", (video_title,))
    conn.commit()
    conn.close()
    
    # Also remove from COURSES dictionary
    load_courses()
    for course in COURSES:
        COURSES[course]["videos"] = [v for v in COURSES[course]["videos"] if v["title"] != video_title]
    
    with open('courses.pkl', 'wb') as f:
        pickle.dump(COURSES, f)

def db_delete_quiz(quiz_title):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM quizzes WHERE title = ?", (quiz_title,))
    conn.commit()
    conn.close()
    
    # Also remove from COURSES dictionary
    load_courses()
    for course in COURSES:
        COURSES[course]["quizzes"] = [q for q in COURSES[course]["quizzes"] if q["title"] != quiz_title]
    
    with open('courses.pkl', 'wb') as f:
        pickle.dump(COURSES, f)


# --- Student Queries ---
def db_save_contact_message(username, subject, message):
    conn = get_connection()
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO contact_messages (username, subject, message, timestamp) VALUES (?, ?, ?, ?)",
              (username, subject, message, timestamp))
    conn.commit()
    conn.close()

def db_get_all_contact_messages():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, subject, message, timestamp FROM contact_messages ORDER BY timestamp DESC")
    messages = c.fetchall()
    conn.close()
    return messages

def db_send_admin_reply(query_id, reply):
    conn = get_connection()
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO admin_replies (query_id, reply, timestamp) VALUES (?, ?, ?)",
              (query_id, reply, timestamp))
    conn.commit()
    conn.close()

def db_get_admin_replies_for_student(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
    SELECT contact_messages.subject, contact_messages.message, admin_replies.reply, admin_replies.timestamp
    FROM contact_messages
    JOIN admin_replies ON contact_messages.id = admin_replies.query_id
    WHERE contact_messages.username = ?
    ORDER BY admin_replies.timestamp DESC
    ''', (username,))
    rows = c.fetchall()
    conn.close()
    return rows



def refresh_courses():
    global COURSES
    load_courses()
    st.rerun()  # Optional: Force UI refresh

def db_add_quiz_to_course(course_name, quiz_title, questions):
    global COURSES
    if course_name not in COURSES:
        return False
    
    # Check if quiz already exists
    for quiz in COURSES[course_name]["quizzes"]:
        if quiz["title"] == quiz_title:
            return False
    
    # Add new quiz
    COURSES[course_name]["quizzes"].append({
        "title": quiz_title,
        "questions": questions
    })
    
    # Save courses to a file for persistence
    with open('courses.pkl', 'wb') as f:
        pickle.dump(COURSES, f)
    
    return True

# Load courses from file if it exists
def load_courses():
    global COURSES
    try:
        if os.path.exists('courses.pkl'):
            with open('courses.pkl', 'rb') as f:
                COURSES = pickle.load(f)
        else:
            # Initialize with default courses if file doesn't exist
            COURSES = {
                "Python Programming": {
                    "videos": [
                        {"title": "Introduction to Python", "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc"},
                        {"title": "Python Data Structures", "url": "https://www.youtube.com/watch?v=W8KRzm-HUcc"}
                    ],
                    "quizzes": [
                        {
                            "title": "Python Basics",
                            "questions": [
                                {"question": "What is Python?", 
                                 "options": ["A snake", "A programming language", "A database", "A web framework"],
                                 "answer": 1},
                                {"question": "Which of these is a Python data type?", 
                                 "options": ["Integer", "Float", "String", "All of the above"],
                                 "answer": 3}
                            ]
                        }
                    ]
                },
                "Machine Learning": {
                    "videos": [
                        {"title": "Introduction to ML", "url": "https://www.youtube.com/watch?v=gmvvaobm7eQ"},
                        {"title": "Supervised Learning", "url": "https://www.youtube.com/watch?v=1NxnPkZM9bc"}
                    ],
                    "quizzes": [
                        {
                            "title": "ML Fundamentals",
                            "questions": [
                                {"question": "What is a supervised learning task?", 
                                 "options": ["Learning without labels", "Learning with labels", "Reinforcement learning", "None of these"],
                                 "answer": 1},
                                {"question": "Which algorithm is used for classification?", 
                                 "options": ["Linear Regression", "K-means", "Decision Trees", "PCA"],
                                 "answer": 2}
                            ]
                        }
                    ]
                }
            }
    except Exception as e:
        print(f"Error loading courses: {e}")
        COURSES = {}  # Fallback to empty dict if loading fails

#database function for updating user profile
def db_update_user_profile(username, email=None, password=None, profile_photo=None):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        if email:
            c.execute("UPDATE users SET email = ? WHERE username = ?", (email, username))
        if password:
            hashed_password = hash_password(password)
            c.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))
        if profile_photo is not None:
            c.execute("UPDATE users SET profile_photo = ? WHERE username = ?", (profile_photo, username))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True

# function to get user profile data
def db_get_user_profile(username):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT email, profile_photo FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result:
        return {"email": result[0], "profile_photo": result[1]}
    return {"email": "", "profile_photo": None}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize database
init_db()
create_default_admin()
insert_default_courses()
load_courses()
verify_course_data()

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'notes' not in st.session_state:
    st.session_state.notes = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}
if 'is_admin' not in st.session_state:  # Add this line
    st.session_state.is_admin = False
if 'rerun' not in st.session_state:    # For our refresh_courses function
    st.session_state.rerun = False

# Sample courses and content
COURSES = {
    "Python Programming": {
        "videos": [
            {"title": "Introduction to Python", "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc"},
            {"title": "Python Data Structures", "url": "https://www.youtube.com/watch?v=W8KRzm-HUcc"}
        ],
        "quizzes": [
            {
                "title": "Python Basics",
                "questions": [
                    {"question": "What is Python?", 
                     "options": ["A snake", "A programming language", "A database", "A web framework"],
                     "answer": 1},
                    {"question": "Which of these is a Python data type?", 
                     "options": ["Integer", "Float", "String", "All of the above"],
                     "answer": 3}
                ]
            }
        ]
    },
    "Machine Learning": {
        "videos": [
            {"title": "Introduction to ML", "url": "https://www.youtube.com/watch?v=gmvvaobm7eQ"},
            {"title": "Supervised Learning", "url": "https://www.youtube.com/watch?v=1NxnPkZM9bc"}
        ],
        "quizzes": [
            {
                "title": "ML Fundamentals",
                "questions": [
                    {"question": "What is a supervised learning task?", 
                     "options": ["Learning without labels", "Learning with labels", "Reinforcement learning", "None of these"],
                     "answer": 1},
                    {"question": "Which algorithm is used for classification?", 
                     "options": ["Linear Regression", "K-means", "Decision Trees", "PCA"],
                     "answer": 2}
                ]
            }
        ]
    }
}

def db_get_user_email(username):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def db_store_reset_token(username, token, expiry):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO password_reset_tokens (username, token, expiry) VALUES (?, ?, ?)",
                 (username, token, expiry))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True


def db_reset_password(username, new_password):
    hashed_password = hash_password(new_password)
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))
        # Delete used token
        c.execute("DELETE FROM password_reset_tokens WHERE username = ?", (username,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True

def send_admin_credentials_email(email, username, temp_password):
    load_dotenv()
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")
    
    if not email_address or not email_password:
        print("Email credentials not found. Check your .env file.")
        return False

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = email
    msg['Subject'] = "Your AI Learning Platform Admin Account Credentials"
    
    body = f"""
    Hello {username},

    You have been added as an Admin to the AI Learning Platform.

    Your temporary login credentials are:

    **Username:** {username}
    **Temporary Password:** {temp_password}

    Please login and immediately change your password.

    Regards,
    AI Learning Platform Team
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_address, email_password)
        server.sendmail(email_address, email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False



def db_get_user_password(username):
    """Fetch the user's current password (hashed) and return a temporary password."""
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    
    if result:
        # Generate temporary password
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # Update database
        hashed_temp_password = hash_password(temp_password)
        conn = sqlite3.connect('learning_platform.db')
        c = conn.cursor()
        c.execute("UPDATE users SET password = ?, is_temp_password = 1 WHERE username = ?", (hashed_temp_password, username))
        conn.commit()
        conn.close()
        
        return temp_password
    return None


def send_password_email(email, username):
    """Send the current password to the user via email."""
    load_dotenv()
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")
    
    if not email_address or not email_password:
        print("Email credentials not found. Check your .env file.")
        return False
    
    # Fetch user's temporary password
    temp_password = db_get_user_password(username)
    
    if not temp_password:
        return False  # User not found
    
    # Create the email
    msg = MIMEMultipart()
    msg['From'] = email_address
    msg['To'] = email
    msg['Subject'] = "Your AI Learning Platform Account Password"
    
    body = f"""
    Hello {username},

    You requested to recover your password. Use the password below to log in:

    **Temporary Password:** {temp_password}

    Please change your password after logging in.

    If you did not request this, please ignore this email.

    Regards,
    AI Learning Platform Team
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Send email using SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_address, email_password)
        server.sendmail(email_address, email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
    
def is_valid_email(email):
    """Validate email format using regex."""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

# Database helper functions
def db_create_user(username, password, email):
    hashed_password = hash_password(password)
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password, email, joined_date) VALUES (?, ?, ?, ?)",
            (username, hashed_password, email, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

def db_authenticate_admin(username, password):
    hashed_password = hash_password(password)
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT password, is_temp_password FROM admins WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hashed_password:
        # Check if temp password
        if result[1] == 1:
            st.session_state.force_change_password = True  # Force password change
        else:
            st.session_state.force_change_password = False
        return True
    return False


def db_authenticate(username, password):
    hashed_password = hash_password(password)
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT password, is_temp_password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hashed_password:
        if result[1] == 1:
            st.session_state.force_student_change_password = True
        else:
            st.session_state.force_student_change_password = False
        return True
    return False


def db_get_user_data(username):
    user_data = {
        "courses_enrolled": [],
        "quiz_scores": {},
        "notes": []
    }
    
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    
    # Get enrolled courses
    c.execute("SELECT course_name FROM courses_enrolled WHERE username = ?", (username,))
    for row in c.fetchall():
        user_data["courses_enrolled"].append(row[0])
    
    # Get quiz scores
    c.execute("SELECT course_name, score FROM quiz_scores WHERE username = ?", (username,))
    for row in c.fetchall():
        user_data["quiz_scores"][row[0]] = row[1]
    
    # Get notes
    c.execute("SELECT id, title, filename, path, uploaded_at FROM notes WHERE uploaded_by = ?", (username,))
    for row in c.fetchall():
        user_data["notes"].append({
            "id": row[0],
            "title": row[1],
            "filename": row[2],
            "path": row[3],
            "uploaded_by": username,
            "uploaded_at": row[4]
        })
    
    conn.close()
    return user_data

def db_get_all_notes():
    notes = []
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT id, title, filename, path, uploaded_by, uploaded_at FROM notes")
    for row in c.fetchall():
        notes.append({
            "id": row[0],
            "title": row[1],
            "filename": row[2],
            "path": row[3],
            "uploaded_by": row[4],
            "uploaded_at": row[5]
        })
    conn.close()
    return notes

# --- Fetch all Courses ---
def db_get_all_courses():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM courses")
    rows = c.fetchall()
    conn.close()
    return [{"name": row[0]} for row in rows]

# --- Fetch all Videos ---
def db_get_all_videos():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT title FROM videos")
    rows = c.fetchall()
    conn.close()
    return [{"title": row[0]} for row in rows]

# --- Fetch all Quizzes ---
def db_get_all_quizzes():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT title FROM quizzes")
    rows = c.fetchall()
    conn.close()
    return [{"title": row[0]} for row in rows]


def db_delete_note(file_path):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM notes WHERE path = ?", (file_path,))
    conn.commit()
    conn.close()


def db_enroll_course(username, course_name):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO courses_enrolled (username, course_name, enrolled_date) VALUES (?, ?, ?)",
            (username, course_name, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

def db_save_quiz_result(username, course_name, quiz_name, score):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR REPLACE INTO quiz_scores (username, course_name, quiz_name, score, date_taken) VALUES (?, ?, ?, ?, ?)",
            (username, course_name, quiz_name, score, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True

def db_save_note(title, filename, path, username):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO notes (title, filename, path, uploaded_by, uploaded_at) VALUES (?, ?, ?, ?, ?)",
            (title, filename, path, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True

def db_mark_video_watched(username, video_title, course_name):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO videos_watched (username, video_title, course_name, watched_date) VALUES (?, ?, ?, ?)",
            (username, video_title, course_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True

def db_get_videos_watched(username):
    videos = []
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute("SELECT video_title FROM videos_watched WHERE username = ?", (username,))
    for row in c.fetchall():
        videos.append(row[0])
    conn.close()
    return videos

def db_get_progress_data(username):
    progress_data = {}
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
     # Load latest courses (important if admin has added new courses)
    load_courses()  
    
    # Get enrolled courses
    c.execute("SELECT course_name FROM courses_enrolled WHERE username = ?", (username,))
    enrolled_courses = [row[0] for row in c.fetchall()]

    for course in enrolled_courses:

         # Safely get course data with default empty structure
        course_info = COURSES.get(course, {"videos": [], "quizzes": []})  # Default empty structure
        total_videos = len(course_info["videos"])
        
        # Count watched videos for this course
        c.execute(
            "SELECT COUNT(*) FROM videos_watched WHERE username = ? AND course_name = ?",
            (username, course)
        )
        watched_count = c.fetchone()[0]
        # ✅ DEBUGGING - Check fetched data
        print(f"Course: {course}, Total Videos: {total_videos}, Watched: {watched_count}")
        # Calculate progress
        if total_videos > 0:
            progress = (watched_count / total_videos) * 100
        else:
            progress = 100 if watched_count > 0 else 0  # If no videos exist, assume full progress
            
        progress_data[course] = progress
    
    conn.close()
    # ✅ DEBUGGING - Check final progress dictionary
    print(f"Updated Progress Data for {username}: {progress_data}")
    return progress_data

def db_save_chat_message(username, role, content):
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO chat_history (username, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (username, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False
    conn.close()
    return True

def db_get_chat_history(username):
    messages = []
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM chat_history WHERE username = ? ORDER BY timestamp",
        (username,)
    )
    for row in c.fetchall():
        messages.append({"role": row[0], "content": row[1]})
    conn.close()
    return messages

def db_clear_chat_history(username):
    """Deletes all chat messages for a specific user."""
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    try:
        c.execute("DELETE FROM chat_history WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.close()
        return False


def db_get_leaderboard_data(course_name):
    """Fetch leaderboard data for a specific course."""
    leaderboard_data = []
    conn = sqlite3.connect('learning_platform.db')
    c = conn.cursor()
    
    # Get all students enrolled in the given course
    c.execute("SELECT username FROM courses_enrolled WHERE course_name = ?", (course_name,))
    enrolled_students = [row[0] for row in c.fetchall()]
    
    for username in enrolled_students:
        # Get average quiz score for this course (Ensure default value if no quiz is taken)
        c.execute(
            "SELECT AVG(score) FROM quiz_scores WHERE username = ? AND course_name = ?",
            (username, course_name)
        )
        avg_score_result = c.fetchone()[0]
        avg_score = avg_score_result if avg_score_result is not None else 0  # ✅ Ensure it's always a number
        
        # Get progress for this course only (Ensure default value if no progress recorded)
        progress_data = db_get_progress_data(username)
        avg_progress = progress_data.get(course_name, 0)  # ✅ Default to 0 if no progress
        
        # ✅ Ensure 'Total Score' is always calculated
        total_score = (avg_score * 0.7) + (avg_progress * 0.3)
        
        leaderboard_data.append({
            "Username": username,
            "Avg Quiz Score": avg_score,
            "Course Progress": avg_progress,
            "Total Score": total_score  #  Ensuring 'Total Score' exists
        })
    
    conn.close()
    
    #  Ensure sorting does not fail if some users have no data
    if leaderboard_data:
        leaderboard_data = sorted(leaderboard_data, key=lambda x: x.get("Total Score", 0), reverse=True)

    return leaderboard_data


# Helper functions

def get_download_link(file_path, file_name):
    with open(file_path, "rb") as file:
        contents = file.read()
    b64 = base64.b64encode(contents).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">Download {file_name}</a>'

def simulate_ml_recommendation(user_data):
    """Simple ML model to recommend courses based on user activity"""
    courses = list(COURSES.keys())
    
    if not user_data.get("courses_enrolled"):
        return random.choice(courses)
    
    # Check quiz performance and recommend accordingly
    low_score_courses = []
    for course, score in user_data.get("quiz_scores", {}).items():
        if score < 70:
            low_score_courses.append(course)
    
    if low_score_courses:
        return random.choice(low_score_courses)
    else:
        # Recommend a new course
        enrolled = set(user_data.get("courses_enrolled", []))
        available = [c for c in courses if c not in enrolled]
        if available:
            return random.choice(available)
        else:
            return "You've explored all our courses! Well done!"

def chat_with_gemma(query, user_data=None):
    """Function to interact with Forefront AI API"""
    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    context = "You are an AI learning assistant for an educational platform."
    
    if user_data:
        courses_enrolled = user_data.get("courses_enrolled", [])
        quiz_scores = user_data.get("quiz_scores", {})
        
        if courses_enrolled:
            context += f" The student is enrolled in: {', '.join(courses_enrolled)}."
        
        if quiz_scores:
            low_scores = [course for course, score in quiz_scores.items() if score < 70]
            high_scores = [course for course, score in quiz_scores.items() if score >= 70]
            
            if low_scores:
                context += f" They need more help with: {', '.join(low_scores)}."
            if high_scores:
                context += f" They're performing well in: {', '.join(high_scores)}."
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "google/gemma-3-27b-it:free",  
        "messages": [
            {"role": "system", "content": context},
            {"role": "user", "content": query}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "No response from AI.")
    except requests.exceptions.RequestException as e:
        return f"API request failed: {e}"

# UI Functions
def render_login_page():
    st.title("🧠 AI Learning Platform")
    params = st.query_params
    
    tab1, tab2, tab3, tab4 = st.tabs(["Login", "Sign Up", "Admin Login", "Forgot Password"])
    
    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_button"):
            if db_authenticate(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.current_page = "dashboard"
                st.success("Login successful!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        new_username = st.text_input("Username", key="signup_username")
        new_password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password")
        email = st.text_input("Email")
        
        if st.button("Sign Up", key="signup_button"):
            if new_password != confirm_password:
                st.error("Passwords do not match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long")
            elif not is_valid_email(email):
                st.error("Please enter a valid email address")
            else:
                if db_create_user(new_username, new_password, email):
                    st.success("Account created successfully! Please login.")
                else:
                    st.error("Username already exists")

    with tab3:
        admin_username = st.text_input("Admin Username", key="admin_username")
        admin_password = st.text_input("Admin Password", type="password", key="admin_password")
        
        if st.button("Admin Login", key="admin_login_button"):
            if db_authenticate_admin(admin_username, admin_password):
                st.session_state.logged_in = True
                st.session_state.username = admin_username
                st.session_state.is_admin = True
                st.session_state.current_page = "admin_dashboard"
                st.success("Admin login successful!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid admin credentials")
    with tab4:
        st.subheader("Forgot Password")
        username_for_reset = st.text_input("Enter your username", key="forgot_username")
        
        if st.button("Send Password via Email"):
            if not username_for_reset:
                st.error("Please enter your username")
                return
            
            # Check if username exists
            email = db_get_user_email(username_for_reset)
            if not email:
                st.error("Username not found")
                return
            
            # Store token in database
            if send_password_email(email, username_for_reset):
                st.success(f"Your password has been sent to your email ({email})")
            else:
                st.error("Failed to send email. Please try again later.")
         
def render_admin_dashboard():
    if st.session_state.force_change_password:
        st.warning("You are using a temporary password. Please change your password now.")

        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")

        if st.button("Update Password"):
            if new_password != confirm_new_password:
                st.error("Passwords do not match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                if db_update_admin_password(st.session_state.username, new_password):
                    st.success("Password updated successfully! Please login again.")
                    time.sleep(2)
                    st.session_state.logged_in = False
                    st.session_state.username = ""
                    st.session_state.is_admin = False
                    st.session_state.force_change_password = False
                    st.rerun()
                else:
                    st.error("Failed to update password. Please try again.")

        st.stop()  # 🛑 VERY important: Stop rest of Admin Dashboard from showing
    st.title(f"Admin Dashboard - Welcome, {st.session_state.username}! ")
    
    # Navigation
    menu = ["Student Management", "Course Management", "Notes Management", "Analytics", "Student Queries", "Admin Settings"]
    selected = st.sidebar.radio("Admin Navigation", menu)
    
    if selected == "Student Management":
        st.subheader("Student Management")
        
        # Get all students
        students = db_get_all_students()
        
        if not students:
            st.info("No students registered yet")
        else:
            # Display students in a dataframe
            student_df = pd.DataFrame(students)
            st.dataframe(student_df)
            
            # Remove student option
            st.subheader("Remove Student")
            student_to_remove = st.selectbox("Select student to remove", [s["username"] for s in students])
            
            if st.button("Remove Student"):
                if db_remove_student(student_to_remove):
                    st.success(f"Student {student_to_remove} removed successfully")
                    st.rerun()
                else:
                    st.error("Failed to remove student")
    
    elif selected == "Course Management":
        load_courses()
        st.subheader("Course Management")
    
        # Add new course
        st.write("### Add New Course")
        new_course_name = st.text_input("Course Name")
    
        if st.button("Add Course"):
            if new_course_name:
                if db_add_course(new_course_name):
                    st.success("Added successfully")
                    time.sleep(2) 
                    refresh_courses()
                    st.rerun()
                else:
                    st.error("Course already exists")
    
        # Add video to course
        st.write("### Add Video to Course")
        course_for_video = st.selectbox("Select Course", list(COURSES.keys()))
        video_title = st.text_input("Video Title")
        video_url = st.text_input("Video URL (YouTube)")
    
        if st.button("Add Video"):
            if video_title and video_url:
                if db_add_video_to_course(course_for_video, video_title, video_url):
                    st.success(f"Video '{video_title}' added to {course_for_video}")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Failed to add video. It may already exist.")

        # Add quiz to course
        st.write("### Add Quiz to Course")
        course_for_quiz = st.selectbox("Select Course", list(COURSES.keys()), key="quiz_course")
        quiz_title = st.text_input("Quiz Title")
    
        # === AI-powered Quiz Generation ===
        st.write("Or use AI to generate questions automatically")

        # Suggested topics based on course
        course_topics_map = {
        "Python Programming": ["Variables", "Functions", "Data Types", "Loops", "OOP"],
        "Machine Learning": ["Supervised Learning", "Unsupervised Learning", "Regression", "Classification"],
        "Data Structures": ["Arrays", "Linked Lists", "Stacks", "Queues", "Trees"],
        "Web Development": ["HTML", "CSS", "JavaScript", "Flask", "Django"],
        "Database Management": ["SQL", "NoSQL", "ORM", "SQLAlchemy", "MongoDB"],
        }

        # Topic selection
        suggested_topics = course_topics_map.get(course_for_quiz, [])
        selected_topic = st.selectbox("Choose a suggested topic (or type your own)", suggested_topics + ["Other"], index=0)

        if selected_topic == "Other":
            generate_topic = st.text_input("Enter Custom Topic", key="custom_topic")
        else:
            generate_topic = selected_topic

        # Question settings
        num_questions = st.slider("Number of Questions", min_value=1, max_value=10, value=3, step=1)
        difficulty = st.selectbox("Select Difficulty Level", ["Easy", "Medium", "Hard"], index=1)

        # Generate from AI
        if st.button("Generate with AI"):
            if generate_topic:
                prompt = f"""
                Generate {num_questions} multiple-choice questions in JSON format for the topic '{generate_topic}'.
                Difficulty level: {difficulty}.

                Each question should follow this format:

                [
                {{
                "question": "Your question here",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "answer": 1  // (0-based index of the correct option)
                }},
                ...
                ]

                Only return the JSON array. Do not include explanations, notes, or markdown formatting.
                """

                response = chat_with_gemma(prompt)

                try:
                    json_str = response.strip()
                    if "```" in json_str:
                        # Strip code block formatting if present
                        json_str = json_str.split("```")[1] if "json" in json_str else json_str.split("```")[0]

                    questions = json.loads(json_str)

                    if isinstance(questions, list) and all("question" in q and "options" in q and "answer" in q for q in questions):
                        st.session_state.generated_quiz_preview = questions
                        st.success("AI-generated questions ready for preview below.")
                    else:
                        st.error("AI response structure is invalid. Please try again.")

                except json.JSONDecodeError:
                    st.error("Failed to parse AI response as JSON.")
                    st.code(response)

        # Preview mode
        if "generated_quiz_preview" in st.session_state and st.session_state.generated_quiz_preview:
            st.markdown("---")
            st.subheader("📝 Preview & Edit AI-Generated Quiz")
            edited_questions = []

            for i, q in enumerate(st.session_state.generated_quiz_preview):
                st.write(f"**Question {i+1}**")
                question_text = st.text_input(f"Edit Question {i+1}", value=q["question"], key=f"preview_q{i}")

                options = []
                for j in range(4):
                    opt = st.text_input(f"Option {j+1} for Q{i+1}", value=q["options"][j], key=f"preview_q{i}_opt{j}")
                    options.append(opt)

                answer = st.number_input(f"Correct Answer Index (0-3) for Q{i+1}", min_value=0, max_value=3, value=q["answer"], key=f"preview_q{i}_ans")

                edited_questions.append({
                "question": question_text,
                "options": options,
                "answer": answer
                })

            if st.button("✅ Confirm & Load into Quiz Form"):
                st.session_state.quiz_questions = edited_questions
                del st.session_state.generated_quiz_preview  # Clear preview
                st.success("Questions loaded into form. You can now save or modify them.")
            st.rerun()

        # Manual Quiz Creation
        st.write("Quiz Questions:")
    
        if 'quiz_questions' not in st.session_state:
            st.session_state.quiz_questions = [{
            "question": "",
            "options": ["", "", "", ""],
            "answer": 0
            }]
    
        for i, q in enumerate(st.session_state.quiz_questions):
            st.write(f"**Question {i+1}**")
            q["question"] = st.text_input(f"Question {i+1}", value=q["question"], key=f"q{i}")
        
            for j in range(4):
                q["options"][j] = st.text_input(f"Option {j+1}", value=q["options"][j], key=f"q{i}_opt{j}")
        
            q["answer"] = st.number_input(f"Correct Answer Index (0-3)", min_value=0, max_value=3, value=q["answer"], key=f"q{i}_ans")
    
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Add Question"):
                st.session_state.quiz_questions.append({
                "question": "",
                "options": ["", "", "", ""],
                "answer": 0
            })
                st.rerun()
    
        with col2:
            if len(st.session_state.quiz_questions) > 1:
                if st.button("Remove Last Question"):
                    st.session_state.quiz_questions.pop()
                    st.rerun()
    
        if st.button("Save Quiz"):
            if quiz_title and all(q["question"] for q in st.session_state.quiz_questions):
                if db_add_quiz_to_course(course_for_quiz, quiz_title, st.session_state.quiz_questions):
                    st.success(f"Quiz '{quiz_title}' added to {course_for_quiz}")
                    st.session_state.quiz_questions = [{
                    "question": "",
                    "options": ["", "", "", ""],
                    "answer": 0
                    }]
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Failed to add quiz. It may already exist.")

        st.markdown("---")
        st.subheader("🗑️ Delete Course, Video, or Quiz")

        # Delete Course
        st.write("### Delete Course")
        delete_course = st.selectbox("Select Course to Delete", [c["name"] for c in db_get_all_courses()])
        if st.button("❌ Delete Selected Course"):
            db_delete_course(delete_course)
            st.success(f"✅ Course '{delete_course}' deleted.")
            st.rerun()

        # Delete Video
        st.write("### Delete Video")
        selected_course_v = st.selectbox("Select Course for Videos", list(COURSES.keys()), key="delete_video_course")
        course_videos = COURSES.get(selected_course_v, {}).get("videos", [])
        video_titles = [v["title"] for v in course_videos]

        if video_titles:
            delete_video = st.selectbox("Select Video to Delete", video_titles)
            if st.button("❌ Delete Selected Video"):
                db_delete_video(delete_video)
                st.success(f"✅ Video '{delete_video}' deleted from {selected_course_v}.")
                st.rerun()
        else:
            st.info(f"No videos available for {selected_course_v}")

        # Delete Quiz
        st.write("### Delete Quiz")
        selected_course_q = st.selectbox("Select Course for Quizzes", list(COURSES.keys()), key="delete_quiz_course")
        course_quizzes = COURSES.get(selected_course_q, {}).get("quizzes", [])
        quiz_titles = [q["title"] for q in course_quizzes]

        if quiz_titles:
            delete_quiz = st.selectbox("Select Quiz to Delete", quiz_titles)
            if st.button("❌ Delete Selected Quiz"):
                db_delete_quiz(delete_quiz)
                st.success(f"✅ Quiz '{delete_quiz}' deleted from {selected_course_q}.")
                st.rerun()
        else:
            st.info(f"No quizzes available for {selected_course_q}")



    elif selected == "Notes Management":
        st.subheader("Notes")
        
        # Upload notes
        st.write("### Upload Notes")
        
        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])
        note_title = st.text_input("Note Title")
        
        if uploaded_file is not None and note_title:
            # Create a notes directory if it doesn't exist
            if not os.path.exists("notes"):
                os.makedirs("notes")
            
            # Save the file
            file_path = os.path.join("notes", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Save note info to database
            if db_save_note(note_title, uploaded_file.name, file_path, st.session_state.username):
                st.success(f"Note '{note_title}' uploaded successfully!")
        
        # Display notes
        st.write("### Admin Uploaded Notes")
        
        user_data = db_get_user_data(st.session_state.username)
        user_notes = user_data.get("notes", [])
        
        if not user_notes:
            st.info("You haven't uploaded any notes yet")
        else:
            for note in user_notes:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{note['title']}**")
                    st.write(f"Uploaded on: {note['uploaded_at']}")
                
                with col2:
                    if os.path.exists(note["path"]):
                        st.markdown(get_download_link(note["path"], note["filename"]), unsafe_allow_html=True)

                with col3:
                    if st.button("🗑 Delete", key=f"del_admin_note_{note['path']}"):
                        try:
                            os.remove(note["path"])
                            db_delete_note(note["path"])
                            st.success(f"Note '{note['title']}' deleted successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete note: {str(e)}")        
        
        # Display shared notes from other users
        st.write("### Notes from  Students")
        
        all_notes = db_get_all_notes()
        other_notes = [note for note in all_notes if note["uploaded_by"] != st.session_state.username]
        
        if not other_notes:
            st.info("No notes shared by  students yet")
        else:
            for note in other_notes:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{note['title']}**")
                    st.write(f"Uploaded by: {note['uploaded_by']} on {note['uploaded_at']}")
                
                with col2:
                    if os.path.exists(note["path"]):
                        st.markdown(get_download_link(note["path"], note["filename"]), unsafe_allow_html=True)

                with col3:
                    if st.button("🗑 Delete", key=f"del_student_note_{note['path']}"):
                        try:
                            os.remove(note["path"])
                            db_delete_note(note["path"])
                            st.success(f"Note '{note['title']}' deleted successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete note: {str(e)}")        
    
    elif selected == "Analytics":
        st.subheader("Platform Analytics")
        
        # Get database statistics
        conn = sqlite3.connect('learning_platform.db')
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM courses_enrolled")
        enrollments_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM quiz_scores")
        quiz_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM notes")
        notes_count = c.fetchone()[0]
        
        conn.close()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Students", user_count)
        with col2:
            st.metric("Course Enrollments", enrollments_count)
        with col3:
            st.metric("Quizzes Taken", quiz_count)
        with col4:
            st.metric("Notes Shared", notes_count)
        
        # Course popularity chart
        st.write("### Course Popularity")
        
        conn = sqlite3.connect('learning_platform.db')
        c = conn.cursor()
        c.execute("SELECT course_name, COUNT(*) FROM courses_enrolled GROUP BY course_name")
        course_data = c.fetchall()
        conn.close()
        
        if course_data:
            course_df = pd.DataFrame(course_data, columns=["Course", "Enrollments"])
            fig = px.pie(course_df, values='Enrollments', names='Course', title='Course Enrollment Distribution')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No enrollment data available yet")

    elif selected == "Student Queries":
        st.markdown("---")
        st.subheader("📬 Student Contact Messages")

        messages = db_get_all_contact_messages()

        if messages:
            for msg in messages:
                with st.expander(f"📩 {msg[2]} - from {msg[1]} ({msg[4]})"):
                    st.write(f"**Student:** {msg[1]}")
                    st.write(f"**Subject:** {msg[2]}")
                    st.write(f"**Message:** {msg[3]}")

                    reply_message = st.text_area(f"Reply to {msg[1]}", key=f"reply_text_{msg[0]}")

                    if st.button(f"Send Reply to {msg[1]}", key=f"send_reply_{msg[0]}"):
                        if reply_message.strip():
                            db_send_admin_reply(msg[0], reply_message)  
                            st.success("✅ Reply sent successfully!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("⚠️ Reply cannot be empty.")
        else:
            st.info("No student queries found.")

    
    elif selected == "Admin Settings":
        st.subheader("Admin Settings")
        
        # Add new admin
        st.write("### Add New Admin")
        new_admin_username = st.text_input("Admin Username")
        new_admin_email = st.text_input("Admin Email")
        
        if st.button("Add Admin"):
            if new_admin_username and new_admin_email:
                if db_create_admin(new_admin_username, new_admin_email):
                    st.success(f"Admin '{new_admin_username}' added successfully. Credentials sent via email.")
                else:
                    st.error("Admin already exists")

        # 🔐 Admin Management Section
        st.markdown("---")
        st.subheader("🔐 Admin Management")

        # Only allow the main admin to access this section
        if st.session_state.username != "admin":
            st.info("Only the main admin can manage other admins.")
        else:
            # Only executed if current user is the main admin
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT username, email, joined_date FROM admins")
            admins = c.fetchall()
            conn.close()

            st.write("### Current Admins:")
    
            for admin in admins:
                admin_user, email, joined_date = admin
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.write(f"👤 **{admin_user}**")
                    st.caption(f"📧 {email}")
                    st.caption(f"🗓️ Joined: {joined_date}")
                with col2:
                    if admin_user != "admin":  # Prevent deletion of main admin
                        if st.button(f"Remove", key=f"remove_admin_{admin_user}"):
                            conn = get_connection()
                            c = conn.cursor()
                            c.execute("DELETE FROM admins WHERE username = ?", (admin_user,))
                            conn.commit()
                            conn.close()
                            st.success(f"Admin '{admin_user}' removed.")
                            st.rerun()


def render_dashboard():
    if st.session_state.force_student_change_password:
        st.warning("You are using a temporary password. Please change your password now.")

        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")

        if st.button("Update Password"):
            if new_password != confirm_new_password:
                st.error("Passwords do not match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long")
            else:
                if db_update_user_password(st.session_state.username, new_password):
                    st.success("Password updated successfully! Please login again.")
                    time.sleep(2)
                    st.session_state.logged_in = False
                    st.session_state.username = ""
                    st.session_state.is_admin = False
                    st.session_state.force_student_change_password = False
                    st.rerun()
                else:
                    st.error("Failed to update password. Please try again.")
        st.stop()  # VERY IMPORTANT — do not show dashboard if temp password  
    st.title(f"Welcome, {st.session_state.username}! 👋")
    user_profile = db_get_user_profile(st.session_state.username)
    
    # Navigation
    menu = ["Dashboard", "Courses", "Notes", "Leaderboard", "AI Chat", "Contact Admin", "Settings"]
    selected = st.sidebar.radio("Navigation", menu)
    
    if user_profile.get("profile_photo"):
        profile_image = Image.open(io.BytesIO(user_profile.get("profile_photo")))
        st.sidebar.image(profile_image, width=100, caption=st.session_state.username)
    else:
        # Display default image or initials
        st.sidebar.markdown(f"## 👤 {st.session_state.username}")

    if selected == "Dashboard":
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Your Learning Journey")
            user_data = db_get_user_data(st.session_state.username)
            
            # Enrollment status
            if not user_data.get("courses_enrolled"):
                st.info("You're not enrolled in any courses yet. Check out our courses section!")
            else:
                st.write(f"You're enrolled in {len(user_data.get('courses_enrolled', []))} courses")
            
            # Recent activity
            st.subheader("Recent Activity")
            activities = []
            for course, result in user_data.get("quiz_scores", {}).items():
                activities.append(f"Quiz score for {course}: {result}%")
            
            if activities:
                for activity in activities[-3:]:
                    st.text(activity)
            else:
                st.text("No recent activity")
        
        with col2:
            st.subheader("Recommendation")
            recommendation = simulate_ml_recommendation(user_data)
            st.info(f"Recommended: {recommendation}")
    
    elif selected == "Courses":
        load_courses() 
        st.subheader("Available Courses")
        
        tabs = st.tabs(list(COURSES.keys()))
        
        for i, (course_name, course_data) in enumerate(COURSES.items()):
            with tabs[i]:
                st.write(f"### {course_name}")
                
                # Enroll button
                user_data = db_get_user_data(st.session_state.username)
                if course_name not in user_data.get("courses_enrolled", []):
                    if st.button(f"Enroll in {course_name}", key=f"enroll_{course_name}"):
                        if db_enroll_course(st.session_state.username, course_name):
                            st.success(f"Successfully enrolled in {course_name}")
                            st.rerun()
                else:
                    st.success(f"You are enrolled in this course")
                
                # Video lectures
                st.subheader("Video Lectures")
                for video in course_data["videos"]:
                    with st.expander(video["title"]):
                        st_player(video["url"])
                        
                        # Mark as watched
                        videos_watched = db_get_videos_watched(st.session_state.username)
                        if video["title"] not in videos_watched:
                            if st.button("Mark as Watched", key=f"watch_{video['title']}"):
                                if db_mark_video_watched(st.session_state.username, video["title"], course_name):
                                    st.success("Video marked as watched!")
                                    st.rerun()
                        else:
                            st.success("✓ Watched")
                
                # Quizzes
                st.subheader("Quizzes")
                for quiz in course_data["quizzes"]:
                    with st.expander(quiz["title"]):
                        # Check if quiz already taken
                        quiz_id = f"{course_name}_{quiz['title']}"
                        conn = sqlite3.connect('learning_platform.db')
                        c = conn.cursor()
                        c.execute(
                            "SELECT score FROM quiz_scores WHERE username = ? AND course_name = ? AND quiz_name = ?",
                            (st.session_state.username, course_name, quiz['title'])
                        )
                        result = c.fetchone()
                        conn.close()
                        
                        if result:
                            st.write(f"Your score: {result[0]}%")
                            if st.button("Retake Quiz", key=f"retake_{quiz_id}"):
                                conn = sqlite3.connect('learning_platform.db')
                                c = conn.cursor()
                                c.execute(
                                    "DELETE FROM quiz_scores WHERE username = ? AND course_name = ? AND quiz_name = ?",
                                    (st.session_state.username, course_name, quiz['title'])
                                )
                                conn.commit()
                                conn.close()
                                st.rerun()
                        else:
                            # Display quiz
                            answers = []
                            for i, q in enumerate(quiz["questions"]):
                                st.write(f"**Q{i+1}: {q['question']}**")
                                answer = st.radio(f"Select your answer for Q{i+1}", 
                                                options=[o for o in q['options']], 
                                                key=f"q_{quiz_id}_{i}")
                                answers.append(q['options'].index(answer))
                            
                            if st.button("Submit Quiz", key=f"submit_{quiz_id}"):
                                # Calculate score
                                correct = 0
                                for i, q in enumerate(quiz["questions"]):
                                    if answers[i] == q["answer"]:
                                        correct += 1
                                
                                score = (correct / len(quiz["questions"])) * 100
                                
                                # Save results to database
                                if db_save_quiz_result(st.session_state.username, course_name, quiz['title'], score):
                                    st.success(f"Quiz submitted! Your score: {score}%")
                                    st.rerun()
    
    elif selected == "Notes":
        st.subheader("Your Notes")
        
        # Upload notes
        st.write("### Upload Notes")
        
        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])
        note_title = st.text_input("Note Title")
        
        if uploaded_file and note_title:
            if st.button("📤 Upload Note"):
                # Create a notes directory if it doesn't exist
                if not os.path.exists("notes"):
                    os.makedirs("notes")
            
                # Save the file
                file_path = os.path.join("notes", uploaded_file.name)
                try:
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
            
                    # Save note info to database
                    if db_save_note(note_title, uploaded_file.name, file_path, st.session_state.username):
                        st.success(f"Note '{note_title}' uploaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to upload note '{note_title}'. Please try again.")
                except Exception as e:
                    st.error(f"❌ Error while uploading note: {str(e)}")

        # Display notes
        st.write("### Your Uploaded Notes")
        
        user_data = db_get_user_data(st.session_state.username)
        user_notes = user_data.get("notes", [])
        
        if not user_notes:
            st.info("You haven't uploaded any notes yet")
        else:
            for note in user_notes:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{note['title']}**")
                    st.write(f"Uploaded on: {note['uploaded_at']}")
                
                with col2:
                    if os.path.exists(note["path"]):
                        st.markdown(get_download_link(note["path"], note["filename"]), unsafe_allow_html=True)

                with col3:
                    if st.button("🗑 Delete", key=f"del_admin_note_{note['path']}"):
                        try:
                            os.remove(note["path"])
                            db_delete_note(note["path"])
                            st.success(f"Note '{note['title']}' deleted successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete note: {str(e)}")        
        
        # Display shared notes from other users
        st.write("### Notes from Other Students and Admins ")
        
        all_notes = db_get_all_notes()
        other_notes = [note for note in all_notes if note["uploaded_by"] != st.session_state.username]
        
        if not other_notes:
            st.info("No notes shared by other students yet")
        else:
            for note in other_notes:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{note['title']}**")
                    st.write(f"Uploaded by: {note['uploaded_by']} on {note['uploaded_at']}")
                
                with col2:
                    if os.path.exists(note["path"]):
                        st.markdown(get_download_link(note["path"], note["filename"]), unsafe_allow_html=True)
    

    
    elif selected == "Leaderboard":
        st.subheader("📊 Course-Wise Leaderboards")
    
        # Load all available courses
        load_courses()
    
        # Create tabs for each course
        course_tabs = st.tabs(list(COURSES.keys()))
    
        for i, course_name in enumerate(COURSES.keys()):
            with course_tabs[i]:
                st.write(f"### {course_name} Leaderboard")
            
                # Fetch leaderboard for this specific course
                leaderboard_data = db_get_leaderboard_data(course_name)
            
                if leaderboard_data:
                    # Convert to DataFrame
                    leaderboard_df = pd.DataFrame(leaderboard_data)
                
                    # Add rank column
                    leaderboard_df.index = leaderboard_df.index + 1
                    leaderboard_df = leaderboard_df.rename_axis("Rank").reset_index()
                
                    # Highlight current user
                    def highlight_user(row):
                        return ['background-color: #FFFF00' if row.Username == st.session_state.username else '' for _ in row]
                
                    st.dataframe(leaderboard_df.style.apply(highlight_user, axis=1), width=800)
                
                    # Top performers chart
                    top_5 = leaderboard_df.head(5)
                
                    fig = px.bar(top_5, x="Username", y="Total Score",
                            title=f"Top 5 Performers in {course_name}",
                            color="Username",
                            labels={"Total Score": "Overall Performance"},
                            text="Total Score")
                
                    fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No leaderboard data available for {course_name}")

    
    elif selected == "AI Chat":
        st.subheader("AI Learning Assistant")
        
        # Show DeepSeek AI information
        st.markdown("""
        ### 🤖 AI Assistant
        This AI assistant uses Google powerful Gemma 3 7b model to help with your learning journey.
        """)
        
        if st.button("🗑️ Clear Chat"):
            if db_clear_chat_history(st.session_state.username):
                st.success("Chat history cleared!")
                st.session_state.chat_history = []  # Reset chat in session state
                st.rerun()  # 🔄 Force UI refresh    
    
        # Get chat history from database
        chat_history = db_get_chat_history(st.session_state.username)
        
        # Display chat history
        for message in chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Chat input
        user_query = st.chat_input("Ask me anything about your courses...")
        
        if user_query:
            # Save user message to database
            db_save_chat_message(st.session_state.username, "user", user_query)
            
            # Display user message
            with st.chat_message("user"):
                st.write(user_query)
            
            # Generate AI response
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                # Get user data for personalized responses
                user_data = db_get_user_data(st.session_state.username)
                
                with st.spinner("Thinking..."):
                    # Call ollama API
                    assistant_response = chat_with_gemma(user_query, user_data)
                
                # Simulate typing effect
                for chunk in assistant_response.split():
                    full_response += chunk + " "
                    response_placeholder.markdown(full_response + "▌")
                    time.sleep(0.02)
                
                response_placeholder.markdown(full_response)
            
            # Save assistant response to database
            db_save_chat_message(st.session_state.username, "assistant", assistant_response)

    elif selected == "Contact Admin":
        st.subheader("📬 Contact Admin")

        subject = st.text_input("Subject")
        message = st.text_area("Write your issue or query here")

        if st.button("📤 Send Message"):
            if subject and message:
                db_save_contact_message(st.session_state.username, subject, message)
                st.success("✅ Message sent successfully!")
            else:
                st.error("⚠️ Both Subject and Message are required.")

        # Show admin replies
        st.markdown("---")
        st.subheader("📩 Replies from Admin")

        replies = db_get_admin_replies_for_student(st.session_state.username)

        if replies:
            for reply in replies:
                st.write(f"**Subject:** {reply[0]}")
                st.write(f"**Your Query:** {reply[1]}")
                st.success(f"**Admin Reply:** {reply[2]}  (on {reply[3]})")
                st.markdown("---")
        else:
            st.info("No replies yet from admin.")

    
    elif selected == "Settings":
        st.subheader("App Settings")

        settings_tab1, settings_tab2, settings_tab3 = st.tabs(["Profile", "Account", "About"])

        with settings_tab1:
            st.subheader("Profile Settings")
            
            # Get current user profile data
            user_profile = db_get_user_profile(st.session_state.username)
            
            # Profile photo upload
            st.write("### Profile Photo")
            
            # Display current photo if available
            if user_profile.get("profile_photo"):
                profile_image = Image.open(io.BytesIO(user_profile.get("profile_photo")))
                st.image(profile_image, width=150, caption="Current profile photo")
            
            uploaded_photo = st.file_uploader("Upload new profile photo", type=["jpg", "jpeg", "png"])
            
            if uploaded_photo is not None:
                # Display preview
                image = Image.open(uploaded_photo)
                st.image(image, width=150, caption="Preview")
                
                # Resize and convert to bytes for storage
                img_resized = image.resize((200, 200))
                buf = io.BytesIO()
                img_resized.save(buf, format="JPEG")
                img_bytes = buf.getvalue()
                
                if st.button("Save Profile Photo"):
                    if db_update_user_profile(st.session_state.username, profile_photo=img_bytes):
                        st.success("Profile photo updated successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to update profile photo")
        
        with settings_tab2:
            st.subheader("Account Settings")
            
            # Email update
            current_email = user_profile.get("email", "")
            new_email = st.text_input("Email", value=current_email)
            
            if new_email != current_email:
                if st.button("Update Email"):
                    if db_update_user_profile(st.session_state.username, email=new_email):
                        st.success("Email updated successfully!")
                    else:
                        st.error("Failed to update email")
            
            # Password change
            st.write("### Change Password")
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.button("Change Password"):
                if not db_authenticate(st.session_state.username, current_password):
                    st.error("Current password is incorrect")
                elif new_password != confirm_password:
                    st.error("New passwords don't match")
                elif not new_password:
                    st.error("New password cannot be empty")
                else:
                    if db_update_user_profile(st.session_state.username, password=new_password):
                        st.success("Password changed successfully!")
                    else:
                        st.error("Failed to update password")
            
        with settings_tab3:
                st.markdown("""
        ### About Gemma 3-27B
        
        This application uses the Google Gemma 3-27B model to provide intelligent responses to your questions
        and help with your learning journey. The AI is configured to understand your progress in courses and
        provide personalized assistance.
        
        """)
        
# Main app logic
def main():
    # Display page based on current state
    if st.session_state.current_page == "login" and not st.session_state.logged_in:
        render_login_page()
    elif st.session_state.logged_in and st.session_state.is_admin:
        # Admin logout button in sidebar
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.is_admin = False
            st.session_state.current_page = "login"
            st.rerun() 
        render_admin_dashboard()       
    elif st.session_state.logged_in:
        # Logout button in sidebar
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_page = "login"
            st.rerun()
        
        render_dashboard()

if __name__ == "__main__":
    main()
