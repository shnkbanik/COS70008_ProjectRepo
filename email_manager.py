# email_manager.py
# Functionality:
# Bulk Email Send Functionality
# Scheduled Email Send Functionality
# New User Email Send Functionality
# InActive User Email Send Functionality

import smtplib
import ssl
from email.mime.text import MIMEText
import certifi
import config
import database
import threading
import time
from datetime import datetime

def send_email(to_email, subject, body):
    """
    Send email to a address
    Return (success, message):
    success -> True or False
    message -> a short text explaining what happened
    """
    # Build the email itself: who it's from, who it's to, subject, body.
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = config.SENDER_EMAIL
    message["To"] = to_email

    try:
        # create secure encrypted connection setting with certifi security certificate
        secure_context = ssl.create_default_context(cafile=certifi.where())

        # SMTP_SSL
        server = smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT,
                                   context=secure_context, timeout=15) # Timeout after 15 secounds
        server.login(config.SENDER_EMAIL, config.SENDER_APP_PASSWORD) # Sender ACC login process
        server.send_message(message) # send email
        server.quit() # Close the connection

        return True, "Email sent to " + to_email

    except Exception as error:
        # unsuccessful email send
        return False, "Could not send email to " + to_email + ". Reason: " + str(error)

def send_bulk_email(email_list, subject, body):
    """
    Send email to multiple addresses
    Return:
    * how many succeeded
    * how many failed
    """
    success_count = 0
    fail_count = 0

    for email_address in email_list:
        success, message = send_email(email_address, subject, body)
        print(message) # Print progress in the terminal
        if success:
            success_count = success_count + 1
        else:
            fail_count = fail_count + 1
    return success_count, fail_count
def send_welcome_email(student_email):
    """
    Send automatic welcome email to user after registration from admin panel
    """
    subject = "Welcome to Medibank OSHC"
    body = (
        "Hello,\n\n"
        "Your Medibank OSHC account has been created.\n"
        "Now, we are providing an advanced AI-Chatbot to our users."
        "Users experience the personal AI assistant by getting specific"
        "answers to the queries. You can log in to the system and"
        "ask questions about your OSHC policy \n\n"
        "Thank you,\n"
        "Medibank"
    )
    return send_email(student_email, subject, body)


def send_startup_email_to_all_students():
    """
    Send update email to students in the database.
    Send email when the app first starts
    Please set SEND_ON_STARTUP = True.
    """
    students = database.get_all_students()

    # students looks like [("id1", "email1"), ("id2", "email2")]
    # We only need the email part for sending.
    email_list = []
    for user_id, email in students:
        email_list.append(email)
    subject = "Medibank OHSC - New Update for APP Available"
    body = (
        "Hello,\n\n"
        "The Medibank OSHC has a new update available in the APP."
        "Now, we are providing an advanced AI-Chatbot to our users."
        "Users experience the personal AI assistant by getting specific"
        "answers to the queries. Please log in and try it out.\n\n"
        "Thank you,\n"
        "Medibank"
    )
    success_count, fail_count = send_bulk_email(email_list, subject, body)
    print("Startup email finished. Sent:", success_count, "Failed:", fail_count)


def send_daily_reminder_emails():
    """
    Send reminder email to registered students who has not logged in yet.
    This send automatically by scheduler
    time set in config.py (DAILY_EMAIL_HOUR and DAILY_EMAIL_MINUTE).
    """
    email_list = database.get_students_not_logged_in()
    subject = "Don't forget - Medibank AI-Chatbot is here to help"
    body = (
        "Hello,\n\n"
        "Now, we are providing an advanced AI-Chatbot to our users."
        "Users experience the personal AI assistant by getting specific"
        "answers to the queries. Please log in and try it out.\n\n"
        "Thank you,\n"
        "Medibank"
    )
    success_count, fail_count = send_bulk_email(email_list, subject, body)
    print("Daily reminder finished. Sent:", success_count, "Failed:", fail_count)

# Scheduler

def start_daily_email_scheduler():
    """
    Starts the background clock-checking loop when the app starts.
    This function starts the run_scheduler_loop() function
    """
    background_thread = threading.Thread(target=run_scheduler_loop, daemon=True)
    background_thread.start()


def run_scheduler_loop():
    """
    This function check the scheduled date and time of sending reminder email
    and check if email has been sent or not.
    """
    last_sent_date = None

    while True:
        now = datetime.now()
        today_text = now.strftime("%Y-%m-%d")

        target_hour = config.DAILY_EMAIL_HOUR
        target_minute = config.DAILY_EMAIL_MINUTE

        already_sent_today = (last_sent_date == today_text)

        if now.hour == target_hour and now.minute == target_minute and not already_sent_today:
            print("Scheduler: it is time, sending daily reminder emails now...")
            send_daily_reminder_emails()
            last_sent_date = today_text

        time.sleep(60)