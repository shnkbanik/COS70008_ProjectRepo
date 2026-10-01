# auth_manager.py
# Functionality:
# Login condition
# Write the last login time in Database after successful login

import database

Dummy_user = {
    "123456": {"password": "student123", "role": "student"},
    "654321": {"password": "admin123", "role": "admin"},
}

def login(user_id, plain_password):
    """
    log a user in.

    It returns THREE things:
    1. success -> True or False
    2. role    -> "student" or "admin" (if success is True)
    3. message -> error message on login fail
    """

    # Checking whether the fields are empty or not
    if user_id == "" or plain_password == "":
        return False, None, "Please enter both User ID and Password."

    is_valid, role = database.verify_login(user_id, plain_password)

    if is_valid:
        # Login worked - save the last login time in the database.
        database.update_last_login(user_id)

        return True, role, "Login successful."
    else:
        return False, None, "Incorrect User ID or Password."

