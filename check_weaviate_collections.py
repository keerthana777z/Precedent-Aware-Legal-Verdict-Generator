import weaviate
from weaviate.connect import ConnectionParams
from dotenv import load_dotenv
import os

# Load .env variables
load_dotenv()

WEAVIATE_HTTP_URL = os.getenv("WEAVIATE_HTTP_URL", "http://localhost:8081")
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))

# Connect to Weaviate
client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url(WEAVIATE_HTTP_URL, WEAVIATE_GRPC_PORT)
)
client.connect()

# ✅ List all collections
collections = client.collections.list_all()
print("\n📚 Collections in your Weaviate instance:\n")
for col in collections:
    print(" -", col)  # <-- just print the string name directly

# ✅ Optional: Count total documents
for col in collections:
    try:
        collection = client.collections.get(col)
        count = collection.aggregate.over_all(total_count=True).total_count
        print(f"   {col} → {count} objects")
    except Exception as e:
        print(f"   ⚠️ Could not fetch count for {col}: {e}")

client.close()
