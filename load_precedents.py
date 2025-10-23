import os
import time
import pandas as pd
import cohere
import weaviate
import glob # Import the glob module to find files
from dotenv import load_dotenv
from weaviate.connect import ConnectionParams
from weaviate.classes.data import DataObject # Correct import for v4

# --- Configuration ---
# Use glob to find all CSV files starting with 'ipc_' and ending with '_cases.csv'
CSV_FILE_PATTERN = "ipc_*_cases.csv" #  Pattern to find your scraped files
PRECEDENT_COLLECTION_NAME = "Precedents"
BATCH_SIZE = 10 # Process N cases at a time for embedding
RETRY_DELAY = 60 # Seconds to wait if Cohere API limit is hit
# --- End Configuration ---

# --- Load Environment Variables & Initialize Clients ---
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embed-multilingual-v3.0")
WEAVIATE_HTTP_URL = os.getenv("WEAVIATE_HTTP_URL", "http://localhost:8081")
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))

if not COHERE_API_KEY:
    raise ValueError("❌ Cohere API key missing in .env file.")

try:
    co = cohere.Client(COHERE_API_KEY)
    print("✅ Cohere client initialized.")
except Exception as e:
    print(f"❌ Error initializing Cohere client: {e}")
    exit()

try:
    client = weaviate.WeaviateClient(
        connection_params=ConnectionParams.from_url(WEAVIATE_HTTP_URL, WEAVIATE_GRPC_PORT)
    )
    client.connect()
    print("✅ Weaviate client connected.")
except Exception as e:
    print(f"❌ Error connecting to Weaviate: {e}")
    exit()

# Check if collection exists
if PRECEDENT_COLLECTION_NAME not in client.collections.list_all():
    print(f"❌ Collection '{PRECEDENT_COLLECTION_NAME}' not found in Weaviate.")
    print("👉 Please create the collection first using a setup script.")
    client.close()
    exit()
else:
    precedent_collection = client.collections.get(PRECEDENT_COLLECTION_NAME)
    print(f"✅ Using Weaviate collection: {PRECEDENT_COLLECTION_NAME}")
    
# --- End Initialization ---

# --- Find all CSV files matching the pattern ---
csv_files = glob.glob(CSV_FILE_PATTERN)
if not csv_files:
    print(f"❌ No CSV files found matching the pattern '{CSV_FILE_PATTERN}'. Exiting.")
    client.close()
    exit()

print(f"📂 Found {len(csv_files)} CSV files to process:")
for f in csv_files:
    print(f"   - {f}")
# --- End Find CSV files ---

total_cases_processed = 0

# --- Loop through each CSV file ---
for csv_filename in csv_files:
    print(f"\n--- Processing file: {csv_filename} ---")

    # 1. Read the current CSV file
    try:
        df = pd.read_csv(csv_filename)
        # Handle potential missing summaries (fill with empty string)
        df['summary_text'] = df['summary_text'].fillna('')
        # Ensure other key columns exist
        if 'case_name' not in df.columns: df['case_name'] = 'N/A'
        if 'citation' not in df.columns: df['citation'] = 'N/A'
        print(f"📄 Read {len(df)} cases from {csv_filename}.")
    except Exception as e:
        print(f"❌ Error reading CSV file {csv_filename}: {e}. Skipping this file.")
        continue # Skip to the next file

    # Filter out rows with empty summaries as they can't be embedded
    df = df[df['summary_text'].str.strip() != '']
    if df.empty:
        print(f"🤷 No valid case summaries found in {csv_filename} to process.")
        continue # Skip to the next file

    print(f"⚙️ Processing {len(df)} cases with valid summaries from {csv_filename}...")

    # 2. Generate Embeddings & Store in Weaviate in Batches for this file
    file_cases_processed = 0
    # Use a new context manager for each file's batch operations
    with precedent_collection.batch.dynamic() as batch:
        for i in range(0, len(df), BATCH_SIZE):
            batch_df = df.iloc[i:i + BATCH_SIZE]
            texts_to_embed = batch_df['summary_text'].tolist()
            batch_num = (i // BATCH_SIZE) + 1

            print(f"   🧩 Processing batch {batch_num}/{ (len(df) + BATCH_SIZE - 1)//BATCH_SIZE } ({len(texts_to_embed)} cases)...")

            # Get Embeddings
            embeddings = []
            try:
                response = co.embed(
                    texts=texts_to_embed,
                    model=EMBEDDING_MODEL,
                    input_type="search_document"
                )
                embeddings = response.embeddings # Assuming list of lists/vectors
                print(f"   ✅ Batch {batch_num}: Embeddings generated ({len(embeddings)} vectors).")
                time.sleep(2) # Small delay

            except Exception as e:
                print(f"   ⚠️ Batch {batch_num} embedding failed: {e}")
                print(f"   ⏳ Retrying after {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
                try:
                    # Retry once
                    response = co.embed(
                        texts=texts_to_embed, model=EMBEDDING_MODEL, input_type="search_document"
                    )
                    embeddings = response.embeddings
                    print(f"   ✅ Batch {batch_num} retried successfully.")
                except Exception as e2:
                    print(f"   ❌ Batch {batch_num} failed again. Skipping batch. Error: {e2}")
                    continue # Skip this batch

            # Add data to Weaviate batch
            if len(embeddings) == len(batch_df):
                print(f"      Adding {len(batch_df)} items to Weaviate batch...")
                for idx, (_, row) in enumerate(batch_df.iterrows()):
                    properties = {
                        "case_summary": row['summary_text'],
                        "case_name": row['case_name'],
                        "citation": row['citation']
                        # Add other properties if needed
                    }
                    # Add IPC Section as a property IF you want (optional)
                    # ipc_section_from_filename = csv_filename.split('_')[1] # Extract from 'ipc_302_cases.csv'
                    # properties['ipc_section'] = ipc_section_from_filename

                    batch.add_object(
                         properties=properties,
                         vector=embeddings[idx]
                     )
                file_cases_processed += len(batch_df)
                print(f"      Batch {batch_num} added. Processed so far for this file: {file_cases_processed}")
            else:
                 print(f"      ❌ Mismatch between texts ({len(batch_df)}) and embeddings ({len(embeddings)}). Skipping Weaviate insertion for this batch.")

    print(f"--- Finished processing file: {csv_filename}. Added {file_cases_processed} cases. ---")
    total_cases_processed += file_cases_processed

print("\n\nFinished processing all CSV files! ")
print(f"Total cases processed and attempted to store in Weaviate: {total_cases_processed}")

# 3. Close Connection
client.close()
print("🔒 Weaviate connection closed.")