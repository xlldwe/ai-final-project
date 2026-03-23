import aiosqlite
import os
import logging
from bot_aiogram.config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db():
    dir_path = os.path.dirname(DB_PATH)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript('''
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
                delivery_type TEXT DEFAULT 'standard',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Seed products
        cursor = await db.execute('SELECT COUNT(*) FROM products')
        row = await cursor.fetchone()
        if row[0] == 0:
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
            await db.executemany(
                'INSERT INTO products (name, description, price, category, stock) VALUES (?, ?, ?, ?, ?)',
                products
            )

        await db.commit()
    logger.info("Aiogram database initialized.")


async def get_all_products():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM products WHERE active = 1 ORDER BY category, name')
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_product(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM products WHERE id = ? AND active = 1', (product_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def add_product(name, description, price, category):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'INSERT INTO products (name, description, price, category) VALUES (?, ?, ?, ?)',
            (name, description, price, category)
        )
        product_id = cursor.lastrowid
        await db.commit()
    logger.info(f"Product added: {name} id={product_id}")
    return product_id


async def remove_product(product_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('UPDATE products SET active = 0 WHERE id = ?', (product_id,))
        affected = cursor.rowcount
        await db.commit()
    logger.info(f"Product {product_id} removed")
    return affected > 0


async def register_user(user_id, username, first_name, last_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
            (user_id, username, first_name, last_name)
        )
        await db.commit()


async def create_order(user_id, username, items, total, address, delivery_type='standard'):
    import json
    items_json = json.dumps(items, ensure_ascii=False)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'INSERT INTO orders (user_id, username, items_json, total, address, delivery_type) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, username, items_json, total, address, delivery_type)
        )
        order_id = cursor.lastrowid
        await db.commit()
    logger.info(f"Order #{order_id} created for user {user_id}")
    return order_id


async def get_all_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM orders ORDER BY created_at DESC')
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_user_orders(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            'SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_order_status(order_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        await db.commit()
    logger.info(f"Order #{order_id} status updated to {status}")


async def save_feedback(user_id, username, text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO feedback (user_id, username, text) VALUES (?, ?, ?)',
            (user_id, username, text)
        )
        await db.commit()
    logger.info(f"Feedback saved from user {user_id}")


async def get_all_feedback():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('SELECT * FROM feedback ORDER BY created_at DESC')
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]