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
