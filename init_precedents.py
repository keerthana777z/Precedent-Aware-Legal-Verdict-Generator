import weaviate
from weaviate.classes.config import Property, DataType, Tokenization # <-- Import Tokenization
from weaviate.connect import ConnectionParams
import os
from dotenv import load_dotenv

# Load environment variables if needed
load_dotenv()
WEAVIATE_HTTP_URL = os.getenv("WEAVIATE_HTTP_URL", "http://localhost:8081")
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))

# Connect to Weaviate
try:
    client = weaviate.WeaviateClient(
        connection_params=ConnectionParams.from_url(WEAVIATE_HTTP_URL, WEAVIATE_GRPC_PORT)
    )
    client.connect()
    print("✅ Connected to Weaviate.")
except Exception as e:
    print(f"❌ Failed to connect to Weaviate: {e}")
    exit()

precedent_collection_name = "Precedents"

try:
    # Check if the collection already exists
    existing_collections = client.collections.list_all()
    if precedent_collection_name in existing_collections:
        print(f"⚠️ Collection '{precedent_collection_name}' already exists.")
        # Optional: Uncomment the next two lines if you want to delete and recreate it
        # client.collections.delete(precedent_collection_name)
        # print(f"🗑️ Deleted existing '{precedent_collection_name}' collection.")

    # Create the Precedents collection if it doesn't exist (or was just deleted)
    if precedent_collection_name not in client.collections.list_all(): # Check again
        client.collections.create(
            name=precedent_collection_name,
            description="Stores summaries and judgments from past legal cases",
            properties=[
                Property(name="case_summary", data_type=DataType.TEXT),
                Property(name="case_name", data_type=DataType.TEXT),
                # Corrected: Use Tokenization.FIELD for keyword-like behavior
                Property(name="citation", data_type=DataType.TEXT, tokenization=Tokenization.FIELD),
                # Optional: Add ipc_section property if you plan to store it
                # Property(name="ipc_section", data_type=DataType.TEXT, tokenization=Tokenization.FIELD),
            ],
            vectorizer_config=None # Using external embeddings (Cohere)
        )
        print(f"✅ Created '{precedent_collection_name}' collection successfully.")

    # Verify creation
    print("\n📚 Collections available now:")
    current_collections = client.collections.list_all() # Fetch again after potential creation
    for name in current_collections: # Iterate through keys (names)
         print(f"- {name}")

except Exception as e:
    print(f"❌ An error occurred: {e}") # Print the actual error message
finally:
    # Close the connection
    client.close()
    print("🔒 Connection closed.")