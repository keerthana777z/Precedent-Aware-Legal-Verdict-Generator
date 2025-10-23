# ⚖️ Precedent-Aware Legal Verdict Generator

> AI-Powered Legal Decision Support for the Indian Context. Analyze Indian cases instantly: AI delivers crime classification, IPC mapping, and precedent-aware verdict recommendations, specifically calibrated for local legal frameworks.

This project utilizes Retrieval-Augmented Generation (RAG) with Weaviate and Cohere to analyze legal case summaries (or FIR details), retrieve relevant Indian Penal Code (IPC) sections and historical precedents, and generate a structured, AI-powered verdict draft.

## ✨ Features

* **Case Input:** Accepts textual input describing case details or FIR summaries.
* **IPC Section Retrieval (RAG):** Identifies and retrieves potentially relevant IPC sections based on the input text using vector similarity search.
* **Precedent Retrieval (RAG):** Searches a database of past case summaries/judgments to find relevant precedents based on vector similarity.
* **AI Verdict Generation:** Uses a large language model (Cohere) to synthesize the retrieved IPC sections and precedents, analyze the input scenario, and generate a structured verdict including:
    * Relevant Law Identified
    * Precedents Considered (and their applicability)
    * Legal Reasoning
    * Verdict (Guilty/Not Guilty/Liable)
    * Punishment (if specified in retrieved context)
* **Web Interface:** Simple Flask-based web UI for easy interaction.

<img width="1483" height="821" alt="Screenshot 2025-10-23 at 10 47 11 PM" src="https://github.com/user-attachments/assets/839b2b58-fcb1-441c-a2fb-4d1c12787d94" />
<img width="1502" height="834" alt="Screenshot 2025-10-23 at 10 53 20 PM" src="https://github.com/user-attachments/assets/da2bc096-9b27-4432-9bbc-b8f6a7961356" />
<img width="1510" height="812" alt="Screenshot 2025-10-23 at 10 52 23 PM" src="https://github.com/user-attachments/assets/2a80917b-9316-4f17-8f08-f26f67ec8d5f" />
<img width="1502" height="718" alt="Screenshot 2025-10-23 at 10 54 09 PM" src="https://github.com/user-attachments/assets/9e234104-3cf1-4ede-900d-694e7898f750" />
<img width="1512" height="540" alt="Screenshot 2025-10-23 at 10 54 35 PM" src="https://github.com/user-attachments/assets/bb7b2426-d2ba-4275-938c-da84e8e5ed54" />




## 🛠️ Tech Stack

* **Backend:** Python, Flask
* **Vector Database:** Weaviate (deployed via Docker)
* **AI/Embeddings:** Cohere API (for text embeddings and verdict generation)
* **Web Scraping (Data Collection):** Selenium, BeautifulSoup4
* **Data Handling:** Pandas
* **Deployment:** Docker (for Weaviate)
* **Frontend:** HTML, CSS, JavaScript

