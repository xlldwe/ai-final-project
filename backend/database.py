import sqlite3
import os
from backend.config import Config


def get_db_connection():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT,
            stock INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT DEFAULT 'Admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chat_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_message TEXT,
            bot_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Insert sample products if empty
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        products = [
            ('T-Shirt Classic', 'Comfortable cotton t-shirt, perfect for everyday wear.', 299.99, 'T-Shirts', None, 50),
            ('Slim Jeans', 'Modern slim-fit jeans in dark wash denim.', 799.99, 'Jeans', None, 30),
            ('Summer Dress', 'Elegant floral summer dress, lightweight fabric.', 599.99, 'Dresses', None, 25),
            ('Leather Jacket', 'Premium genuine leather jacket, classic style.', 2499.99, 'Jackets', None, 15),
            ('Sport Sneakers', 'Comfortable athletic sneakers for daily use.', 899.99, 'Shoes', None, 40),
            ('Wool Sweater', 'Warm merino wool sweater for cold days.', 699.99, 'Sweaters', None, 20),
            ('Cargo Pants', 'Versatile cargo pants with multiple pockets.', 549.99, 'Pants', None, 35),
            ('Linen Shirt', 'Breathable linen shirt, perfect for summer.', 449.99, 'Shirts', None, 45),
        ]
        cursor.executemany(
            'INSERT INTO products (name, description, price, category, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)',
            products
        )

    # Insert sample blog posts if empty
    cursor.execute('SELECT COUNT(*) FROM blog_posts')
    if cursor.fetchone()[0] == 0:
        posts = [
            ('Spring Collection 2024', 'Discover our breathtaking spring collection featuring vibrant colors and fresh styles. This season we bring you the finest fabrics from around the world, carefully crafted into timeless pieces that will elevate your wardrobe.', 'Fashion Team'),
            ('How to Care for Your Clothes', 'Proper clothing care extends the life of your garments and keeps them looking their best. Learn the essential tips for washing, drying, and storing your favorite fashion pieces.', 'Style Expert'),
            ('Sustainable Fashion Guide', 'Fashion industry is one of the largest polluters in the world. We are committed to changing that. Learn about our eco-friendly initiatives and how you can make more sustainable fashion choices.', 'Eco Team'),
        ]
        cursor.executemany(
            'INSERT INTO blog_posts (title, content, author) VALUES (?, ?, ?)',
            posts
        )

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


def get_all_products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products ORDER BY category, name').fetchall()
    conn.close()
    return [dict(p) for p in products]


def get_product_by_id(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    return dict(product) if product else None


def get_all_blog_posts():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM blog_posts ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(p) for p in posts]


def save_contact(name, email, message):
    conn = get_db_connection()
    conn.execute('INSERT INTO contacts (name, email, message) VALUES (?, ?, ?)', (name, email, message))
    conn.commit()
    conn.close()


def save_chat_analytics(session_id, user_message, bot_response):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO chat_analytics (session_id, user_message, bot_response) VALUES (?, ?, ?)',
        (session_id, user_message, bot_response)
    )
    conn.commit()
    conn.close()


def get_chat_analytics():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM chat_analytics ORDER BY created_at DESC LIMIT 100').fetchall()
    conn.close()
    return [dict(r) for r in rows]