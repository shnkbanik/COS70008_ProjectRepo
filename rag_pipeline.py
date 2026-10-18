# rag_pipeline.py
# Functionality:
# This is the "search engine" of fetching information from documents
# read every Medibank document in the knowledge_base folder,
# cut it into small pieces ("chunks"),
# turn each chunk into numbers (an "embedding"),
# save them in a FAISS index.
# Search: turn the student's question into numbers
# ask FAISS "which chunks are closest in meaning?"
# The LLM reads ONLY those best chunks and writes the answer.
# This is what stops the LLM from making things up.

import os
import json
import re
import threading
import numpy as np
import faiss
from pypdf import PdfReader
import config

# File location for the documents of the knowledge base folder
BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_PATH = os.path.join(BASE_FOLDER, config.KNOWLEDGE_BASE_FOLDER)
INDEX_PATH = os.path.join(BASE_FOLDER, config.INDEX_FOLDER)
FAISS_FILE = os.path.join(INDEX_PATH, "index.faiss")
CHUNKS_FILE = os.path.join(INDEX_PATH, "chunks.json")
META_FILE = os.path.join(INDEX_PATH, "meta.json")

# Load the AI model and FAISS DB for single time and remember it here for next question
_embedding_model = None
_faiss_index = None
_chunks = []
# Stop two threads (warm-up + a question) from building index at the same time
_load_lock = threading.Lock()

# read the doc of knowledge base
def get_document_files():
    """
    Returns the full paths of every .pdf / .txt / .md file in the knowledge_base folder in alphabetical order
    """
    if not os.path.isdir(KNOWLEDGE_BASE_PATH):
        return []
    paths = []
    for file_name in sorted(os.listdir(KNOWLEDGE_BASE_PATH)):
        if file_name.lower().endswith((".pdf", ".txt", ".md")):
            paths.append(os.path.join(KNOWLEDGE_BASE_PATH, file_name))
    return paths

def read_document(path):
    """
    Reads a document and returns list of page_number and text.
    .txt / .md file is treated as one single page.
    """
    pages = []

    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        for page_index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append((page_index + 1, text))
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            pages.append((1, file.read()))

    return pages

# Cutting text into chunks

def split_into_chunks(text, chunk_size, overlap):
    """
    Cuts one long text into pieces of about `chunk_size` characters.
    Each piece repeats the last `overlap` characters of the previous one, so no sentence is lost at the cut.
    """
    # Make all spaces and line breaks into single spaces.
    text = " ".join(text.split())

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Look for a nice place to cut in the last 40% of this piece.
            earliest_cut = start + int(chunk_size * 0.6)
            cut = text.rfind(". ", earliest_cut, end)
            if cut == -1:
                cut = text.rfind(" ", earliest_cut, end)
            if cut != -1:
                end = cut + 1
        piece = text[start:end].strip()
        # Ignore tiny pieces (page numbers, headers)
        if len(piece) > 40:
            chunks.append(piece)
        if end >= len(text):
            break
        # Create overlap
        start = max(end - overlap, start + 1)
    return chunks

# Embedding: turning text into numbers
def get_embedding_model():
    """
    Loads the sentence-transformers model one time and remembers it. The first run downloads it from the internet
    """
    global _embedding_model
    if _embedding_model is None:
        # Imported here (not at the top) because this import is slow.
        # This way the app window can open quickly.
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _embedding_model

def embed_texts(text_list):
    """
    Turns a list of texts into a table of numbers (one row per text)
    """
    model = get_embedding_model()
    vectors = model.encode(
        text_list,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype="float32")

# Building and saving the index
def make_signature():
    """
    A short "fingerprint" of the documents + settings. We save it with
    the index. If it changes later (new PDF, edited PDF, new chunk size)
    we know the saved index is old and must be rebuilt.
    """
    files = []
    for path in get_document_files():
        files.append([os.path.basename(path),
                      os.path.getsize(path),
                      int(os.path.getmtime(path))])

    return {
        "files": files,
        "model": config.EMBEDDING_MODEL_NAME,
        "chunk_size": config.CHUNK_SIZE,
        "chunk_overlap": config.CHUNK_OVERLAP,
    }


def build_index():
    """
    Reads all documents, makes chunks, embeds them, and saves the index
    to disk. Returns (faiss_index, chunks).
    """
    document_paths = get_document_files()
    if len(document_paths) == 0:
        raise FileNotFoundError(
            "No documents found. Please put the Medibank OSHC PDF files "
            "into the folder: " + KNOWLEDGE_BASE_PATH)

    chunks = []
    for path in document_paths:
        source_name = os.path.basename(path)
        for page_number, page_text in read_document(path):
            for piece in split_into_chunks(page_text,
                                           config.CHUNK_SIZE,
                                           config.CHUNK_OVERLAP):
                chunks.append({
                    "source": source_name,
                    "page": page_number,
                    "text": piece,
                })

    if len(chunks) == 0:
        raise ValueError(
            "The documents contain no readable text. If they are scanned "
            "images, they need OCR first.")

    print("RAG: embedding", len(chunks), "chunks from",
          len(document_paths), "document(s)...")

    vectors = embed_texts([chunk["text"] for chunk in chunks])

    # IndexFlatIP = "compare by inner product". With normalized vectors
    # that is exactly cosine similarity. "Flat" = check every chunk,
    # which is perfectly fast for a few thousand chunks.
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    # Save everything so next time we skip all of the above.
    os.makedirs(INDEX_PATH, exist_ok=True)
    faiss.write_index(index, FAISS_FILE)
    with open(CHUNKS_FILE, "w", encoding="utf-8") as file:
        json.dump(chunks, file, ensure_ascii=False)
    with open(META_FILE, "w", encoding="utf-8") as file:
        json.dump(make_signature(), file)

    print("RAG: index saved.")
    return index, chunks


