import sqlite3
import chromadb

def setup_sqlite():
    """Sets up the SQLite database for Product Inquiries."""
    print("Setting up SQLite for Products...")
    conn = sqlite3.connect("flipkart_products.db")
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            price REAL,
            stock_status TEXT
        )
    ''')
    
    # Clear existing dummy data (if you run this script twice)
    cursor.execute('DELETE FROM products')
    
    # Insert some dummy Flipkart products
    sample_products = [
        ("Poco X5 Pro", "Mobiles", 22999.00, "In Stock"),
        ("Sony Bravia 4K TV", "Electronics", 55000.00, "In Stock"),
        ("Nike Air Max", "Fashion", 4500.00, "Out of Stock"),
        ("Whirlpool Refrigerator", "Appliances", 18500.00, "In Stock")
    ]
    cursor.executemany("INSERT INTO products (name, category, price, stock_status) VALUES (?, ?, ?, ?)", sample_products)
    conn.commit()
    conn.close()
    print("SQLite setup complete!")

def setup_chromadb():
    """Sets up ChromaDB and ingests FAQ data."""
    print("Setting up ChromaDB for FAQs...")
    # Creates a local database folder named "chroma_db"
    client = chromadb.PersistentClient(path="./chroma_db") 
    
    # Create or get a collection for our FAQs
    collection = client.get_or_create_collection(name="flipkart_faqs")
    
    # Dummy FAQ Data
    faqs = [
        "Flipkart has a 7-day return policy for most electronics. For clothing, it is 14 days.",
        "To track your order, go to 'My Orders' section in the Flipkart app and click on the 'Track' button next to your item.",
        "Flipkart Plus members get free delivery on all items. Non-members get free delivery on orders above ₹500.",
        "Refunds usually take 3 to 5 business days to reflect in your original payment method after the returned item is picked up."
    ]
    
    # Ingest data into Chromadb (vector database)
    collection.add(
        documents=faqs,
        ids=["faq1", "faq2", "faq3", "faq4"]
    )
    print("ChromaDB setup complete!")

if __name__ == "__main__":
    setup_sqlite()
    setup_chromadb()