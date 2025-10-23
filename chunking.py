"""
chunking.py
------------
Extracts text from PDF and splits into meaningful chunks using spaCy.
"""

import fitz  # PyMuPDF
import spacy

# Load spaCy model globally
nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    return text.strip()

def chunk_text_with_spacy(text, max_chunk_size=800, overlap=100):
    """Splits text into overlapping chunks using spaCy sentence segmentation."""
    doc = nlp(text)
    chunks = []
    current_chunk = ""

    for sent in doc.sents:
        if len(current_chunk) + len(sent.text) <= max_chunk_size:
            current_chunk += " " + sent.text
        else:
            chunks.append(current_chunk.strip())
            # Add overlap for better context
            current_chunk = " ".join(current_chunk.split()[-overlap:]) + " " + sent.text

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

if __name__ == "__main__":
    pdf_path = "D:/NLP222/nlp_pdf_ex.pdf"
    raw_text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text_with_spacy(raw_text)
    print(f"✅ Extracted {len(chunks)} chunks.")
