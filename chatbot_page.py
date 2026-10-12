# chatbot_page.py
# Functionality:
# Chatbot screen after logging in by Student
# Select Comprehensive or Essentials according to subscription
# The student types OR speaks questions (microphone button)
# llm_handler.py finds the answer in the documents
# The answer can be read by system ("Read answers by speaker" option)

import threading
import queue
import tkinter as tk

import config
import llm_handler
import voice_handler

# True = a spoken question is sent straight away.
# False = the spoken text is only put in the box, so the student can check it first.
VOICE_AUTO_SEND = getattr(config, "VOICE_AUTO_SEND", True)

class ChatbotPage(tk.Frame):

    def __init__(self, master, user_id, on_logout):
        super().__init__(master, bg="white")

        self.user_id = user_id
        self.on_logout = on_logout
        self.cover_type = None  # Cover type = comprehensive / essential. Initially blank
        self.chat_history = []  # Chat log
        self.recording = False  # True while the microphone is recording
        self.speak_answers = tk.BooleanVar(value=False)  # The "Read answers aloud" tick box. Initially off

        # The LLM can take many seconds. If we waited for it on the main
        # thread, the whole window would freeze. So we run it in a
        # background thread, and the thread drops its result into this
        # "mailbox". The window checks the mailbox every 100 ms.
        # Every item in the mailbox is a small dictionary with a "kind":
        #   "status"      -> text for the grey status label
        #   "answer"      -> the chatbot's answer to a question
        #   "voice_text"  -> the spoken question, turned into text
        #   "voice_error" -> a voice problem to show to the student
        self.mailbox = queue.Queue()

        self.build()
        self.ask_cover_type()
        self.check_mailbox()
        self.start_warm_up()

    def build(self):
        # 3 rows= top bar, chat area, bottom row
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Top bar
        top_bar = tk.Frame(self, bg="white", bd=1, relief="solid")
        top_bar.grid(row=0, column=0, sticky="ew")

        tk.Label(top_bar, text=config.APP_TITLE,
                 font=("Arial", 14, "bold"), bg="white").pack(
            side="left", padx=10, pady=8)

        tk.Button(top_bar, text="Logout",
                  font=("Arial", 10),
                  command=self.on_logout).pack(side="right", padx=10, pady=8)

        # Change Cover Type
        self.change_cover_button = tk.Button(top_bar, text="Change cover type",
                                             font=("Arial", 10),
                                             command=self.ask_cover_type)
        self.change_cover_button.pack(side="right", padx=(0, 6), pady=8)

        # Voice: stop button + tick box to read answers aloud
        tk.Button(top_bar, text="Stop voice",
                  font=("Arial", 10),
                  command=voice_handler.stop_speaking).pack(side="right", padx=(0, 6), pady=8)

        tk.Checkbutton(top_bar, text="Read answers aloud",
                       variable=self.speak_answers,
                       font=("Arial", 10), bg="white",
                       activebackground="white").pack(side="right", padx=(0, 6))

        # status text
        self.status_label = tk.Label(top_bar, text="", font=("Arial", 9),
                                     bg="white", fg="gray")
        self.status_label.pack(side="right", padx=10)

        # Chat area
        chat_area = tk.Frame(self, bg="white")
        chat_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        chat_area.rowconfigure(0, weight=1)
        chat_area.columnconfigure(0, weight=1)

        self.chat_text = tk.Text(chat_area, wrap="word", font=("Arial", 11),
                                 bg="white", relief="solid", bd=1,
                                 padx=10, pady=10, state="disabled")
        self.chat_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(chat_area, orient="vertical",
                                 command=self.chat_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_text.configure(yscrollcommand=scrollbar.set)

        # Text styles. different look for user and chatbot
        self.chat_text.tag_configure("you_name", font=("Arial", 10, "bold"),
                                     foreground="#1a5fb4")
        self.chat_text.tag_configure("bot_name", font=("Arial", 10, "bold"),
                                     foreground="#26a269")
        self.chat_text.tag_configure("note", foreground="gray",
                                     font=("Arial", 10, "italic"))

        # Bottom row

        # Select Cover
        self.choice_row = tk.Frame(self, bg="white")
        self.choice_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        # 2 buttons for 2 cover types
        for cover_key, cover_label in config.COVER_TYPES.items():
            # "lambda key=cover_key" remembers WHICH button was clicked.
            tk.Button(self.choice_row, text=cover_label,
                      font=("Arial", 12), width=24, pady=6,
                      command=lambda key=cover_key: self.choose_cover(key)).pack(
                side="left", padx=(0, 10))

        # user input row:  [ question box ] [ Speak ] [ Send ]
        self.input_row = tk.Frame(self, bg="white")
        self.input_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.input_row.columnconfigure(0, weight=1)

        self.question_entry = tk.Entry(self.input_row, font=("Arial", 12))
        self.question_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=4)
        # Pressing Enter does the same as clicking Send.
        self.question_entry.bind("<Return>", lambda event: self.handle_send())

        # Click once to start speaking, click again to stop and send.
        self.mic_button = tk.Button(self.input_row, text="Speak",
                                    font=("Arial", 11), width=14,
                                    command=self.toggle_recording)
        self.mic_button.grid(row=0, column=1, padx=(0, 8))

        self.send_button = tk.Button(self.input_row, text="Send",
                                     font=("Arial", 11), width=10,
                                     command=self.handle_send)
        self.send_button.grid(row=0, column=2)

        # Show messages

    def add_message(self, who, text):
        """
        Adds one message to the chat area. who = "You" or "Bot".
        """
        name_tag = "you_name" if who == "You" else "bot_name"

        # The Text box is locked (disabled) so the student cannot type in
        # it. We must unlock it for a moment to add text, then lock again.
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, who + "\n", name_tag)
        self.chat_text.insert(tk.END, text + "\n\n")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)  # scroll to the newest message

    def add_note(self, text):
        # A small grey note in the chat (used for voice problems)
        self.chat_text.configure(state="normal")
        self.chat_text.insert(tk.END, text + "\n\n", "note")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)

    def start_thinking_note(self):
        # Show "Thinking..."
        self.chat_text.configure(state="normal")
        self.thinking_start = self.chat_text.index("end-1c")
        self.chat_text.insert(tk.END, "Thinking...\n\n", "note")
        self.chat_text.configure(state="disabled")
        self.chat_text.see(tk.END)

    def remove_thinking_note(self):
        self.chat_text.configure(state="normal")
        self.chat_text.delete(self.thinking_start, tk.END)
        self.chat_text.configure(state="disabled")

        # Lock / unlock the buttons

    def lock_buttons(self):
        # While the bot is busy, the student cannot send, speak or change cover.
        self.send_button.configure(state="disabled")
        self.mic_button.configure(state="disabled")
        self.change_cover_button.configure(state="disabled")

    def unlock_buttons(self):
        self.send_button.configure(state="normal")
        self.mic_button.configure(state="normal", text="Speak")
        self.change_cover_button.configure(state="normal")

        # Choose cover type

    def ask_cover_type(self):
        """
        Asks the student which type of OSHC they have
        shows two buttons
        Runs when the page opens, and again if the student clicks "Change cover type".
        """
        voice_handler.stop_speaking()

        self.cover_type = None
        # A new cover type = a new conversation
        self.chat_history = []

        self.add_message("Bot",
                         "Hello! Which type of Medibank OSHC cover do you have? "
                         "Please choose one below, so I can give you the right answers.")

        # Show the buttons, hide the question box.
        self.input_row.grid_remove()
        self.choice_row.grid()

    def choose_cover(self, cover_key):
        """
        Runs when the student clicks one of the two cover-type buttons.
        """
        self.cover_type = cover_key
        cover_label = config.COVER_TYPES[cover_key]

        self.add_message("You", cover_label)
        self.add_message("Bot",
                         "Thank you! I will answer using " + cover_label +
                         " information. What would you like to know? "
                         "For example: waiting periods, what is covered, or how "
                         "to make a claim. You can type, or click Speak and talk.")

        # Hide the buttons, show the question box.
        self.choice_row.grid_remove()
        self.input_row.grid()
        self.question_entry.focus_set()

        # Voice input - mic

    def toggle_recording(self):
        """
        Runs when the student clicks the Speak / Stop button.
        1st click = start recording. 2nd click = stop, and turn the voice into text.
        """
        if self.cover_type is None:
            return

        if not self.recording:
            # start recording
            if str(self.send_button["state"]) == "disabled":
                return  # the bot is busy

            voice_handler.stop_speaking()  # do not record the bot's own voice
            try:
                voice_handler.start_recording()
            except voice_handler.VoiceError as error:
                self.add_note(str(error))
                return

            self.recording = True
            self.mic_button.configure(text="Stop recording")
            self.send_button.configure(state="disabled")
            self.change_cover_button.configure(state="disabled")
            self.status_label.configure(text="Listening... click 'Stop recording' when you finish")
        else:
            # stop recording
            self.recording = False
            sound = voice_handler.stop_recording()
            self.lock_buttons()
            self.mic_button.configure(text="Working...")
            self.status_label.configure(
                text="Turning your voice into text... (the first time takes longer)")

            worker = threading.Thread(target=self.transcribe_in_background,
                                      args=(sound,), daemon=True)
            worker.start()

    def transcribe_in_background(self, sound):
        """
        Runs in the background thread (Whisper can take a few seconds).
        """
        try:
            text = voice_handler.transcribe(sound)
            self.mailbox.put({"kind": "voice_text", "text": text})
        except voice_handler.VoiceError as error:
            self.mailbox.put({"kind": "voice_error", "text": str(error)})
        except Exception as error:
            self.mailbox.put({"kind": "voice_error",
                              "text": "Sorry, the voice could not be understood: " + str(error)})

        # Sending question

    def handle_send(self):
        question = self.question_entry.get().strip()
        if question == "":
            return

        # Do not allow questions before the cover type is chosen
        if self.cover_type is None:
            return

        # Do not allow a second question while the first one is running
        if str(self.send_button["state"]) == "disabled":
            return

        voice_handler.stop_speaking()  # stop reading the previous answer

        self.question_entry.delete(0, tk.END)
        self.add_message("You", question)
        self.start_thinking_note()

        # While the bot is thinking, lock the buttons
        self.lock_buttons()

        # Copy the history so the thread has its own safe copy
        history_copy = list(self.chat_history)

        worker = threading.Thread(
            target=self.run_in_background,
            args=(question, self.cover_type, history_copy),
            daemon=True)
        worker.start()

    def run_in_background(self, question, cover_type, history_copy):
        """
        Runs in the background thread. It must NOT touch any window
        widget directly (Tkinter is not safe for that). It only puts
        the finished answer into the mailbox.
        """
        answer = llm_handler.generate_response(question, cover_type, history_copy)
        # The language of the answer, so the right voice can read it.
        language = llm_handler.last_language
        self.mailbox.put({"kind": "answer", "question": question,
                          "answer": answer, "language": language})

        # Read the answer aloud

    def read_aloud_in_background(self, answer, language):
        """
        Runs in the background thread: speaks until the answer is finished.
        """
        problem = voice_handler.speak(answer, language)
        if problem != "":
            self.mailbox.put({"kind": "status", "text": problem})

    def check_mailbox(self):
        """
        Runs on the main thread every 100 ms, and checks if something has arrived.
        """
        try:
            message = self.mailbox.get_nowait()
            kind = message["kind"]

            if kind == "status":
                # A status update
                self.status_label.configure(text=message["text"])

            elif kind == "answer":
                self.remove_thinking_note()
                self.add_message("Bot", message["answer"])

                # Remember this exchange for follow-up questions.
                self.chat_history.append({"role": "user", "content": message["question"]})
                self.chat_history.append({"role": "assistant", "content": message["answer"]})

                self.unlock_buttons()
                self.status_label.configure(text="")
                self.question_entry.focus_set()

                if self.speak_answers.get():
                    worker = threading.Thread(
                        target=self.read_aloud_in_background,
                        args=(message["answer"], message["language"]),
                        daemon=True)
                    worker.start()

            elif kind == "voice_text":
                # The spoken question, now as text.
                self.unlock_buttons()
                self.status_label.configure(text="")
                self.question_entry.delete(0, tk.END)
                self.question_entry.insert(0, message["text"])
                if VOICE_AUTO_SEND:
                    self.handle_send()
                else:
                    self.question_entry.focus_set()

            elif kind == "voice_error":
                self.unlock_buttons()
                self.status_label.configure(text="")
                self.add_note(message["text"])

        except queue.Empty:
            pass

        # Check again in 100 ms. If the student logged out, this page
        # no longer exists and stop checking.
        if self.winfo_exists():
            self.after(100, self.check_mailbox)

        # Loading the knowledge base in the background

    def start_warm_up(self):
        self.status_label.configure(text="Loading knowledge base...")
        worker = threading.Thread(target=self.warm_up_in_background, daemon=True)
        worker.start()

    def warm_up_in_background(self):
        try:
            llm_handler.warm_up()
            self.mailbox.put({"kind": "status", "text": "Knowledge base ready"})
        except Exception as error:
            self.mailbox.put({"kind": "status",
                              "text": "Knowledge base problem: " + str(error)})

        # Closing the page

    def destroy(self):
        # Logout: stop the microphone and the voice.
        voice_handler.stop_speaking()
        if self.recording:
            voice_handler.stop_recording()
        super().destroy()