def saved_index_is_up_to_date():
    """
    True if a saved index exists AND the documents have not changed
    since it was built.
    """
    if not (os.path.exists(FAISS_FILE) and os.path.exists(CHUNKS_FILE)
            and os.path.exists(META_FILE)):
        return False

    with open(META_FILE, "r", encoding="utf-8") as file:
        saved_signature = json.load(file)

    return saved_signature == make_signature()


def load_index():
    """
    Makes sure the index is ready in memory. Safe to call many times:
    after the first time it returns instantly.
    """
    global _faiss_index, _chunks

    with _load_lock:
        if _faiss_index is not None:
            return

        if saved_index_is_up_to_date():
            _faiss_index = faiss.read_index(FAISS_FILE)
            with open(CHUNKS_FILE, "r", encoding="utf-8") as file:
                _chunks = json.load(file)
        else:
            _faiss_index, _chunks = build_index()


def rebuild_index():
    """
    Forces a fresh build (for example after an admin adds a new PDF).
    """
    global _faiss_index, _chunks

    with _load_lock:
        _faiss_index, _chunks = build_index()

# Searching
def get_cover_type_of_file(file_name):
    """
    Decides which cover type a document belongs to, using its FILE NAME.
    config.COVER_TYPES has the words to look for, for example:
        "comprehensive" -> Comprehensive_OSHC_Brochure.pdf
        "essential"     -> Essentials_OSHC_Cover_Summary.pdf
    A file with none of those words (for example Medibank_OSHC_Member_Guide.pdf)
    is treated as a GENERAL document and returns "all" - it is used for
    every cover type.
    """
    lower_name = file_name.lower()
    for cover_key in config.COVER_TYPES:
        if cover_key in lower_name:
            return cover_key
    return "all"


def search(question, top_k=None, cover_type=None):
    """
    Finds the chunks closest in meaning to the question.

    cover_type -> "comprehensive" or "essential" (the keys of
                  config.COVER_TYPES). Only documents of that cover type,
                  plus the general documents, are searched.
                  None = search every document.

    Returns a list (best first) of small dictionaries:
    {"text": ..., "source": ..., "page": ..., "score": ...}
    Only chunks with score >= MIN_RELEVANCE_SCORE are returned,
    so an empty list means "nothing relevant in our documents".
    """
    if top_k is None:
        top_k = config.TOP_K

    load_index()

    question_vector = embed_texts([question])

    # Ask FAISS to score every chunk (best first)
    scores, positions = _faiss_index.search(question_vector, _faiss_index.ntotal)

    results = []
    for score, position in zip(scores[0], positions[0]):
        # The list is sorted best-first, so once a score is too low,
        # every chunk after it is too low as well.
        if score < config.MIN_RELEVANCE_SCORE:
            break

        chunk = _chunks[position]

        # Skip documents that belong to the OTHER cover type.
        if cover_type is not None:
            file_cover = get_cover_type_of_file(chunk["source"])
            if file_cover != "all" and file_cover != cover_type:
                continue

        results.append({
            "text": chunk["text"],
            "source": chunk["source"],
            "page": chunk["page"],
            "score": float(score),
        })

        if len(results) >= top_k:
            break

    return results


# Test the code (python rag_pipeline.py)
# Type a question and see which chunks are found and their scores.
# Use this to tune MIN_RELEVANCE_SCORE in config.py.

if __name__ == "__main__":
    print("RAG search test. Documents folder:", KNOWLEDGE_BASE_PATH)
    load_index()
    print("Ready,", len(_chunks), "chunks loaded. Type 'quit' to stop.")
    print("Cover types:", ", ".join(config.COVER_TYPES.keys()))
    chosen_cover = input("Search which cover type? (press Enter for all): ").strip().lower()
    if chosen_cover not in config.COVER_TYPES:
        chosen_cover = None
    print()

    while True:
        test_question = input("Question: ").strip()
        if test_question.lower() in ("quit", "exit", "q"):
            break
        if test_question == "":
            continue

        found = search(test_question, cover_type=chosen_cover)
        if len(found) == 0:
            print("  -> nothing relevant found.\n")
        for item in found:
            print(f"  [{item['score']:.2f}] {item['source']} p.{item['page']}")
            print("   ", item["text"][:200].replace("\n", " "), "...\n")