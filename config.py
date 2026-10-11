# config.py
# Functionality:
# Common variables and data using in the project.
# Application Title, DB file name, Sender email, password, smtp server
# smtp port, daily email time, test email address
# common config of RAG and LLM
APP_TITLE = "Medibank AI-Chatbot"

# Database Settings
# Name of SQLite database file.
# SQLite stores data of Student and Admin in a file in local PC.
DB_FILE_NAME = "medibank.db"

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

# Chatbot (RAG + LLM) Settings
# Folder that holds the Medibank OSHC documents
KNOWLEDGE_BASE_FOLDER = "knowledge_base"

# Folder where the searchable index is saved, so we only build it once
INDEX_FOLDER = "rag_index"

# The model that turns text into numbers (embeddings) for searching
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
# EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Count of the best-matching chunks we give to the LLM for each question.
TOP_K = 4

# A chunk must score at least this (0 to 1) to count as "relevant".
# If nothing reaches it, the bot says it could not find the answer.
# Raise it if the bot answers off-topic questions, lower it if the
# bot refuses questions that ARE in the documents.
MIN_RELEVANCE_SCORE = 0.25

# The LLM runs locally through Ollama (free app: https://ollama.com).
# One-time setup on each computer:  ollama pull llama3.1:8b
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.1:8b"
# Seconds to wait for the model to answer
OLLAMA_TIMEOUT_SECONDS = 300

COVER_TYPES = {
    "comprehensive": "Comprehensive OSHC",
    "essential": "Essentials OSHC",
}
LEXICAL_WEIGHT = 0.15
MAX_PER_PAGE = 1
SHOW_CHUNKS = True
WHISPER_MODEL_SIZE = "small"   # "base" is faster, "medium" more accurate
VOICE_AUTO_SEND = True         # False = put the spoken text in the box so user can check it first