"""
app.py — Precedent-Aware Legal Verdict Assistant
------------------------------------------------------------
Uses Cohere for embeddings + Chat for legal reasoning, and Weaviate for RAG retrieval
from both IPC sections and precedent cases.
"""

from flask import Flask, render_template, request, jsonify
import weaviate
import cohere
import os
import traceback
from dotenv import load_dotenv
from weaviate.connect import ConnectionParams
from cohere import Client

# --- NEW IMPORTS ---
import webbrowser
from threading import Timer
# --- END NEW IMPORTS ---


# ----------------------- #
#   CONFIG + CONNECTIONS  #
# ----------------------- #

load_dotenv()

app = Flask(__name__)

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
WEAVIATE_HTTP_URL = os.getenv("WEAVIATE_HTTP_URL", "http://localhost:8081")
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embed-multilingual-v3.0")
CHAT_MODEL = os.getenv("CHAT_MODEL", "c4ai-aya-23") # Or use "c4ai-aya-23"

# --- Define Port for Flask ---
FLASK_PORT = 5001 # Define the port number here
FLASK_HOST = "127.0.0.1"
# --- End Define Port ---

if not COHERE_API_KEY:
    raise ValueError("❌ Missing COHERE_API_KEY in .env file.")

# Initialize Cohere client
try:
    co = Client(COHERE_API_KEY)
    print("✅ Cohere client initialized.")
except Exception as e:
    print(f"❌ Error initializing Cohere client: {e}")
    exit()

# Connect to Weaviate
try:
    client = weaviate.WeaviateClient(
        connection_params=ConnectionParams.from_url(WEAVIATE_HTTP_URL, WEAVIATE_GRPC_PORT)
    )
    client.connect()
    print("✅ Connected to Weaviate.")
except Exception as e:
    print(f"❌ Error connecting to Weaviate: {e}")
    exit()

# Get references to both collections
ipc_collection = None
precedent_collection = None
try:
    ipc_collection_name = "NLP"
    precedent_collection_name = "Precedents"

    collections = client.collections.list_all()
    print("📚 Available collections:")
    for name in collections: print(f"- {name}") # Corrected loop


    if ipc_collection_name not in collections:
        raise ValueError(f"❌ '{ipc_collection_name}' collection not found in Weaviate.")
    ipc_collection = client.collections.get(ipc_collection_name)
    print(f"✅ Using IPC collection: {ipc_collection_name}")

    if precedent_collection_name not in collections:
         raise ValueError(f"❌ '{precedent_collection_name}' collection not found in Weaviate.")
    precedent_collection = client.collections.get(precedent_collection_name)
    print(f"✅ Using Precedents collection: {precedent_collection_name}\n")

except ValueError as ve:
     print(ve)
     if client.is_connected(): client.close()
     exit()
except Exception as e:
     print(f"❌ Error getting collections from Weaviate: {e}")
     if client.is_connected(): client.close()
     exit()


# ----------------------- #
#   ROUTES                #
# ----------------------- #

@app.route("/")
def index():
    """Serve the frontend."""
    return render_template("index.html")


