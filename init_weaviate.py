import weaviate
from weaviate.classes.config import Property, DataType
from weaviate.connect import ConnectionParams

# Initialize client
client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url("http://localhost:8081", 50051)
)

# 🔌 Open the connection
client.connect()

try:
    class_name = "NLP"

    # ✅ List collections correctly for v4 client
    existing_collections = client.collections.list_all()

    if class_name not in existing_collections:
        client.collections.create(
            name=class_name,
            description="Stores text and its embeddings for legal or NLP-based documents",
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="embedding", data_type=DataType.NUMBER_ARRAY),
                Property(name="source", data_type=DataType.TEXT),
            ],
            vectorizer_config=None  # Using external embeddings (Cohere)
        )
        print("✅ 'NLP' collection created successfully.")
    else:
        print("⚠️ 'NLP' collection already exists.")

    # Optional: verify creation
    print("📚 Collections available now:", client.collections.list_all())

finally:
    # 🔒 Close the connection
    client.close()
    print("🔒 Connection closed.")
