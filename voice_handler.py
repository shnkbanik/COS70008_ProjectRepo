# voice_handler.py
# Functionality:
# Everything about VOICE, so chatbot_page.py stays simple.
#
# 1. VOICE INPUT  (speech -> text)
#    start_recording()  : starts the microphone
#    stop_recording()   : stops it and returns the sound
#    transcribe(sound)  : turns the sound into text with Whisper
#                         (runs on this computer, no internet needed after
#                          the first download, and it understands many languages)
#
# 2. VOICE OUTPUT (text -> speech)
#    speak(text, language) : reads an answer aloud. Uses the built-in Windows
#                            voice on Windows and the "say" command on Mac
#                            (free, nothing to install)
#    stop_speaking()       : stops the voice
#
# The packages for voice input are only loaded when they are needed, so
# the chatbot still works normally if they are not installed.
#
# Install for voice input:   pip install faster-whisper sounddevice

import re
import subprocess
import sys
import threading
import numpy as np
import config

# ---------- Settings (all optional - add them to config.py to change) ----------
# Whisper model size: "base" = small and fast, "small" = more accurate
# (recommended for accents and other languages), "medium" = even better but slow.
WHISPER_MODEL_SIZE = getattr(config, "WHISPER_MODEL_SIZE", "small")
# None = Whisper detects the language by itself. Or force one, e.g. "en", "es".
WHISPER_LANGUAGE = getattr(config, "WHISPER_LANGUAGE", None)

SAMPLE_RATE = 16000          # Whisper wants 16000 samples per second
MIN_SECONDS = 0.5            # shorter recordings are ignored
MIN_LOUDNESS = 0.001         # quieter than this = the microphone heard nothing

# ---------- Things we keep in memory ----------
_recording_stream = None
_recorded_pieces = []
_whisper_model = None
_whisper_lock = threading.Lock()
_speech_process = None
_speech_lock = threading.Lock()
_speech_was_stopped = False


class VoiceError(Exception):
    """
    A problem we can explain to the student in plain words.
    The message of this error is shown on the screen.
    """


# =====================================================================
# 1. Voice input
# =====================================================================

def start_recording():
    """
    Starts recording from the default microphone.
    Call stop_recording() to finish.
    """
    global _recording_stream, _recorded_pieces

    try:
        import sounddevice
    except ImportError:
        raise VoiceError("Voice input is not installed yet.\n"
                         "Run this in the Terminal:  pip install faster-whisper sounddevice")

    _recorded_pieces = []

    def collect(indata, frames, time_info, status):
        # Called many times per second with a small piece of sound.
        _recorded_pieces.append(indata.copy())

    try:
        _recording_stream = sounddevice.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=collect)
        _recording_stream.start()
    except Exception as error:
        _recording_stream = None
        raise VoiceError("I could not open the microphone.\n"
                         "Check that a microphone is connected and that this program is "
                         "allowed to use it (Windows: Settings > Privacy > Microphone. "
                         "Mac: System Settings > Privacy & Security > Microphone).\n("
                         + str(error) + ")")


def stop_recording():
    """
    Stops the microphone and returns the sound as one list of numbers.
    """
    global _recording_stream

    if _recording_stream is not None:
        try:
            _recording_stream.stop()
            _recording_stream.close()
        except Exception:
            pass
        _recording_stream = None

    if len(_recorded_pieces) == 0:
        return np.zeros(0, dtype="float32")

    return np.concatenate(_recorded_pieces)[:, 0]


def is_recording():
    return _recording_stream is not None


def get_whisper_model():
    """
    Loads the Whisper model one time. The first time it is downloaded from
    the internet (small = about 460 MB), after that it works offline.
    """
    global _whisper_model

    with _whisper_lock:
        if _whisper_model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise VoiceError("Voice input is not installed yet.\n"
                                 "Run this in the Terminal:  pip install faster-whisper sounddevice")
            # "int8" keeps it fast and light on a normal laptop CPU.
            _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        return _whisper_model


def transcribe(sound):
    """
    Turns the recorded sound into text. Raises VoiceError with a friendly
    message if the recording is too short or silent.
    """
    if len(sound) < SAMPLE_RATE * MIN_SECONDS:
        raise VoiceError("The recording was too short. Click the microphone button, "
                         "speak your question, then click it again.")

    if float(np.max(np.abs(sound))) < MIN_LOUDNESS:
        raise VoiceError("The microphone did not hear any sound.\n"
                         "Check your microphone settings and allow the program you "
                         "start the chatbot from (Terminal, PyCharm or VS Code).")

    model = get_whisper_model()

    # vad_filter ignores silence, so Whisper does not invent words from noise.
    segments, info = model.transcribe(sound, beam_size=5, vad_filter=True,
                                      language=WHISPER_LANGUAGE)
    text = " ".join(segment.text.strip() for segment in segments).strip()

    if text == "":
        raise VoiceError("I could not hear any words. Please try again, a little closer "
                         "to the microphone.")
    return text


