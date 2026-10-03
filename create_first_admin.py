# create_first_admin.py
# Functionality:
# Only run at the very first time of Launching the project

import database

# make sure the database file and the "users" table exist.
database.create_database()

# add admin account.
admin_id = "admin1"
admin_email = "admin@medibank.com"
admin_password = "admin123"

success, message = database.add_user(
    user_id=admin_id,
    email=admin_email,
    plain_password=admin_password,
    policy_type="",
    role="admin"
)

# Print after adding a row in the Database Table.
if success:
    print("SUCCESS! Admin account created.")
    print("You can now log in with:")
    print("  User ID  :", admin_id)
    print("  Password :", admin_password)
else:
    print("Something went wrong:", message)
    print("This usually means an account with this User ID already exists.")