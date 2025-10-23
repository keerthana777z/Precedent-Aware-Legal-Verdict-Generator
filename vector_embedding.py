"""
vector_embedding.py
--------------------
Extracts text chunks from PDF, generates Cohere embeddings in batches,
and stores them into the Weaviate 'NLP' collection safely with rate-limit handling.
"""

import os
import time
import cohere
import weaviate
from dotenv import load_dotenv
from weaviate.connect import ConnectionParams
from chunking import extract_text_from_pdf, chunk_text_with_spacy

# ---------------------------
# Step 0: Load Configuration
# ---------------------------
load_dotenv()

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embed-multilingual-v3.0")
WEAVIATE_HTTP_URL = os.getenv("WEAVIATE_HTTP_URL", "http://localhost:8081")
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))

if not COHERE_API_KEY:
    raise ValueError("❌ Cohere API key missing in .env file.")

# Initialize Cohere & Weaviate clients
co = cohere.Client(COHERE_API_KEY)
client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url(WEAVIATE_HTTP_URL, WEAVIATE_GRPC_PORT)
)
client.connect()

collection_name = "NLP"
if collection_name not in client.collections.list_all():
    raise ValueError(f"❌ Collection '{collection_name}' not found in Weaviate.")
collection = client.collections.get(collection_name)

# -------------------------
# Step 1: Extract and Chunk
# -------------------------
pdf_path = "/Users/keerthana/Downloads/NLP_PRJ/punishments.pdf"
if not os.path.exists(pdf_path):
    raise FileNotFoundError(f"⚠️ PDF not found at {pdf_path}")

print(f"📄 Extracting text from: {pdf_path}")
text = extract_text_from_pdf(pdf_path)
chunks = chunk_text_with_spacy(text)
print(f"✅ Extracted {len(chunks)} text chunks.")

# -------------------------
# Step 2: Generate Embeddings in Batches
# -------------------------
BATCH_SIZE = 10        # Adjust as needed
RETRY_DELAY = 60          # Wait time (seconds) on rate-limit error
EMBEDDINGS = []

print("⚙️ Generating embeddings via Cohere (batch-safe mode)...")

for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i:i + BATCH_SIZE]
    batch_num = (i // BATCH_SIZE) + 1
    print(f"\n🧩 Processing batch {batch_num} ({len(batch)} chunks)...")

    try:
        response = co.embed(
            texts=batch,
            model=EMBEDDING_MODEL,
            input_type="search_document"
        )
        batch_embeddings = response.embeddings
        EMBEDDINGS.extend(batch_embeddings)
        print(f"✅ Batch {batch_num} completed successfully ({len(batch_embeddings)} embeddings).")
        time.sleep(5)  # Gentle pause between batches to avoid hitting limits

    except Exception as e:
        print(f"⚠️ Batch {batch_num} failed: {e}")
        print(f"⏳ Retrying after {RETRY_DELAY} seconds...")
        time.sleep(RETRY_DELAY)
        try:
            # Retry once
            response = co.embed(
                texts=batch,
                model=EMBEDDING_MODEL,
                input_type="search_document"
            )
            batch_embeddings = response.embeddings.float
            EMBEDDINGS.extend(batch_embeddings)
            print(f"✅ Batch {batch_num} retried successfully.")
        except Exception as e2:
            print(f"❌ Batch {batch_num} failed again. Skipping. Error: {e2}")
            continue

print(f"\n✅ All batches processed. Total embeddings: {len(EMBEDDINGS)}")

# -------------------------
# Step 3: Store in Weaviate
# -------------------------
print("\n📥 Inserting data into Weaviate...")

for i, (chunk, embedding) in enumerate(zip(chunks, EMBEDDINGS)):
    try:
        collection.data.insert(
            properties={
                "text": chunk,
                "source": os.path.basename(pdf_path)
            },
            vector=embedding
        )
        if (i + 1) % 10 == 0:
            print(f"   → Inserted {i + 1}/{len(chunks)} chunks...")
    except Exception as e:
        print(f"⚠️ Failed to insert chunk {i + 1}: {e}")

print(f"✅ Successfully stored {len(EMBEDDINGS)} chunks into '{collection_name}' collection.")

# -------------------------
# Step 4: Close Connection
# -------------------------
client.close()
print("🔒 Connection closed. All done!")