# =====================================================================
# 2. Voice output
# =====================================================================

# The Mac voice to use for each language (the name the LLM gives us).
# If a voice is not installed on your Mac: System Settings > Accessibility >
# Spoken Content > System Voice > Manage Voices.
MAC_VOICES = {
    "english": "Samantha",
    "spanish": "Monica",
    "french": "Thomas",
    "german": "Anna",
    "italian": "Alice",
    "portuguese": "Luciana",
    "hindi": "Lekha",
    "chinese": "Tingting",
    "mandarin": "Tingting",
    "japanese": "Kyoko",
    "korean": "Yuna",
    "arabic": "Maged",
    "indonesian": "Damayanti",
    "thai": "Kanya",
    "vietnamese": "Linh",
}

# On Windows we pick the voice by language code. If a language voice is not
# installed: Settings > Time & language > Speech > Add voices.
WINDOWS_LANGUAGE_CODES = {
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "hindi": "hi",
    "chinese": "zh",
    "mandarin": "zh",
    "japanese": "ja",
    "korean": "ko",
    "arabic": "ar",
    "indonesian": "id",
    "thai": "th",
    "vietnamese": "vi",
}


def clean_for_speech(text):
    """
    Removes things that sound strange when read aloud: bullet signs,
    asterisks, web links.
    """
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^\s*[•\*\-]\s+", "", text, flags=re.MULTILINE)
    text = text.replace("*", "").replace("#", "")
    text = re.sub(r"\n+", ". ", text)
    return text.strip()


def speak_on_windows(spoken_text, language):
    """
    Reads the text aloud with the built-in Windows voice (through PowerShell).
    Returns "" when all is fine, or a short message explaining the problem.
    """
    global _speech_process, _speech_was_stopped

    code = WINDOWS_LANGUAGE_CODES.get(language.lower())
    if code is None:
        return "Sorry, I have no voice for " + language + "."

    # PowerShell picks an installed voice for this language and reads the
    # text it receives on standard input. Exit code 3 = no voice for the language.
    script = (
        "[Console]::InputEncoding = [Text.Encoding]::UTF8; "
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$v = $s.GetInstalledVoices() | Where-Object { "
        "$_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq '" + code + "' } "
        "| Select-Object -First 1; "
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) } "
        "elseif ('" + code + "' -ne 'en') { exit 3 }; "
        "$s.Speak([Console]::In.ReadToEnd())"
    )

    with _speech_lock:
        _speech_was_stopped = False
        try:
            _speech_process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", script],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as error:
            return "I could not start the voice: " + str(error)
        process = _speech_process

    try:
        process.communicate(spoken_text.encode("utf-8"))
    except Exception:
        pass

    if _speech_was_stopped or process.returncode == 0:
        return ""
    if process.returncode == 3:
        return ("The voice for " + language + " is not installed on this PC "
                "(Settings > Time & language > Speech).")
    return "The voice could not play."


def speak(text, language="English"):
    """
    Reads the text aloud and waits until it is finished, so call it from a
    background thread. Returns "" when all is fine, or a short message
    explaining why nothing was spoken.
    """
    global _speech_process, _speech_was_stopped

    if sys.platform == "win32":
        spoken_text = clean_for_speech(text)
        if spoken_text == "":
            return ""
        stop_speaking()
        return speak_on_windows(spoken_text, language)

    if sys.platform != "darwin":
        return "Reading answers aloud only works on Windows or Mac."

    voice = MAC_VOICES.get(language.lower())
    if voice is None:
        return "Sorry, I have no voice for " + language + "."

    spoken_text = clean_for_speech(text)
    if spoken_text == "":
        return ""

    stop_speaking()

    # If the chosen voice is not installed, English falls back to the default voice.
    voices_to_try = [voice, None] if language.lower() == "english" else [voice]

    for voice_name in voices_to_try:
        command = ["say"]
        if voice_name is not None:
            command += ["-v", voice_name]
        command += ["-f", "-"]          # read the text from standard input

        with _speech_lock:
            _speech_was_stopped = False
            try:
                _speech_process = subprocess.Popen(
                    command, stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as error:
                return "I could not start the voice: " + str(error)
            process = _speech_process

        try:
            process.communicate(spoken_text.encode("utf-8"))
        except Exception:
            pass

        if _speech_was_stopped or process.returncode == 0:
            return ""

    return ("The voice for " + language + " is not installed on this Mac "
            "(System Settings > Accessibility > Spoken Content > System Voice > Manage Voices).")


def stop_speaking():
    """
    Stops the voice immediately (safe to call even if nothing is playing).
    """
    global _speech_was_stopped

    with _speech_lock:
        if _speech_process is not None and _speech_process.poll() is None:
            _speech_was_stopped = True
            try:
                _speech_process.terminate()
            except Exception:
                pass