@app.route("/query", methods=["POST"])
def query_verdict():
    """Handle RAG query pipeline with IPC and Precedents."""
    data = request.get_json()
    user_query = data.get("query", "").strip()

    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400

    print(f"\n🧠 New query received: {user_query}")

    # Step 1: Generate query embedding
    query_embedding = None # Initialize
    try:
        response = co.embed(
            model=EMBEDDING_MODEL,
            texts=[user_query],
            input_type="search_query"
        )
        if hasattr(response, 'embeddings') and isinstance(response.embeddings, list) and response.embeddings:
             query_embedding = response.embeddings[0]
        else:
             raise ValueError("Unexpected embedding response format from Cohere.")

        print("✅ Query embedding generated.")
    except Exception as e:
        print(f"❌ Cohere embedding failed: {e}")
        print(traceback.format_exc())
        return jsonify({"answer": f"Embedding generation failed. Error: {e}"}), 500

    if query_embedding is None:
         print("❌ Query embedding could not be generated or extracted.")
         return jsonify({"answer": "Failed to generate query embedding."}), 500


    # Step 2: Retrieve similar chunks from BOTH Weaviate collections
    ipc_results = []
    precedent_results = []
    try:
        print("🔍 Searching Weaviate for relevant IPC sections...")
        ipc_response = ipc_collection.query.near_vector(
            near_vector=query_embedding,
            limit=3,
            return_properties=["text", "source"]
        )
        ipc_results = ipc_response.objects or []
        print(f"✅ Retrieved {len(ipc_results)} IPC results.")

        print("🔍 Searching Weaviate for relevant precedents...")
        precedent_response = precedent_collection.query.near_vector(
            near_vector=query_embedding,
            limit=2,
            return_properties=["case_summary", "case_name", "citation"]
        )
        precedent_results = precedent_response.objects or []
        print(f"✅ Retrieved {len(precedent_results)} precedent results.")

    except Exception as e:
        print(f"❌ Weaviate query failed: {e}")
        print(traceback.format_exc())
        return jsonify({"answer": f"Error retrieving from Weaviate. Error: {e}"}), 500

    if not ipc_results and not precedent_results:
         print("⚠️ No matching IPC sections or precedents found.")
         return jsonify({
             "answer": "⚠️ No relevant legal content or precedents found in the database for this query.",
             "references": [],
             "precedent_references": []
            }), 200

    # Step 3: Build the combined context
    ipc_context = "\n\n".join(
        f"IPC Source: {obj.properties.get('source', 'N/A')}\nContent: {obj.properties.get('text', '')}"
        for obj in ipc_results
    ) if ipc_results else "No relevant IPC sections found."

    precedent_context = "\n\n".join(
        f"Case: {obj.properties.get('case_name', 'N/A')} ({obj.properties.get('citation', 'N/A')})\nSummary: {obj.properties.get('case_summary', '')}"
        for obj in precedent_results
    ) if precedent_results else "No relevant precedents found."


    # Step 4: Use Cohere Chat with updated prompt
    prompt = f"""
    You are acting as a legal judge in India. Your task is to analyze a given case scenario based *strictly* on the provided sections of the Indian Penal Code (IPC) and relevant legal precedents summaries.

    **Instructions:**
    1.  **Identify Relevant Law:** State the applicable IPC section(s) found in the 'IPC CONTEXT'.
    2.  **Consider Precedents:** Mention any relevant case(s) from the 'RELEVANT PRECEDENTS' section if they apply and explain how they influence the interpretation or decision. If no precedents apply, state that clearly.
    3.  **Legal Reasoning:** Explain step-by-step how the law (and precedents, if any) applies to the facts of the 'CASE SCENARIO'. Focus only on the provided context.
    4.  **Verdict:** Conclude with a clear judgment (e.g., "Guilty", "Not Guilty", "Liable under Section X").
    5.  **Punishment (If applicable):** If the retrieved IPC context specifies a punishment, mention it. If not, state that the punishment details are not available in the provided context.
    6.  **Format:** Structure your response like a concise court ruling with clear headings (e.g., **Relevant Law:**, **Precedents Considered:**, **Reasoning:**, **Verdict:**, **Punishment:**). Use markdown bold (**) for headings.
    7.  **Constraint:** DO NOT use any external knowledge about the IPC, precedents, or law beyond what is explicitly provided in the context below. If context is insufficient, state that clearly in the reasoning.

    **--- IPC CONTEXT ---**
    {ipc_context}

    **--- RELEVANT PRECEDENTS ---**
    {precedent_context}

    **--- CASE SCENARIO ---**
    {user_query}

    **--- YOUR RULING ---**
    """

    answer = "⚠️ Failed to generate answer."
    try:
        print(f"💬 Sending prompt to Cohere Chat model ({CHAT_MODEL})...")
        chat_response = co.chat(
            model=CHAT_MODEL,
            message=prompt,
            temperature=0.3,
            max_tokens=800
        )

        answer = chat_response.text.strip()
        print("✅ Cohere Chat answer generated.\n")

    except Exception as e:
        print(f"❌ Cohere Chat failed: {e}")
        print(traceback.format_exc())
        answer = f"⚠️ Failed to generate answer via Cohere Chat. Error: {e}"
        return jsonify({"answer": answer, "references": [], "precedent_references": []}), 500

    # Prepare references to return (WITH SNIPPETS for IPC)
    ipc_refs = [
        f"{obj.properties.get('source', 'IPC Section')}: \"{obj.properties.get('text', '')[:75]}...\""
        for obj in ipc_results
    ]

    precedent_refs = [
        f"{obj.properties.get('case_name', 'N/A')} ({obj.properties.get('citation', 'N/A')})"
         for obj in precedent_results
    ]

    return jsonify({
        "answer": answer,
        "references": ipc_refs,
        "precedent_references": precedent_refs
    })


# ----------------------- #
#   MAIN ENTRY POINT      #
# ----------------------- #

# --- NEW: Function to open browser ---
def open_browser():
    """Opens the web browser to the Flask app's URL."""
    url = f"http://{FLASK_HOST}:{FLASK_PORT}"
    print(f"🌍 Opening browser to {url}")
    webbrowser.open_new(url)
# --- END NEW Function ---

if __name__ == "__main__":
    # Use a timer to open the browser 1 second after app.run is called
    Timer(1, open_browser).start()

    # Run the Flask app
    # Use host='0.0.0.0' if you want it accessible from other devices on your network
    # For local development, '127.0.0.1' (or default) is fine.
    app.run(debug=True, host=FLASK_HOST, port=FLASK_PORT)