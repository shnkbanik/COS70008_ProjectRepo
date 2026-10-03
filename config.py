# config.py
# Functionality:
# Common variables and data using in the project.
# Application Title, DB file name, Sender email, password, smtp server
# smtp port, daily email time, test email address
APP_TITLE = "Medibank AI-Chatbot"

# Database Settings
# Name of SQLite database file.
# SQLite stores data of Student and Admin in a file in local PC.
DB_FILE_NAME = "medibank_users.db"

# Email Settings (used later by smtplib to send emails)
# Sender (Admin) Email address for sending notification
SENDER_EMAIL = "cos70008@gmail.com"
# Sender email address password
SENDER_APP_PASSWORD = "zgmr xmwl ndcn bhsh"

# Gmail outgoing mail server details.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# Automatic Email Settings on each Deployment / RUN
# True = system will send email to all students when run (start) the application.
# False = system will not send email to all students when run (start) the application.
SEND_ON_STARTUP = False

# Scheduled Email Settings
# 24-HOUR format (0 to 23 for the hour).
# Example: HOUR = 21, MINUTE = 30 means the check happens at 9:30 PM.
DAILY_EMAIL_HOUR = 21
DAILY_EMAIL_MINUTE = 0