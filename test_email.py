# test_email.py
# Sample email send to receiver to check connection
import email_manager

print("Sending a test email to: shounakbnagad@gmail.com")

success, message = email_manager.send_email(
    to_email="shounakbnagad@gmail.com",
    subject="Test Email - Medibank OSHC",
    body="Feature is working fine."
)
print(message)
if success:
    print("passed. Go check the inbox now.")
else:
    print("failed. Read the error message above to see why.")