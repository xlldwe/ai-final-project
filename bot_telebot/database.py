import sqlite3
import os
import logging
from bot_telebot.config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection():
    dir_path = os.path.dirname(DB_PATH)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            stock INTEGER DEFAULT 100,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            items_json TEXT NOT NULL,
            total REAL NOT NULL,
            address TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            data_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Seed products if empty
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        products = [
            ('T-Shirt Classic', 'Comfortable cotton t-shirt, perfect for everyday wear.', 299.99, 'T-Shirts', 50),
            ('Slim Jeans', 'Modern slim-fit jeans in dark wash denim.', 799.99, 'Jeans', 30),
            ('Summer Dress', 'Elegant floral summer dress, lightweight fabric.', 599.99, 'Dresses', 25),
            ('Leather Jacket', 'Premium genuine leather jacket, classic style.', 2499.99, 'Jackets', 15),
            ('Sport Sneakers', 'Comfortable athletic sneakers for daily use.', 899.99, 'Shoes', 40),
            ('Wool Sweater', 'Warm merino wool sweater for cold days.', 699.99, 'Sweaters', 20),
            ('Cargo Pants', 'Versatile cargo pants with multiple pockets.', 549.99, 'Pants', 35),
            ('Linen Shirt', 'Breathable linen shirt, perfect for summer.', 449.99, 'Shirts', 45),
        ]
        cursor.executemany(
            'INSERT INTO products (name, description, price, category, stock) VALUES (?, ?, ?, ?, ?)',
            products
        )

    conn.commit()
    conn.close()
    logger.info("Telebot database initialized successfully.")


def get_all_products():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM products WHERE active = 1 ORDER BY category, name').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(product_id):
    conn = get_connection()
    row = conn.execute('SELECT * FROM products WHERE id = ? AND active = 1', (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_product(name, description, price, category):
    conn = get_connection()
    cursor = conn.execute(
        'INSERT INTO products (name, description, price, category) VALUES (?, ?, ?, ?)',
        (name, description, price, category)
    )
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Product added: {name} (id={product_id})")
    return product_id


def remove_product(product_id):
    conn = get_connection()
    cursor = conn.execute('UPDATE products SET active = 0 WHERE id = ?', (product_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    logger.info(f"Product removed: id={product_id}")
    return affected > 0


def register_user(user_id, username, first_name, last_name):
    conn = get_connection()
    conn.execute(
        '''INSERT OR IGNORE INTO users (id, username, first_name, last_name)
           VALUES (?, ?, ?, ?)''',
        (user_id, username, first_name, last_name)
    )
    conn.commit()
    conn.close()


def create_order(user_id, username, items_json, total, address=''):
    conn = get_connection()
    cursor = conn.execute(
        'INSERT INTO orders (user_id, username, items_json, total, address) VALUES (?, ?, ?, ?, ?)',
        (user_id, username, items_json, total, address)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Order created: id={order_id}, user={user_id}, total={total}")
    return order_id


def get_all_orders():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order(order_id):
    conn = get_connection()
    row = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_order_status(order_id, status):
    conn = get_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()


def get_user_orders(user_id):
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_feedback(user_id, username, text):
    conn = get_connection()
    conn.execute(
        'INSERT INTO feedback (user_id, username, text) VALUES (?, ?, ?)',
        (user_id, username, text)
    )
    conn.commit()
    conn.close()
    logger.info(f"Feedback saved from user {user_id}")


def get_all_feedback():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM feedback ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_user_state(user_id, state, data_json='{}'):
    conn = get_connection()
    conn.execute(
        '''INSERT OR REPLACE INTO user_states (user_id, state, data_json, updated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
        (user_id, state, data_json)
    )
    conn.commit()
    conn.close()


def get_user_state(user_id):
    conn = get_connection()
    row = conn.execute(
        'SELECT state, data_json FROM user_states WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return row['state'], row['data_json']
    return None, '{}'


def clear_user_state(user_id):
    conn = get_connection()
    conn.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()