# admin_panel.py
# Admin user login
# bulk email
# Dashboard
# user registration

import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import database

class AdminPanel(tk.Frame):

    def __init__(self, master, on_logout):
        super().__init__(master, bg="white")


        # call when the admin clicks "Logout".
        self.on_logout = on_logout

        self.build()

        # refresh the page with updated data
        self.refresh_dashboard()
        self.refresh_student_list()

    def build(self):
        # This Frame (self) has exactly two rows:
        #   row 0 -> the top bar (fixed at the top, never scrolls)
        #   row 1 -> everything else (scrollable)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Top bar
        top_bar = tk.Frame(self, bg="white", bd=1, relief="solid")
        top_bar.grid(row=0, column=0, sticky="ew")

        tk.Label(top_bar, text="Medibank AI-Chatbot - Admin Panel",
                 font=("Arial", 14, "bold"), bg="white").pack(
            side="left", padx=10, pady=8)

        tk.Button(top_bar, text="Logout",
                  font=("Arial", 10),
                  command=self.on_logout).pack(side="right", padx=10, pady=8)

        # ---------- Scrollable area ----------
        # A Canvas is the only widget in Tkinter that can scroll, so we
        # put a Canvas here, and a Scrollbar next to it. Then all three
        # sections below (Bulk Email, Dashboard, Add New User) go
        # inside a plain Frame called "body", and "body" sits inside
        # the Canvas.
        scroll_area = tk.Frame(self, bg="white")
        scroll_area.grid(row=1, column=0, sticky="nsew")
        scroll_area.rowconfigure(0, weight=1)
        scroll_area.columnconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_area, bg="white", highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(scroll_area, orient="vertical",
                                  command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")

        canvas.configure(yscrollcommand=scrollbar.set)

        body = tk.Frame(canvas, bg="white")
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def on_body_resize(event):
            # Tells the canvas how tall the scrollable area really is,
            # every time the content inside it changes size.
            canvas.configure(scrollregion=canvas.bbox("all"))
        body.bind("<Configure>", on_body_resize)

        def on_canvas_resize(event):
            # Makes the body frame always match the canvas width, so
            # the sections stretch to fill the window instead of
            # staying a fixed narrow width.
            canvas.itemconfig(body_id, width=event.width)
        canvas.bind("<Configure>", on_canvas_resize)

        def on_mousewheel(event):
            # Lets the mouse scroll wheel work over the canvas.
            # event.delta is 120 (or a multiple of it) on Windows and
            # Mac, so dividing by 120 gives a small, steady scroll
            # step on both.
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # We only turn on scrolling with the mouse wheel while the
        # mouse is actually over this screen, so it does not interfere
        # with any other window.
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # Bulk Email
        email_box = tk.LabelFrame(body, text="Bulk Email",
                                   font=("Arial", 11, "bold"),
                                   bg="white", padx=10, pady=10)
        email_box.pack(fill="x", padx=10, pady=10)

        # Inbox and Send Item buttons
        button_row = tk.Frame(email_box, bg="white")
        button_row.pack(fill="x", pady=(0, 8))

        tk.Button(button_row, text="Inbox",
                  command=self.show_not_ready).pack(side="left", padx=(0, 6))
        tk.Button(button_row, text="Send Item",
                  command=self.show_not_ready).pack(side="left")

        # From field
        from_row = tk.Frame(email_box, bg="white")
        from_row.pack(fill="x", pady=4)
        tk.Label(from_row, text="From:", font=("Arial", 10),
                 bg="white", width=8, anchor="w").pack(side="left")
        from_entry = tk.Entry(from_row, font=("Arial", 10))
        from_entry.insert(0, "cos70008@gmail.com")
        from_entry.configure(state="disabled")  # locked, cannot be edited
        from_entry.pack(side="left", fill="x", expand=True)

        # To field
        to_row = tk.Frame(email_box, bg="white")
        to_row.pack(fill="x", pady=4)
        tk.Label(to_row, text="To:", font=("Arial", 10),
                 bg="white", width=8, anchor="nw").pack(side="left")

        to_list_frame = tk.Frame(to_row, bg="white")
        to_list_frame.pack(side="left", fill="x", expand=True)

        # selectmode="multiple" in To field
        self.student_listbox = tk.Listbox(to_list_frame, height=4,
                                           selectmode="multiple",
                                           font=("Arial", 10))
        self.student_listbox.pack(side="left", fill="x", expand=True)

        tk.Button(to_list_frame, text="Select All",
                  command=self.select_all_students).pack(side="left", padx=(6, 0))

        # Subject field
        subject_row = tk.Frame(email_box, bg="white")
        subject_row.pack(fill="x", pady=4)
        tk.Label(subject_row, text="Subject:", font=("Arial", 10),
                 bg="white", width=8, anchor="w").pack(side="left")
        self.subject_entry = tk.Entry(subject_row, font=("Arial", 10))
        self.subject_entry.pack(side="left", fill="x", expand=True)

        # Body field
        body_row = tk.Frame(email_box, bg="white")
        body_row.pack(fill="x", pady=4)
        tk.Label(body_row, text="Body:", font=("Arial", 10),
                 bg="white", width=8, anchor="nw").pack(side="left")
        self.body_text = tk.Text(body_row, height=4, font=("Arial", 10))
        self.body_text.pack(side="left", fill="x", expand=True)

        # Send button
        tk.Button(email_box, text="Send",
                  font=("Arial", 10),
                  command=self.show_not_ready).pack(anchor="e", pady=(8, 0))

        # Dashboard
        dashboard_box = tk.LabelFrame(body, text="Dashboard",
                                       font=("Arial", 11, "bold"),
                                       bg="white", padx=10, pady=10)
        dashboard_box.pack(fill="x", padx=10, pady=10)

        self.registered_label = self.make_dashboard_row(
            dashboard_box, "Registered User:", 0)
        self.active_label = self.make_dashboard_row(
            dashboard_box, "Active User in 24 Hours:", 1)
        self.never_used_label = self.make_dashboard_row(
            dashboard_box, "User Never Used:", 2)

        tk.Button(dashboard_box, text="Refresh",
                  command=self.refresh_dashboard).grid(
            row=3, column=0, columnspan=2, pady=(10, 0))

        # Add New User
        add_user_box = tk.LabelFrame(body, text="Add New User",
                                      font=("Arial", 11, "bold"),
                                      bg="white", padx=10, pady=10)
        add_user_box.pack(fill="x", padx=10, pady=10)

        # User ID and Email - side by side
        tk.Label(add_user_box, text="User ID", font=("Arial", 10),
                 bg="white").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.new_user_id_entry = tk.Entry(add_user_box, font=("Arial", 10))
        self.new_user_id_entry.grid(row=0, column=1, padx=6, pady=6)

        tk.Label(add_user_box, text="Email", font=("Arial", 10),
                 bg="white").grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.new_email_entry = tk.Entry(add_user_box, font=("Arial", 10))
        self.new_email_entry.grid(row=0, column=3, padx=6, pady=6)

        # Policy Type Radio button and Password - side by side
        tk.Label(add_user_box, text="Policy Type", font=("Arial", 10),
                 bg="white").grid(row=1, column=0, padx=6, pady=6, sticky="e")

        self.policy_type_var = tk.StringVar(value="student")
        policy_frame = tk.Frame(add_user_box, bg="white")
        policy_frame.grid(row=1, column=1, sticky="w")
        tk.Radiobutton(policy_frame, text="Student", variable=self.policy_type_var,
                        value="student", bg="white").pack(side="left")
        tk.Radiobutton(policy_frame, text="Regular User", variable=self.policy_type_var,
                        value="regular_user", bg="white").pack(side="left")

        tk.Label(add_user_box, text="Password", font=("Arial", 10),
                 bg="white").grid(row=1, column=2, padx=6, pady=6, sticky="e")
        self.new_password_entry = tk.Entry(add_user_box, font=("Arial", 10),
                                            show="*")
        self.new_password_entry.grid(row=1, column=3, padx=6, pady=6)

        # Role - radio button
        tk.Label(add_user_box, text="Role", font=("Arial", 10),
                 bg="white").grid(row=2, column=0, padx=6, pady=6, sticky="e")

        self.role_var = tk.StringVar(value="student")
        role_frame = tk.Frame(add_user_box, bg="white")
        role_frame.grid(row=2, column=1, columnspan=3, sticky="w")
        tk.Radiobutton(role_frame, text="Student", variable=self.role_var,
                        value="student", bg="white").pack(side="left")
        tk.Radiobutton(role_frame, text="Regular User", variable=self.role_var,
                        value="regular_user", bg="white").pack(side="left")
        tk.Radiobutton(role_frame, text="Admin", variable=self.role_var,
                        value="admin", bg="white").pack(side="left")

        # Add User button
        tk.Button(add_user_box, text="Add User",
                  font=("Arial", 10),
                  command=self.handle_add_user).grid(
            row=3, column=0, columnspan=4, pady=(10, 0))

    def make_dashboard_row(self, parent, label_text, row_number):
        """
        This is a small helper function so we do not repeat the same
        code three times for the three dashboard numbers.
        It creates a label on the left and a number box on the right,
        and returns the number box so we can update it later.
        """
        tk.Label(parent, text=label_text, font=("Arial", 11),
                 bg="white").grid(row=row_number, column=0, padx=6, pady=6, sticky="e")

        value_label = tk.Label(parent, text="0", font=("Arial", 11, "bold"),
                                bg="white", relief="solid", bd=1, width=8)
        value_label.grid(row=row_number, column=1, padx=6, pady=6, sticky="w")

        return value_label

    def refresh_dashboard(self):
            """
            Asks the database for the latest three numbers and updates
            the labels on screen.
            """
            total_registered, active_today, never_used = database.get_dashboard_counts()

            self.registered_label.configure(text=str(total_registered))
            self.active_label.configure(text=str(active_today))
            self.never_used_label.configure(text=str(never_used))

        # NEW: Load students from database into the email recipient list
        # NEW: Load students from database into the email recipient list

    def refresh_student_list(self):
        """
        Clears and refills the "To" list box with every student
        currently in the database.
        """
        self.student_listbox.delete(0, tk.END)

        students = database.get_all_students()

        for user_id, email in students:
            self.student_listbox.insert(tk.END, f"{user_id} - {email}")

    def select_all_students(self):
        # This selects every single row in the list box at once.
        self.student_listbox.select_set(0, tk.END)

    def handle_add_user(self):
        # Read everything the admin typed into the Add New User form.
        user_id = self.new_user_id_entry.get().strip()
        email = self.new_email_entry.get().strip()
        password = self.new_password_entry.get().strip()
        policy_type = self.policy_type_var.get()
        role = self.role_var.get()

        # Simple check - do not allow empty fields.
        if user_id == "" or email == "" or password == "":
            messagebox.showwarning("Missing Information",
                                    "Please fill in User ID, Email, and Password.")
            return

        messagebox.showinfo("Success", f"User '{user_id}' was added successfully.")


        # success, message = database.add_user(user_id, email, password,
        #                                       policy_type, role)

        # if success:
        #   messagebox.showinfo("Success", message)
        success, message = database.add_user(user_id, email, password,
                                             policy_type, role)

        # Clear the form so it is ready for the next new user.
        self.new_user_id_entry.delete(0, tk.END)
        self.new_email_entry.delete(0, tk.END)
        self.new_password_entry.delete(0, tk.END)

            # Update the dashboard numbers and the email list,
            # since we just added a new row to the database.
        self.refresh_dashboard()
        self.refresh_student_list()
        # else:
        messagebox.showerror("Could Not Add User", message)

    def show_not_ready(self):
        # A shared message for every button we have not built yet
        # (Send, Inbox, Send Item, Refresh).
        messagebox.showinfo("Coming Soon",
                             "This feature will be added in a later step.")


# Test Run
if __name__ == "__main__":
    database.create_database()

    def logout():
        print("Logout button was pressed.")

    root = tk.Tk()
    root.title("Medibank AI-Chatbot - Admin Panel")
    root.geometry("950x800")
    root.minsize(700, 500)   # stops the screen shrinking so small that
                             # nothing fits, even with the scrollbar
    root.configure(bg="white")

    admin_page = AdminPanel(root, on_logout=logout)
    admin_page.pack(fill="both", expand=True)

    root.mainloop()