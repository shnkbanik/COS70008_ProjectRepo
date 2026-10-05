import smtplib
import ssl
import threading
import time
from datetime import datetime
from email.mime.text import MIMEText

import certifi

import config
import database


def send_email(to_email, subject, body):
    """Send one email. Returns (success, message)."""
    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = config.SENDER_EMAIL
    message["To"] = to_email

    try:
        context = ssl.create_default_context(cafile=certifi.where())
        server = smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT,
                                  context=context, timeout=15)  # give up after 15 seconds
        server.login(config.SENDER_EMAIL, config.SENDER_APP_PASSWORD)
        server.send_message(message)
        server.quit()
        return True, "Email sent to " + to_email

    except Exception as error:
        return False, "Could not send email to " + to_email + ". Reason: " + str(error)


def send_bulk_email(email_list, subject, body):
    """Send the same email to a list of addresses. Returns (sent, failed)."""
    success_count = 0
    fail_count = 0

    for email_address in email_list:
        success, message = send_email(email_address, subject, body)
        print(message)
        if success:
            success_count += 1
        else:
            fail_count += 1

    return success_count, fail_count


def send_welcome_email(student_email):
    """Welcome email sent when the admin adds a new student."""
    subject = "Welcome to Medibank OSHC"
    body = (
        "Hello,\n\n"
        "Your Medibank OSHC account has been created.\n"
        "We now offer an AI chatbot that gives specific answers to your "
        "questions. Log in and ask anything about your OSHC policy.\n\n"
        "Thank you,\n"
        "Medibank"
    )
    return send_email(student_email, subject, body)


def send_startup_email_to_all_students():
    """Update email to every student. Only runs if SEND_ON_STARTUP is True in config."""
    students = database.get_all_students()

    # each item is (user_id, email), we only need the email
    email_list = []
    for user_id, email in students:
        email_list.append(email)

    subject = "Medibank OSHC - New Update Available"
    body = (
        "Hello,\n\n"
        "There is a new update in the Medibank OSHC app. "
        "We now offer an AI chatbot that gives specific answers to your "
        "questions. Please log in and try it out.\n\n"
        "Thank you,\n"
        "Medibank"
    )
    sent, failed = send_bulk_email(email_list, subject, body)
    print("Startup email finished. Sent:", sent, "Failed:", failed)


def send_daily_reminder_emails():
    """Reminder for students who have not logged in. Called by the scheduler."""
    email_list = database.get_students_not_logged_in()

    subject = "Don't forget - Medibank AI-Chatbot is here to help"
    body = (
        "Hello,\n\n"
        "We now offer an AI chatbot that gives specific answers to your "
        "questions. Please log in and try it out.\n\n"
        "Thank you,\n"
        "Medibank"
    )
    sent, failed = send_bulk_email(email_list, subject, body)
    print("Daily reminder finished. Sent:", sent, "Failed:", failed)


# Scheduler

def start_daily_email_scheduler():
    """Start the reminder scheduler in a background thread."""
    thread = threading.Thread(target=run_scheduler_loop, daemon=True)
    thread.start()


def run_scheduler_loop():
    """Check the clock every minute and send the daily reminder once at the set time."""
    last_sent_date = None

    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        time_matches = (now.hour == config.DAILY_EMAIL_HOUR
                        and now.minute == config.DAILY_EMAIL_MINUTE)

        if time_matches and last_sent_date != today:
            print("Scheduler: sending daily reminder emails now...")
            send_daily_reminder_emails()
            last_sent_date = today

        time.sleep(60)