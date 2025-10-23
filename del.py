"""
reset_collection.py
--------------------
Deletes and recreates the 'NLP' collection cleanly.
Use this when you want to wipe all data before re-embedding.
"""

import weaviate
from weaviate.classes.config import Property, DataType
from weaviate.connect import ConnectionParams

client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url("http://localhost:8081", 50051)
)
client.connect()

collection_name = "NLP"

# 1️⃣ Delete existing collection
collections = client.collections.list_all()
if collection_name in collections:
    client.collections.delete(collection_name)
    print(f"🗑️ Deleted old collection '{collection_name}'.")
else:
    print(f"⚠️ No existing collection named '{collection_name}' found.")

# 2️⃣ Recreate it fresh
client.collections.create(
    name=collection_name,
    description="Stores text and its embeddings for legal or NLP-based documents",
    properties=[
        Property(name="text", data_type=DataType.TEXT),
        Property(name="embedding", data_type=DataType.NUMBER_ARRAY),
        Property(name="source", data_type=DataType.TEXT),
    ],
    vectorizer_config=None  # External embeddings
)

print(f"✅ Fresh '{collection_name}' collection created successfully.")

# 3️⃣ Verify
print("📚 Collections now:", client.collections.list_all())

client.close()
print("🔒 Connection closed.")
