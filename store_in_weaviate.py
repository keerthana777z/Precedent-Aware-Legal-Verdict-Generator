"""
store_in_weaviate.py
---------------------
Loads saved chunks & embeddings, and inserts them into the Weaviate 'NLP' collection.
"""

import os
import json
import weaviate
from dotenv import load_dotenv
from weaviate.connect import ConnectionParams

# Load .env
load_dotenv()

WEAVIATE_HTTP_URL = os.getenv("WEAVIATE_HTTP_URL", "http://localhost:8081")
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))

# Connect to Weaviate
client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url(WEAVIATE_HTTP_URL, WEAVIATE_GRPC_PORT)
)
client.connect()

# Load data from local file
with open("chunk_embeddings.json", "r", encoding="utf-8") as f:
    data = json.load(f)

chunks = data["chunks"]
embeddings = data["embeddings"]

print(f"📥 Preparing to insert {len(chunks)} chunks into Weaviate...")

collection_name = "NLP"
collection = client.collections.get(collection_name)

for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
    collection.data.insert(
        properties={
            "text": chunk,
            "embedding": embedding,
            "source": "sample_legal_doc.pdf"
        }
    )

print(f"✅ Successfully inserted {len(chunks)} chunks into '{collection_name}' collection.")

client.close()
print("🔒 Connection closed.")
