# chatbot_page.py
# Functionality:
# Chatbot screen after logging in by Student

# Currently, UNDER DEVELOPMENT

import tkinter as tk
import config


class ChatbotPage(tk.Frame):

    def __init__(self, master, user_id, on_logout):
        super().__init__(master, bg="white")

        self.user_id = user_id
        self.on_logout = on_logout

        self.build()

    def build(self):
        # Top bar
        top_bar = tk.Frame(self, bg="white", bd=1, relief="solid")
        top_bar.pack(fill="x")

        tk.Label(top_bar, text=config.APP_TITLE,
                 font=("Arial", 14, "bold"), bg="white").pack(
            side="left", padx=10, pady=8)

        tk.Button(top_bar, text="Logout",
                  font=("Arial", 10),
                  command=self.on_logout).pack(side="right", padx=10, pady=8)

        # Under Construction Message
        center = tk.Frame(self, bg="white")
        center.pack(expand=True)

        # tk.Label(center, text=f"Welcome, {self.user_id}",
        #        font=("Arial", 14), bg="white").pack(pady=(60, 10))

        tk.Label(center, text="The chatbot will develop on next week",
                 font=("Arial", 11, "italic"), bg="white", fg="gray").pack()

