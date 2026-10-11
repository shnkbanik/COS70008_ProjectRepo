import json
import urllib.request
import urllib.error

import config
import rag_pipeline

# Answered directly, since "hi" would never match a document.
GREETINGS = ("hi", "hello", "hey", "hi there", "hello there", "good morning",
             "good afternoon", "good evening")
THANKS = ("thanks", "thank you", "thx", "ok thanks", "thanks a lot")


# Language of the last answer. chatbot_page.py uses it to pick the voice.
last_language = "English"


def get_cover_label(cover_type):
    """Turns "comprehensive" into the display name "Comprehensive OSHC"."""
    return config.COVER_TYPES.get(cover_type, "Medibank OSHC")


def build_system_prompt(cover_type, language="English"):
    """The rules given to the LLM before every question."""
    cover_label = get_cover_label(cover_type)

    return (
        "You are the Medibank OSHC (Overseas Student Health Cover) assistant "
        "for international students in Australia.\n"
        f"The student you are talking to has {cover_label}.\n"
        "Rules:\n"
        "1. Answer ONLY using the INFORMATION given in the user's message. "
        "Never use outside knowledge about Medibank, prices, or rules.\n"
        f"2. The information may mention other types of cover. Only use what "
        f"applies to {cover_label}. If it is not clear that something applies "
        f"to {cover_label}, do not say that it does.\n"
        "3. If the information does not contain the answer, say you do not "
        "have that information and suggest contacting Medibank. Do not guess.\n"
        "4. Write ONE short, clear answer. Do not repeat yourself and do not "
        "give the same point twice.\n"
        "5. NEVER mention where the answer came from. Do not write file names, "
        "page numbers, brochure or guide names, numbers like [1], or the words "
        "'source', 'excerpt', 'information provided' or 'document'. Just state "
        "the answer as if you know the policy.\n"
        f"6. Write your WHOLE answer in {language}, even if the INFORMATION is "
        "written in another language. Use short, simple sentences. Use short "
        "bullet points when listing things.\n"
        "7. You are not a doctor. Do not give medical advice or diagnoses. "
        "For an emergency, tell the student to call 000.\n"
        "8. You give general information about the cover, not personal advice. "
        "Do not tell the student which cover to buy or whether it is right for "
        "them. For questions about their own account or claim, suggest "
        "contacting Medibank."
    )


def is_short_follow_up(question):
    """True for real follow-ups ("and for my partner?"), not for new questions."""
    words = question.lower().strip("!.? ").split()
    if len(words) <= 2:
        return True
    starters = ("and", "also", "what about", "how about", "what if", "y", "y para")
    text = " ".join(words)
    return any(text.startswith(start + " ") for start in starters) and len(words) <= 7


def detect_language(text):
    """Asks the LLM which language the question is in. Falls back to English."""
    try:
        messages = [
            {"role": "system",
             "content": "Reply with ONE word only: the English name of the language "
                        "the user's text is written in (for example English, Spanish, "
                        "Hindi, Chinese). Do not answer the text."},
            {"role": "user", "content": text},
        ]
        reply = call_ollama(messages, max_words=4)
        letters = "".join(ch for ch in reply.split()[0] if ch.isalpha())
        return letters if letters else "English"
    except Exception:
        return "English"


def translate_to_english(text):
    """Translates the question to English for searching. Falls back to the original."""
    try:
        messages = [
            {"role": "system",
             "content": "Translate the user's text into English. Reply with the "
                        "English translation only - no notes, no quotes. Do not "
                        "answer the question."},
            {"role": "user", "content": text},
        ]
        reply = call_ollama(messages, max_words=60)
        return reply.strip() if reply.strip() else text
    except Exception:
        return text


def warm_up():
    """Loads the search index early so the first question is not slow."""
    rag_pipeline.load_index()


def build_user_message(question, found_chunks, earlier_question=None, language="English"):
    """
    Combines the found text and the question into one message. No file names
    or numbers are included, so the LLM has nothing to quote.
    """
    context_parts = []
    for chunk in found_chunks:
        context_parts.append(chunk["text"])

    context_text = "\n\n---\n\n".join(context_parts)

    message = "INFORMATION:\n" + context_text + "\n\n"
    if earlier_question:
        message += "EARLIER STUDENT QUESTION (for context only): " + earlier_question + "\n"
    message += "STUDENT QUESTION: " + question + "\n\n"
    # Repeated here because the model follows the last instruction most.
    message += f"Write your answer in {language}."
    return message


