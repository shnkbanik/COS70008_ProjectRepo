# login_page.py
# Functionality:
# Develop the UI of login page
# Clicking on Sign in- system checks the validity of credential
# Successful login will pass the signal to main.py to redirect into respective screen based on ROLE

import tkinter as tk
from tkinter import messagebox
import auth_manager


class LoginPage(tk.Frame):

    def __init__(self, master, on_login_success):
        super().__init__(master, bg="white")

        # on_login_success is a function of main.py.
        # After successful login, and pass user_id and role to main.py to redirect in next screen
        self.on_login_success = on_login_success

        self.build()

    def build(self):
        # content fill in the middle of the whole window
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        center = tk.Frame(self, bg="white")
        center.grid(row=0, column=0)

        # Title
        tk.Label(center, text="Medibank AI-Chatbot - Login Page",
                 font=("Arial", 20, "bold"),
                 bg="white", fg="black").grid(
            row=0, column=0, columnspan=2, pady=(40, 30))

        # User ID field
        tk.Label(center, text="ID:",
                 font=("Arial", 12), bg="white", fg="black").grid(
            row=1, column=0, padx=10, pady=10, sticky="e")

        self.id_entry = tk.Entry(center, font=("Arial", 12), width=25)
        self.id_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # Password field
        tk.Label(center, text="Password:",
                 font=("Arial", 12), bg="white", fg="black").grid(
            row=2, column=0, padx=10, pady=10, sticky="e")

        self.password_entry = tk.Entry(center, font=("Arial", 12),
                                        width=25, show="*")
        self.password_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        # Sign In button
        tk.Button(center, text="Sign In",
                  font=("Arial", 12),
                  width=15,
                  command=self.handle_sign_in).grid(
            row=3, column=0, columnspan=2, pady=30)

        # Pressing Enter in the password box also triggers Sign In.
        # self.password_entry.bind("<Return>", lambda event: self.handle_sign_in())

    def handle_sign_in(self):
        # Read the credential.
        user_id = self.id_entry.get().strip()
        password = self.password_entry.get().strip()

        # pass the entered data to auth_manager.login function.
        success, role, message = auth_manager.login(user_id, password)

        if success:
            # Login worked. Pass the USER ROLE to main.py to open the correct screen.
            self.on_login_success(user_id, role)
        else:
            # Login failed. Show the error message
            messagebox.showerror("Login Failed", message)


# Test the code
# Dummy User
# Student -> ID: 123456   Password: student123
# Admin   -> ID: 654321   Password: admin123
# Any other ID/password will correctly show "Login Failed".

if __name__ == "__main__":

    # Dummy ID PASS

    print("Dummy ID PASS")
    print("  Student -> ID: 123456   Password: student123")
    print("  Admin   -> ID: 654321   Password: admin123")

    # Login
    def on_login_success(user_id, role):
        print("Sign In was successful.")
        print("  user_id:", user_id)
        print("  role   :", role)

    # plain window to set the login screen.
    root = tk.Tk()
    root.title( "Medibank AI-Chatbot - Login Page")
    root.geometry(f"950x800")
    root.configure(bg="white")

    login_page = LoginPage(root, on_login_success=on_login_success)
    login_page.pack(fill="both", expand=True)

    # Keep the screen open
    root.mainloop()
