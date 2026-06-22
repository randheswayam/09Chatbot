import os
# Force Protobuf to use the pure-Python implementation to avoid descriptor errors
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# SQLite fix for Streamlit Cloud
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import streamlit as st
import sqlite3
import chromadb
from groq import Groq
from semantic_router import Route
from semantic_router.layer import RouteLayer

# ... [The rest of your app.py code stays exactly the same below this] ...
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import sqlite3
import chromadb
from groq import Groq
from semantic_router import Route
from semantic_router.layer import RouteLayer
from semantic_router.encoders import HuggingFaceEncoder

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Flipkart AI Assistant", page_icon="🛒")
st.title("🛒 Flipkart AI Assistant")
st.caption("Powered by Llama 3.3, ChromaDB, and Semantic Router")

# Get Groq API Key from Streamlit Secrets
# In Streamlit Cloud, you will add this key in your App Settings -> Secrets.
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "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") #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
groq_client = Groq(api_key=GROQ_API_KEY)

# ==========================================
# 2. INITIALIZE DATABASES & ROUTER
# ==========================================
@st.cache_resource
def init_systems():
    # Initialize ChromaDB for FAQs
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    faq_collection = chroma_client.get_collection(name="flipkart_faqs")
    
    # Define Semantic Routes (How the bot decides where to look)
    faq_route = Route(
        name="faq",
        utterances=[
            "how do I return an item?", "where is my order?", 
            "what is the delivery fee", "how long for refund?", 
            "return policy", "track my package"
        ],
    )
    product_route = Route(
        name="product",
        utterances=[
            "what is the price of", "do you have the Poco X5", 
            "is the Sony TV in stock", "show me phones", 
            "Nike shoes cost"
        ],
    )
    
    # We use a lightweight encoder so it's fast on Streamlit Cloud
    encoder = HuggingFaceEncoder()
    router = RouteLayer(encoder=encoder, routes=[faq_route, product_route])
    
    return faq_collection, router

faq_collection, router = init_systems()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def get_faq_answer(query):
    """Retrieves FAQ context from ChromaDB."""
    results = faq_collection.query(query_texts=[query], n_results=1)
    if results['documents'][0]:
        return results['documents'][0][0]
    return "No relevant FAQ found."

def get_product_info(query):
    """Retrieves product information from SQLite database."""
    conn = sqlite3.connect("flipkart_products.db")
    cursor = conn.cursor()
    # Simple search: grab all products and let the LLM filter, 
    # or implement a basic keyword search. We'll do a simple fetch for simplicity.
    cursor.execute("SELECT name, price, stock_status FROM products")
    products = cursor.fetchall()
    conn.close()
    
    # Format the data so Llama 3.3 can read it easily
    context = "Here are some items from our catalog:\n"
    for p in products:
        context += f"- {p[0]}: ₹{p[1]} ({p[2]})\n"
    return context

def generate_llama_response(query, context, route_name):
    """Sends the context and user query to Llama 3.3 via Groq."""
    system_prompt = f"""You are a helpful customer support chatbot for Flipkart. 
    Use the provided context to answer the user's question. 
    If the context doesn't have the answer, politely say you don't know. 
    Context from {route_name} database: {context}"""

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        model="llama3-70b-8192", # We use an available Groq Llama model 
        temperature=0.3,
    )
    return chat_completion.choices[0].message.content

# ==========================================
# 4. STREAMLIT CHAT INTERFACE
# ==========================================
# Store chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask a question about Flipkart products or FAQs..."):
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Route the query (Semantic Router)
    route_choice = router(prompt).name
    
    # 2. Fetch appropriate data based on the route
    if route_choice == "faq":
        context_data = get_faq_answer(prompt)
        st.toast("Routed to: FAQ Database", icon="📚")
    elif route_choice == "product":
        context_data = get_product_info(prompt)
        st.toast("Routed to: Product Database", icon="📦")
    else:
        context_data = "I am a Flipkart assistant. I can help with FAQs or Products."
        st.toast("General Chat", icon="💬")

    # 3. Generate response using Llama 3.3
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = generate_llama_response(prompt, context_data, route_choice)
                st.markdown(response)
                # Save response to history
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Error connecting to LLM: {e}")