## ⚙️ Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/keerthana777z/Precedent-Aware-Legal-Verdict-Generator.git](https://github.com/keerthana777z/Precedent-Aware-Legal-Verdict-Generator.git)
    cd Precedent-Aware-Legal-Verdict-Generator
    ```

2.  **Install Docker:** Ensure you have Docker Desktop installed and running. Download from [Docker's website](https://www.docker.com/products/docker-desktop/).

3.  **Configure Environment Variables:**
    * Create a file named `.env` in the project root directory.
    * Add your Cohere API key:
        ```
        COHERE_API_KEY=YOUR_COHERE_API_KEY_HERE
        ```
    * *(Optional)* You can also override Weaviate URLs/ports or AI model names in this file (e.g., `WEAVIATE_HTTP_URL`, `CHAT_MODEL`).

4.  **Install Python Dependencies:**
    * It's recommended to use a virtual environment:
        ```bash
        python3 -m venv venv
        source venv/bin/activate # On macOS/Linux
        # .\venv\Scripts\activate # On Windows
        ```
    * Install required packages:
        ```bash
        pip install weaviate-client cohere python-dotenv flask pandas selenium beautifulsoup4 spacy PyMuPDF cramjam # Added cramjam to avoid warnings
        # Download Spacy model for chunking (used in vector_embedding.py if needed)
        spacy download en_core_web_sm
        ```
    * *Note:* Ensure NumPy version conflicts are resolved (sometimes downgrading might be needed: `pip install "numpy<2.0"` if you encounter issues).



## 🚀 Running the Application

Follow these steps in order:

1.  **Start Weaviate Database:**
    * Open your terminal in the project directory.
    * Run: `docker-compose up -d`
    * Wait ~30 seconds for Weaviate to initialize fully.
    * *(To stop Weaviate later: `docker-compose down`)*

2.  **Create Weaviate Collections:**
    * Run the initialization scripts to set up the necessary tables (collections) in Weaviate:
        ```bash
        # Initialize/Clear the IPC collection (ensure init_weaviate.py/del.py creates "NLP")
        python init_weaviate.py # Or your equivalent setup script for the 'NLP' collection

        # Initialize the Precedents collection
        python init_precedents.py
        ```
    * *Note:* Check these scripts. `init_precedents.py` should create a collection named `Precedents`. Ensure your script for IPC sections creates one named `NLP`.

3.  **Prepare Data (Load IPC Sections):**
    * You need to load the base IPC section text into the `NLP` collection.
    * **Option A (Using Friend's JSON):** If you have `chunk_embeddings.json` and `store_in_weaviate.py`:
        ```bash
        python store_in_weaviate.py # Loads pre-processed IPC chunks from JSON
        ```
    * **Option B (Processing PDF):** If you have the IPC PDF (e.g., `nlp_pdf.pdf`) and want to process it directly:
        * Ensure `pdf_path` and `collection_name = "NLP"` are set correctly in `vector_embedding.py`.
        * Run: `python vector_embedding.py`
    * **Option C (Using `punishments.pdf`):** If you want to load the text from `punishments.pdf`:
        * Ensure `pdf_path="punishments.pdf"` and `collection_name = "NLP"` are set in `vector_embedding.py`.
        * Run: `python vector_embedding.py` *(This will ADD punishment data alongside any existing IPC data if you didn't clear the collection)*

4.  **Scrape Precedent Data (Optional, if needed):**
    * Modify `scrape_precedents.py` to set the desired `ipc_section` and relevant `search_query`.
    * Run: `python scrape_precedents.py`
    * Repeat for other IPC sections to generate multiple `ipc_XXX_cases.csv` files.

5.  **Load Precedent Data into Weaviate:**
    * This script finds all `ipc_*_cases.csv` files and loads them.
    * Run: `python load_precedents.py`
    * This might take time depending on the number of cases and Cohere API usage.

6.  **Run the Flask Web Application:**
    * ```bash
        python app.py
        ```
    * The script should automatically open your default web browser to `http://127.0.0.1:5001` (or the port specified in `app.py`). If not, navigate there manually.

## Usage

1.  Once the web application is running and loaded in your browser:
2.  Enter the details of an FIR or a case summary into the text area.
3.  Click the "Generate Verdict" button.
4.  Wait for the system to process the query (embedding, searching Weaviate, generating response with Cohere).
5.  The AI-generated verdict/analysis will appear in the right-hand panel, along with the IPC sections and precedents that were retrieved and considered relevant.




## 🛣️ Future Work / Roadmap

* Implement file upload functionality (PDF, TXT, DOC).
* Add an explicit crime classification step using NLP models.
* Expand the precedent database significantly.
* Refine the RAG retrieval strategy (e.g., re-ranking).
* Improve the frontend UI/UX.
* Add user authentication and case management features.
* Implement evaluation metrics to measure verdict quality.

## 🙏 Acknowledgements

* Cohere for providing the language models and embedding APIs.
* Weaviate for the open-source vector database.
* Indian Kanoon for access to legal documents (used for scraping).

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

## DONE BY:
[keerthana777z](https://github.com/keerthana777z)


