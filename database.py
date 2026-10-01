# database.py
# Function:
# DB Create
# DB Table create
# New User Entry
# Login Data Fetch
# User count, login in last 24 hours count, Not log in count

import sqlite3
import os
from datetime import datetime

# werkzeug - helper library - scrambles a password
from werkzeug.security import generate_password_hash, check_password_hash


# This builds the full path to our database file
DB_PATH = os.path.join(os.path.dirname(__file__), "medibank.db")


def get_connection():
    """
    This function opens a connection to our SQLite database file.
    Almost every function below starts by calling this.
    """
    connection = sqlite3.connect(DB_PATH)
    return connection


def create_database():
    """
    This function creates the 'users' table if it does not exist yet.
    We call this ONE TIME, right when the app starts (in main.py).
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Create a table with 6 columns, matching the structure
    # user_id, email, hashed_password, policy_type, role, last_login.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            policy_type TEXT,
            role TEXT NOT NULL,
            last_login TEXT
        )
    """)

    connection.commit()
    connection.close()


def add_user(user_id, email, plain_password, policy_type, role):
    """
    This function adds ONE new row (one new user) into the database.
    This will be used by the "Add New User" form in the Admin Panel.

    plain_password = the password typed by the admin, not scrambled yet.
    We scramble it here, right before saving, using generate_password_hash().

    It returns two things:
    success -> True or False
    message -> a short text we can show on screen
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Turn the plain password into scrambled version.
    hashed_password = generate_password_hash(plain_password)

    try:
        cursor.execute("""
            INSERT INTO users (user_id, email, hashed_password, policy_type, role, last_login)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, email, hashed_password, policy_type, role, None))

        connection.commit()
        success = True
        message = "User added successfully."

    except sqlite3.IntegrityError:
        # If user id is not unique
        success = False
        message = "This User ID already exists. Please use a different one."

    connection.close()
    return success, message


def get_user_by_id(user_id):
    """
    This function looks up ONE user using their user_id.
    It returns the user as a simple dictionary, or None if not found.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    # turn the row (a plain tuple) into a dictionary, so it is
    # easier to read later
    user_dict = {
        "user_id": row[0],
        "email": row[1],
        "hashed_password": row[2],
        "policy_type": row[3],
        "role": row[4],
        "last_login": row[5],
    }
    return user_dict


def verify_login(user_id, plain_password):
    """
    This function checks if a user_id and password are correct.

    It returns two things: (is_valid, role)
    is_valid -> True or False
    role     -> "student" or "admin" (only meaningful if is_valid is True)
    """
    user = get_user_by_id(user_id)

    if user is None:
        # No user id exist
        return False, None

    # check_password_hash compares the typed password and returns True or False.
    password_ok = check_password_hash(user["hashed_password"], plain_password)

    if password_ok:
        return True, user["role"]
    else:
        return False, None


def update_last_login(user_id):
    """
    This function updates the last_login column to RIGHT NOW,
    using ISO format (example: 2026-11-25 14:30:00).
    We call this every time a login is successful.
    """
    connection = get_connection()
    cursor = connection.cursor()

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE users SET last_login = ? WHERE user_id = ?
    """, (now_text, user_id))

    connection.commit()
    connection.close()


def get_all_students():
    """
    This function returns every student's user_id and email.
    This will be used to fill the "To" dropdown list on the
    Bulk Email screen.

    It returns a list that looks like this:
    [("123456", "student1@gmail.com"), ("654321", "student2@gmail.com")]
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT user_id, email FROM users WHERE role = 'student'")
    rows = cursor.fetchall()
    connection.close()

    return rows


def get_dashboard_counts():
    """
    This function calculates the three numbers shown on the
    Admin Dashboard:

    1. total_registered -> how many students exist in total
    2. active_today      -> how many students logged in TODAY
    3. never_used        -> how many students have NEVER logged in

    We only count role = 'student', since the dashboard is about
    chatbot usage, and only students use the chatbot.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # 1. Total registered students.
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total_registered = cursor.fetchone()[0]

    # 2. Students who logged in today.
    # "Today" starts at 12:00 AM, so we compare just the DATE part
    # (the first 10 characters, like "2026-11-25") of last_login.
    today_text = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE role = 'student' AND substr(last_login, 1, 10) = ?
    """, (today_text,))
    active_today = cursor.fetchone()[0]

    # 3. Students who have NEVER logged in (last_login is still empty).
    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE role = 'student' AND last_login IS NULL
    """)
    never_used = cursor.fetchone()[0]

    connection.close()

    return total_registered, active_today, never_used


def get_students_not_logged_in_today():
    """
    This function returns the email addresses of every student who
    has NOT logged in today. This list will be used by the automatic
    daily email feature, these students are the ones who receive
    the reminder email.
    """
    connection = get_connection()
    cursor = connection.cursor()

    today_text = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT email FROM users
        WHERE role = 'student'
        AND (last_login IS NULL OR substr(last_login, 1, 10) != ?)
    """, (today_text,))

    rows = cursor.fetchall()
    connection.close()

    # rows looks like [("a@gmail.com",), ("b@gmail.com",)]
    # We turn it into a simple, plain list of emails.
    email_list = []
    for row in rows:
        email_list.append(row[0])

    return email_list