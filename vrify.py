import weaviate
from weaviate.connect import ConnectionParams

client = weaviate.WeaviateClient(
    connection_params=ConnectionParams.from_url("http://localhost:8081", 50051)
)
client.connect()

collection = client.collections.get("NLP")

# Check total object count
count = collection.aggregate.over_all(total_count=True).total_count
print(f"📊 Total objects in NLP collection: {count}")

# Fetch sample objects to inspect
response = collection.query.fetch_objects(limit=3)
for i, obj in enumerate(response.objects or [], 1):
    print(f"\n--- Object {i} ---")
    print(f"Text (first 150 chars): {obj.properties['text'][:150]}")
    print(f"Embedding length: {len(obj.properties['embedding']) if 'embedding' in obj.properties else '❌ None'}")

client.close()