def call_ollama(messages, max_words=None):
    """Sends the messages to Ollama and returns the answer text."""
    request_data = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        # low temperature = stick to the facts
        "options": {"temperature": 0.1, "num_ctx": 4096},
    }

    if max_words is not None:
        # short answers only (e.g. the language name)
        request_data["options"]["num_predict"] = max_words * 4
        request_data["options"]["temperature"] = 0

    request = urllib.request.Request(
        config.OLLAMA_URL,
        data=json.dumps(request_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=config.OLLAMA_TIMEOUT_SECONDS) as response:
        reply = json.loads(response.read().decode("utf-8"))

    return reply["message"]["content"].strip()


def generate_response(user_query, cover_type, history=None):
    """
    Called by chatbot_page.py for every question. Always returns plain text
    (an answer or an error message), so it never crashes the app.
    history is the earlier messages: [{"role": ..., "content": ...}, ...]
    """
    global last_language
    last_language = "English"

    if history is None:
        history = []

    cover_label = get_cover_label(cover_type)
    question = user_query.strip()
    simple_text = question.lower().strip("!.? ")

    if simple_text in GREETINGS:
        return ("Hello! I can answer questions about your " + cover_label +
                ", for example waiting periods, what is covered, "
                "and how to make a claim. What would you like to know?")
    if simple_text in THANKS:
        return "You're welcome! Ask me anything else about your " + cover_label + "."

    # Step 0: language
    language = detect_language(question)
    print("Answer language:", language)

    # Step 1: search the documents
    try:
        # short follow-ups need the previous question to be searchable
        search_text = question
        earlier_question = None
        if is_short_follow_up(question) and len(history) > 0:
            for old_message in reversed(history):
                if old_message["role"] == "user":
                    earlier_question = old_message["content"]
                    search_text = earlier_question + " " + question
                    break

        # documents are English, so search with the English translation
        if language.lower() != "english":
            search_text = translate_to_english(search_text)
            print("Searching with:", search_text)

        found_chunks = rag_pipeline.search(search_text, cover_type=cover_type)

    except FileNotFoundError as error:
        return "The knowledge base is not ready yet.\n" + str(error)
    except Exception as error:
        return "Sorry, something went wrong while searching the documents.\n" + str(error)

    # Step 2: nothing found
    if len(found_chunks) == 0:
        return ("Sorry, I could not find that information for " + cover_label +
                ".\n\nPlease try asking in a different way, or contact "
                "Medibank directly for help.")

    # terminal only: which files were used
    print("Chatbot used:", ", ".join(
        f"{chunk['source']} p.{chunk['page']} ({chunk['score']:.2f})"
        for chunk in found_chunks))

    # SHOW_CHUNKS = True in config.py prints the text sent to the LLM (debugging)
    if getattr(config, "SHOW_CHUNKS", False):
        for number, chunk in enumerate(found_chunks, start=1):
            print(f"--- chunk {number}: {chunk['source']} p.{chunk['page']} ---")
            print(chunk["text"])
        print("--- end of chunks ---")

    # Step 3: ask the LLM
    # Earlier answers are not sent: a Spanish answer made the model reply to
    # the next English question in Spanish.
    messages = [{"role": "system", "content": build_system_prompt(cover_type, language)}]
    messages.append({"role": "user",
                     "content": build_user_message(question, found_chunks,
                                                   earlier_question, language)})

    try:
        answer = call_ollama(messages)
        last_language = language
        return answer

    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            return "The AI model took too long to answer. Please try again."
        return ("I cannot reach the AI model.\n\n"
                "Please make sure Ollama is installed and running, and that "
                f"the model is downloaded (run:  ollama pull {config.OLLAMA_MODEL}).")
    except TimeoutError:
        return "The AI model took too long to answer. Please try again."
    except Exception as error:
        return "Sorry, something went wrong while writing the answer.\n" + str(error)


# Terminal test
if __name__ == "__main__":
    print("Medibank OSHC chatbot - terminal test. Type 'quit' to stop.")
    print("Cover types:", ", ".join(config.COVER_TYPES.keys()))
    chosen_cover = ""
    while chosen_cover not in config.COVER_TYPES:
        chosen_cover = input("Which cover type? ").strip().lower()

    warm_up()

    chat_history = []
    while True:
        typed = input("\nYou: ").strip()
        if typed.lower() in ("quit", "exit", "q"):
            break
        if typed == "":
            continue

        reply = generate_response(typed, chosen_cover, chat_history)
        print("\nBot:", reply)

        chat_history.append({"role": "user", "content": typed})
        chat_history.append({"role": "assistant", "content": reply})