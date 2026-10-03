# main.py
# Run the project from this file
# Functionality:
# Create the database if it does not exist
# Show the Login screen
# Switch to the correct next screen, based on the role (student / admin)

import tkinter as tk

import config
import database
import email_manager
from login_page import LoginPage
from admin_panel import AdminPanel
from chatbot_page import ChatbotPage


class App(tk.Tk):

    def __init__(self):
        super().__init__()

        # Create a database if it is not exist.
        database.create_database()

        # If SEND_ON_STARTUP is True in config.py, email every student
        if config.SEND_ON_STARTUP:
            email_manager.send_startup_email_to_all_students()

        # Turn on the scheduler
        email_manager.start_daily_email_scheduler()

        self.title(config.APP_TITLE)
        self.configure(bg="white")

        # Define window size
        self.geometry("950x800")
        self.minsize(700, 600)

        # content fill in the middle of the whole window
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.current_frame = None
        self.show_login()

    def switch_to(self, frame):
        # This removes whatever screen is currently showing,
        # and puts the new one in its place.
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame
        frame.grid(row=0, column=0, sticky="nsew")

    # ---------- Screens ----------

    def show_login(self):
        self.title(config.APP_TITLE)
        page = LoginPage(
            master=self,
            on_login_success=self.handle_login_success,
        )
        self.switch_to(page)

    def handle_login_success(self, user_id, role):
        # If credential is correct and role = admin then display admin panel
        if role == "admin":
            self.show_admin_panel()
        else:
            # If credential is correct and role = student then display chatbot panel
            self.show_chatbot(user_id)

    def show_admin_panel(self):
        self.title(config.APP_TITLE + " - Admin Panel")
        page = AdminPanel(
            master=self,
            on_logout=self.show_login,
        )
        self.switch_to(page)

    def show_chatbot(self, user_id):
        self.title(config.APP_TITLE + " - Chatbot")
        page = ChatbotPage(
            master=self,
            user_id=user_id,
            on_logout=self.show_login,
        )
        self.switch_to(page)


if __name__ == "__main__":
    app = App()
    app.mainloop()