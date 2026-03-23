import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flasgger import Swagger, swag_from
import anthropic
from groq import Groq
import uuid
import logging
import io
import numpy as np
from PIL import Image

from backend.config import Config
from backend.database import (
    init_db, get_all_products, get_product_by_id,
    get_all_blog_posts, save_contact, save_chat_analytics, get_chat_analytics
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../web', static_url_path='')
app.secret_key = Config.SECRET_KEY
CORS(app, supports_credentials=True)

# ─── Swagger / OpenAPI config ────────────────────────────────────────────────
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "FashionAI Shop API",
        "description": (
            "## REST API для FashionAI Shop\n\n"
            "Повне API для онлайн-магазину одягу з інтегрованим AI чат-ботом.\n\n"
            "### Можливості:\n"
            "- **Чат-бот** — контекстний діалог через Claude AI\n"
            "- **Товари** — каталог з фільтрацією по категоріях\n"
            "- **Блог** — новини та статті магазину\n"
            "- **Контакти** — форма зворотного зв'язку\n"
            "- **Аналітика** — статистика взаємодії з ботом\n\n"
            "### Базовий URL: `http://localhost:5000`\n"
            "### Swagger UI: `http://localhost:5000/apidocs/`"
        ),
        "version": "1.0.0",
        "contact": {
            "name": "FashionAI Support",
            "email": "support@fashionai.shop",
        },
        "license": {
            "name": "MIT",
        },
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "tags": [
        {"name": "chat", "description": "AI чат-бот (Claude API)"},
        {"name": "products", "description": "Каталог товарів"},
        {"name": "blog", "description": "Блог і новини"},
        {"name": "contact", "description": "Форма зворотного зв'язку"},
        {"name": "analytics", "description": "Аналітика чат-бота"},
        {"name": "health", "description": "Статус сервісу"},
    ],
    "definitions": {
        "Product": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "example": 1},
                "name": {"type": "string", "example": "T-Shirt Classic"},
                "description": {"type": "string", "example": "Comfortable cotton t-shirt"},
                "price": {"type": "number", "format": "float", "example": 299.99},
                "category": {"type": "string", "example": "T-Shirts"},
                "image_url": {"type": "string", "nullable": True},
                "stock": {"type": "integer", "example": 50},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "BlogPost": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "example": 1},
                "title": {"type": "string", "example": "Spring Collection 2024"},
                "content": {"type": "string", "example": "Discover our breathtaking..."},
                "author": {"type": "string", "example": "Fashion Team"},
                "created_at": {"type": "string", "format": "date-time"},
            },
        },
        "ChatRequest": {
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {
                    "type": "string",
                    "example": "Які товари є у вашому каталозі?",
                    "minLength": 1,
                    "maxLength": 2000,
                },
            },
        },
        "ChatResponse": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "example": "У нашому каталозі є футболки, джинси, сукні...",
                },
                "session_id": {
                    "type": "string",
                    "format": "uuid",
                    "example": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                },
            },
        },
        "ContactRequest": {
            "type": "object",
            "required": ["name", "email", "message"],
            "properties": {
                "name": {"type": "string", "example": "Олексій Шевченко"},
                "email": {"type": "string", "format": "email", "example": "oleksiy@example.com"},
                "message": {"type": "string", "example": "Хотів би дізнатися про знижки"},
            },
        },
        "Error": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "example": "Message cannot be empty"},
            },
        },
    },
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

init_db()

SYSTEM_PROMPT_BASE = """You are a helpful AI assistant for FashionAI Shop, an online clothing store.
You help customers with:
- Finding products and providing recommendations
- Answering questions about sizing, materials, and care instructions
- Explaining shipping, returns, and payment policies
- General fashion advice and styling tips

Store policies:
- Free shipping on orders over 1000 UAH
- 30-day return policy
- Payment methods: credit cards, PayPal, Telegram Payments
- Customer support: support@fashionai.shop

IMPORTANT: Only recommend products that are listed below in the catalog. Never invent products or prices.
Be friendly, concise, and helpful. Respond in the same language the customer uses."""


def build_system_prompt():
    products = get_all_products()
    if not products:
        return SYSTEM_PROMPT_BASE
    lines = ["\nCurrent product catalog:"]
    for p in products:
        stock_note = " (out of stock)" if p['stock'] == 0 else ""
        lines.append(f"- {p['name']} | {p['category']} | {p['price']:.0f} UAH | {p['description']}{stock_note}")
    return SYSTEM_PROMPT_BASE + "\n".join(lines)

chat_sessions = {}


# ─── Health ─────────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    """
    Перевірка статусу сервісу
    ---
    tags:
      - health
    summary: Health check
    description: Повертає статус сервісу та версію API
    responses:
      200:
        description: Сервіс працює нормально
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
            service:
              type: string
              example: FashionAI Backend
            version:
              type: string
              example: "1.0.0"
    """
    return jsonify({"status": "ok", "service": "FashionAI Backend", "version": "1.0.0"})


# ─── Static pages ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return app.send_static_file('index.html')


# ─── Chat ────────────────────────────────────────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Надіслати повідомлення AI чат-боту
    ---
    tags:
      - chat
    summary: Чат з AI асистентом
    description: |
      Відправляє повідомлення до Claude AI та отримує відповідь.
      Контекст діалогу зберігається в межах сесії (до 20 останніх повідомлень).
      Якщо `ANTHROPIC_API_KEY` не задано — повертає demo-відповідь.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          $ref: '#/definitions/ChatRequest'
    responses:
      200:
        description: Відповідь бота
        schema:
          $ref: '#/definitions/ChatResponse'
      400:
        description: Порожнє повідомлення
        schema:
          $ref: '#/definitions/Error'
    """
    data = request.json
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    session_id = session['session_id']

    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    chat_sessions[session_id].append({'role': 'user', 'content': user_message})
    history = chat_sessions[session_id][-20:]

    system_prompt = build_system_prompt()

    if Config.GROQ_API_KEY:
        try:
            client = Groq(api_key=Config.GROQ_API_KEY)
            response = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role': 'system', 'content': system_prompt}] + history,
                max_tokens=1024,
                temperature=0.7,
            )
            bot_response = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            bot_response = get_demo_response(user_message)
    elif Config.ANTHROPIC_API_KEY:
        try:
            client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            response = client.messages.create(
                model='claude-haiku-4-5-20251001',
                max_tokens=1024,
                system=system_prompt,
                messages=history,
            )
            bot_response = response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            bot_response = get_demo_response(user_message)
    else:
        bot_response = get_demo_response(user_message)

    chat_sessions[session_id].append({'role': 'assistant', 'content': bot_response})
    save_chat_analytics(session_id, user_message, bot_response)

    return jsonify({'response': bot_response, 'session_id': session_id})


@app.route('/api/chat/session', methods=['DELETE'])
def clear_chat_session():
    """
    Очистити поточну сесію чату
    ---
    tags:
      - chat
    summary: Скинути контекст діалогу
    description: Видаляє історію повідомлень поточної сесії. Наступне повідомлення почне нову сесію.
    responses:
      200:
        description: Сесія очищена
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Session cleared
    """
    session_id = session.get('session_id')
    if session_id and session_id in chat_sessions:
        del chat_sessions[session_id]
    session.pop('session_id', None)
    return jsonify({'success': True, 'message': 'Session cleared'})


def get_demo_response(message):
    msg = message.lower()

    # Greetings
    if any(w in msg for w in ['hello', 'hi', 'привіт', 'вітаю', 'хелоу', 'hey']):
        return (
            "Привіт! 👋 Ласкаво просимо до <b>FashionAI Shop</b>!\n\n"
            "Я ваш особистий стиліст-асистент. Можу допомогти:\n"
            "• Підібрати одяг під ваш стиль\n"
            "• Розповісти про наші товари та ціни\n"
            "• Відповісти на питання про доставку та оплату\n\n"
            "Що вас цікавить? 😊"
        )

    # Jacket recommendations
    elif any(w in msg for w in ['jacket', 'куртка', 'жакет', 'пальто', 'coat', 'піджак', 'blazer']):
        return (
            "🧥 Відмінний вибір! У нас є чудові варіанти верхнього одягу:\n\n"
            "<b>Leather Jacket</b> — 2 499 UAH\n"
            "Класична шкіряна куртка, преміум якість. Підходить до джинсів та штанів.\n\n"
            "<b>Wool Sweater</b> — 699 UAH\n"
            "Тепла та стильна альтернатива для прохолодної погоди.\n\n"
            "💡 <i>Порада стиліста:</i> Шкіряна куртка + темні slim jeans = ідеальний look на кожен день!\n\n"
            "Хочете дізнатися більше про якийсь товар?"
        )

    # Dress recommendations
    elif any(w in msg for w in ['dress', 'сукня', 'плаття']):
        return (
            "👗 У нас є чудова сукня для вас!\n\n"
            "<b>Summer Dress</b> — 599 UAH\n"
            "Елегантна квіткова сукня з легкої тканини. Ідеальна для літа та вечірніх виходів.\n\n"
            "💡 <i>Порада стиліста:</i> Доповніть образ нашими Sandals (499 UAH) та маленькою сумочкою!\n\n"
            "Бажаєте переглянути увесь каталог суконь?"
        )

    # Jeans recommendations
    elif any(w in msg for w in ['jeans', 'джинси', 'штани', 'pants', 'trouser']):
        return (
            "👖 Наші варіанти брюк та джинсів:\n\n"
            "<b>Slim Jeans</b> — 799 UAH\n"
            "Сучасні джинси slim-fit, темне забарвлення. Підходять і для офісу, і для прогулянки.\n\n"
            "<b>Cargo Pants</b> — 549 UAH\n"
            "Практичні штани-карго з кишенями. Стильно та зручно.\n\n"
            "💡 <i>Порада стиліста:</i> Slim Jeans + біла сорочка Linen Shirt = бездоганний casual look!"
        )

    # T-shirt / shirt recommendations
    elif any(w in msg for w in ['t-shirt', 'футболка', 'shirt', 'сорочка', 'блуза', 'top']):
        return (
            "👕 Наші топи та сорочки:\n\n"
            "<b>T-Shirt Classic</b> — 299 UAH\n"
            "Зручна бавовняна футболка для щоденного носіння. Є різні кольори.\n\n"
            "<b>Linen Shirt</b> — 449 UAH\n"
            "Легка лляна сорочка, ідеальна для літа. Дихає та не мнеться.\n\n"
            "💡 <i>Порада:</i> Базові футболки — основа будь-якого гардеробу! Рекомендуємо взяти 2-3 кольори."
        )

    # Shoes / sneakers
    elif any(w in msg for w in ['shoes', 'sneakers', 'взуття', 'кросівки', 'сандалі', 'boots', 'sandal']):
        return (
            "👟 Наше взуття:\n\n"
            "<b>Sport Sneakers</b> — 899 UAH\n"
            "Зручні кросівки для щоденного використання та спорту.\n\n"
            "💡 <i>Підходять до:</i> джинсів, спортивних штанів, casual образів."
        )

    # Season recommendations
    elif any(w in msg for w in ['літо', 'лiто', 'лыто', 'summer', 'жарко', 'спека', 'тепло']):
        return (
            "☀️ <b>Літні образи від FashionAI:</b>\n\n"
            "<b>Summer Dress</b> — 599 UAH\n"
            "Легка квіткова сукня з натуральної тканини. Ідеально для спеки!\n\n"
            "<b>T-Shirt Classic</b> — 299 UAH\n"
            "Бавовняна футболка — основа літнього гардеробу.\n\n"
            "<b>Linen Shirt</b> — 449 UAH\n"
            "Льон дихає та не мнеться — ідеально для літа.\n\n"
            "<b>Sport Sneakers</b> — 899 UAH\n"
            "Легке взуття для активного літа.\n\n"
            "💡 <i>Порада:</i> Льон та бавовна — найкращі тканини для літа!"
        )

    elif any(w in msg for w in ['зима', 'winter', 'холодно', 'мороз', 'теплий']):
        return (
            "❄️ <b>Зимові образи від FashionAI:</b>\n\n"
            "<b>Leather Jacket</b> — 2 499 UAH\n"
            "Шкіряна куртка — стильно та тепло в будь-яку погоду.\n\n"
            "<b>Wool Sweater</b> — 699 UAH\n"
            "Вовняний светр — затишок та стиль в одному.\n\n"
            "💡 <i>Порада:</i> Светр + джинси = perfect winter look!"
        )

    elif any(w in msg for w in ['вечірка', 'вечір', 'party', 'свято', 'ресторан', 'клуб', 'побачення', 'event']):
        return (
            "🎉 <b>Вечірні образи від FashionAI:</b>\n\n"
            "<b>Summer Dress</b> — 599 UAH\n"
            "Елегантна сукня — ідеальна для вечірніх виходів.\n\n"
            "<b>Leather Jacket</b> — 2 499 UAH\n"
            "Шкіряна куртка надає образу впевненості та стилю.\n\n"
            "<b>Slim Jeans</b> — 799 UAH\n"
            "Темні slim jeans + сорочка = класичний вечірній look.\n\n"
            "💡 <i>Порада стиліста:</i> Для вечірки — поєднуйте Leather Jacket із сукнею або Slim Jeans із Linen Shirt!"
        )

    elif any(w in msg for w in ['офіс', 'робота', 'office', 'бізнес', 'business', 'формальний']):
        return (
            "💼 <b>Офісний стиль від FashionAI:</b>\n\n"
            "<b>Linen Shirt</b> — 449 UAH\n"
            "Строга та стильна сорочка для офісу.\n\n"
            "<b>Slim Jeans</b> — 799 UAH\n"
            "Smart casual — темні джинси відмінно підходять для офісу.\n\n"
            "<b>Leather Jacket</b> — 2 499 UAH\n"
            "Ділова куртка для зустрічей та переговорів.\n\n"
            "💡 <i>Порада:</i> Linen Shirt + Slim Jeans = ідеальний офісний casual!"
        )

    # General recommendations / help choosing
    elif any(w in msg for w in ['recommend', 'порад', 'обрати', 'вибрати', 'підібрати', 'suggest', 'help', 'допоможи', 'що обрати', 'що купити', 'show', 'покажи']):
        return (
            "🛍️ Залюбки допоможу! Розкажіть трохи більше:\n\n"
            "• <b>Для чого одяг?</b> (робота, прогулянка, вечірка, спорт)\n"
            "• <b>Який стиль?</b> (casual, класика, спорт)\n"
            "• <b>Який бюджет?</b> (до 500, до 1000, до 2500 UAH)\n\n"
            "Або можу одразу показати наші <b>хіти продажів</b>:\n\n"
            "🥇 Leather Jacket — 2 499 UAH (найпопулярніше)\n"
            "🥈 Slim Jeans — 799 UAH\n"
            "🥉 Sport Sneakers — 899 UAH\n"
            "⭐ Summer Dress — 599 UAH\n"
            "⭐ T-Shirt Classic — 299 UAH"
        )

    # Price / cost
    elif any(w in msg for w in ['price', 'cost', 'ціна', 'скільки', 'коштує', 'вартість', 'дорого', 'cheap', 'budget', 'бюджет']):
        return (
            "💰 Наші ціни:\n\n"
            "👕 T-Shirt Classic — <b>299 UAH</b>\n"
            "👗 Summer Dress — <b>599 UAH</b>\n"
            "👖 Cargo Pants — <b>549 UAH</b>\n"
            "👔 Linen Shirt — <b>449 UAH</b>\n"
            "🧥 Wool Sweater — <b>699 UAH</b>\n"
            "👖 Slim Jeans — <b>799 UAH</b>\n"
            "👟 Sport Sneakers — <b>899 UAH</b>\n"
            "🧥 Leather Jacket — <b>2 499 UAH</b>\n\n"
            "🚚 <i>Безкоштовна доставка від 1 000 UAH!</i>"
        )

    # Shipping / delivery
    elif any(w in msg for w in ['shipping', 'delivery', 'доставка', 'deliver', 'send', 'відправка']):
        return (
            "🚚 <b>Доставка:</b>\n\n"
            "• Безкоштовна при замовленні від <b>1 000 UAH</b>\n"
            "• Стандартна доставка: 2-5 робочих днів (50 UAH)\n"
            "• Експрес доставка: 1-2 дні (150 UAH)\n"
            "• Доставка по всій Україні\n\n"
            "📦 Відстеження замовлення надсилається на email після відправки."
        )

    # Returns
    elif any(w in msg for w in ['return', 'refund', 'повернення', 'обмін', 'exchange']):
        return (
            "🔄 <b>Повернення та обмін:</b>\n\n"
            "• 30 днів на повернення з дня отримання\n"
            "• Товар має бути без слідів носіння та з бирками\n"
            "• Гроші повертаємо протягом 3-5 робочих днів\n"
            "• Обмін на інший розмір — безкоштовно\n\n"
            "📧 Для оформлення повернення: support@fashionai.shop"
        )

    # Payment
    elif any(w in msg for w in ['pay', 'payment', 'оплата', 'оплатити', 'карта', 'card']):
        return (
            "💳 <b>Способи оплати:</b>\n\n"
            "• Банківська карта (Visa/Mastercard)\n"
            "• PayPal\n"
            "• Telegram Payments\n"
            "• Накладений платіж (оплата при отриманні)\n\n"
            "🔒 Всі платежі захищені SSL шифруванням."
        )

    # Size guide
    elif any(w in msg for w in ['size', 'розмір', 'розміри', 'fit', 'підходить']):
        return (
            "📏 <b>Таблиця розмірів:</b>\n\n"
            "XS — обхват грудей 80-84 см\n"
            "S — обхват грудей 84-88 см\n"
            "M — обхват грудей 88-92 см\n"
            "L — обхват грудей 92-96 см\n"
            "XL — обхват грудей 96-100 см\n"
            "XXL — обхват грудей 100-104 см\n\n"
            "💡 Не знаєте свій розмір? Напишіть свій зріст та вагу — підберемо!"
        )

    # Catalog
    elif any(w in msg for w in ['catalog', 'каталог', 'товари', 'products', 'collection', 'колекція', 'all', 'все']):
        return (
            "🛍️ <b>Наш каталог:</b>\n\n"
            "👕 Футболки та топи\n"
            "👖 Джинси та штани\n"
            "👗 Сукні\n"
            "🧥 Куртки та пальто\n"
            "👔 Сорочки\n"
            "🧶 Светри\n"
            "👟 Взуття\n\n"
            "Перейдіть на сторінку <b>Catalog</b> або запитайте мене про конкретну категорію!"
        )

    # Contact / support
    elif any(w in msg for w in ['contact', 'support', 'контакт', 'підтримка', 'допомога', 'help']):
        return (
            "📞 <b>Контакти FashionAI Shop:</b>\n\n"
            "📧 Email: support@fashionai.shop\n"
            "📱 Telegram: @fashionai_support\n"
            "🕐 Час роботи: Пн-Пт 9:00-18:00\n\n"
            "Або залиште повідомлення через форму на сторінці <b>Contact</b>."
        )

    else:
        return (
            "Дякую за питання! 😊\n\n"
            "Я можу допомогти з:\n"
            "• 👗 Підбором одягу — напишіть що шукаєте\n"
            "• 💰 Цінами — запитайте про конкретний товар\n"
            "• 🚚 Доставкою та оплатою\n"
            "• 📏 Вибором розміру\n"
            "• 🔄 Поверненням товарів\n\n"
            "Просто напишіть своє питання!"
        )


# ─── Products ────────────────────────────────────────────────────────────────

@app.route('/api/products', methods=['GET'])
def products():
    """
    Отримати список всіх товарів
    ---
    tags:
      - products
    summary: Каталог товарів
    description: Повертає всі товари, відсортовані за категорією та назвою.
    parameters:
      - in: query
        name: category
        type: string
        required: false
        description: Фільтр по категорії (T-Shirts, Jeans, Dresses, Jackets, Shoes, Sweaters, Pants, Shirts)
        example: Jeans
    responses:
      200:
        description: Список товарів
        schema:
          type: array
          items:
            $ref: '#/definitions/Product'
    """
    category = request.args.get('category')
    all_products = get_all_products()
    if category:
        all_products = [p for p in all_products if p['category'].lower() == category.lower()]
    return jsonify(all_products)


@app.route('/api/products/<int:product_id>', methods=['GET'])
def product(product_id):
    """
    Отримати товар за ID
    ---
    tags:
      - products
    summary: Деталі товару
    description: Повертає повну інформацію про конкретний товар за його ID.
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
        description: Унікальний ідентифікатор товару
        example: 1
    responses:
      200:
        description: Товар знайдено
        schema:
          $ref: '#/definitions/Product'
      404:
        description: Товар не знайдено
        schema:
          $ref: '#/definitions/Error'
    """
    p = get_product_by_id(product_id)
    if p:
        return jsonify(p)
    return jsonify({'error': 'Product not found'}), 404


@app.route('/api/products/categories', methods=['GET'])
def product_categories():
    """
    Отримати список категорій товарів
    ---
    tags:
      - products
    summary: Всі категорії
    description: Повертає унікальний список категорій наявних у каталозі.
    responses:
      200:
        description: Список категорій
        schema:
          type: object
          properties:
            categories:
              type: array
              items:
                type: string
              example: ["Dresses", "Jackets", "Jeans", "Pants", "Shirts", "Shoes", "Sweaters", "T-Shirts"]
    """
    all_products = get_all_products()
    categories = sorted(set(p['category'] for p in all_products))
    return jsonify({'categories': categories})


# ─── Blog ────────────────────────────────────────────────────────────────────

@app.route('/api/blog', methods=['GET'])
def blog():
    """
    Отримати всі статті блогу
    ---
    tags:
      - blog
    summary: Список статей
    description: Повертає всі статті блогу, відсортовані від найновіших до найстаріших.
    responses:
      200:
        description: Список статей
        schema:
          type: array
          items:
            $ref: '#/definitions/BlogPost'
    """
    return jsonify(get_all_blog_posts())


@app.route('/api/blog/<int:post_id>', methods=['GET'])
def blog_post(post_id):
    """
    Отримати статтю блогу за ID
    ---
    tags:
      - blog
    summary: Деталі статті
    description: Повертає повний текст статті блогу за її ID.
    parameters:
      - in: path
        name: post_id
        type: integer
        required: true
        description: Унікальний ідентифікатор статті
        example: 1
    responses:
      200:
        description: Стаття знайдена
        schema:
          $ref: '#/definitions/BlogPost'
      404:
        description: Стаття не знайдена
        schema:
          $ref: '#/definitions/Error'
    """
    posts = get_all_blog_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    if post:
        return jsonify(post)
    return jsonify({'error': 'Post not found'}), 404


# ─── Contact ─────────────────────────────────────────────────────────────────

@app.route('/api/contact', methods=['POST'])
def contact():
    """
    Надіслати повідомлення через форму зворотного зв'язку
    ---
    tags:
      - contact
    summary: Форма контакту
    description: |
      Зберігає повідомлення від користувача в базі даних.
      Всі поля обов'язкові. Email перевіряється на коректність формату.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          $ref: '#/definitions/ContactRequest'
    responses:
      200:
        description: Повідомлення надіслано
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Your message has been sent!
      400:
        description: Помилка валідації
        schema:
          $ref: '#/definitions/Error'
    """
    data = request.json
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()

    if not all([name, email, message]):
        return jsonify({'error': 'All fields are required'}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'error': 'Invalid email address'}), 400

    save_contact(name, email, message)
    return jsonify({'success': True, 'message': 'Your message has been sent!'})


# ─── Analytics ───────────────────────────────────────────────────────────────

@app.route('/api/analytics', methods=['GET'])
def analytics():
    """
    Аналітика чат-бота
    ---
    tags:
      - analytics
    summary: Статистика взаємодії
    description: |
      Повертає загальну статистику використання чат-бота та останні 10 діалогів.
      Корисно для моніторингу активності та покращення відповідей бота.
    responses:
      200:
        description: Статистика
        schema:
          type: object
          properties:
            total_chats:
              type: integer
              description: Загальна кількість повідомлень
              example: 142
            recent_chats:
              type: array
              description: Останні 10 повідомлень
              items:
                type: object
                properties:
                  id:
                    type: integer
                  session_id:
                    type: string
                  user_message:
                    type: string
                  bot_response:
                    type: string
                  created_at:
                    type: string
                    format: date-time
    """
    data = get_chat_analytics()
    return jsonify({'total_chats': len(data), 'recent_chats': data[:10]})


@app.route('/api/analytics/summary', methods=['GET'])
def analytics_summary():
    """
    Зведена статистика по темах чатів
    ---
    tags:
      - analytics
    summary: Топ тем запитів
    description: Аналізує повідомлення та виводить найпопулярніші теми запитів користувачів.
    responses:
      200:
        description: Зведена статистика
        schema:
          type: object
          properties:
            total_messages:
              type: integer
              example: 142
            topics:
              type: object
              description: Кількість запитів по темах
              example:
                delivery: 34
                products: 28
                returns: 15
                payment: 12
                other: 53
    """
    data = get_chat_analytics()
    topics = {'delivery': 0, 'products': 0, 'returns': 0, 'payment': 0, 'other': 0}
    for row in data:
        msg = (row.get('user_message') or '').lower()
        if any(w in msg for w in ['delivery', 'shipping', 'доставка']):
            topics['delivery'] += 1
        elif any(w in msg for w in ['product', 'catalog', 'товар', 'каталог']):
            topics['products'] += 1
        elif any(w in msg for w in ['return', 'refund', 'повернення']):
            topics['returns'] += 1
        elif any(w in msg for w in ['pay', 'payment', 'оплата', 'оплатити']):
            topics['payment'] += 1
        else:
            topics['other'] += 1
    return jsonify({'total_messages': len(data), 'topics': topics})


# ─── CNN Predict ─────────────────────────────────────────────────────────────

_cnn_model = None
CNN_CLASS_NAMES = [
    'T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat',
    'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot'
]
CNN_CLASS_UA = [
    'Футболка', 'Штани', 'Светр/Пуловер', 'Сукня', 'Пальто',
    'Сандалі', 'Сорочка', 'Кросівки', 'Сумка', 'Черевики'
]

def get_cnn_model():
    global _cnn_model
    if _cnn_model is None:
        model_path = 'neural_network/models/best_model.keras'
        if not os.path.exists(model_path):
            return None
        try:
            import tensorflow as tf
            _cnn_model = tf.keras.models.load_model(model_path)
            logger.info("CNN model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load CNN model: {e}")
            return None
    return _cnn_model


@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Класифікувати зображення одягу через CNN
    ---
    tags:
      - products
    summary: Розпізнавання одягу на фото
    description: |
      Приймає зображення у форматі multipart/form-data або бінарний потік.
      Обробляє через CNN (Fashion MNIST, 10 класів) та повертає передбачений клас одягу.

      **Класи:** T-shirt, Trouser, Pullover, Dress, Coat, Sandal, Shirt, Sneaker, Bag, Ankle boot
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: image
        type: file
        required: true
        description: Зображення одягу (JPG, PNG, будь-який розмір — буде масштабовано до 28x28)
    responses:
      200:
        description: Результат класифікації
        schema:
          type: object
          properties:
            class:
              type: string
              example: T-shirt/top
            class_ua:
              type: string
              example: Футболка
            confidence:
              type: number
              format: float
              example: 0.9431
            confidence_pct:
              type: string
              example: "94.31%"
            top3:
              type: array
              description: Топ-3 класи за впевненістю
              items:
                type: object
                properties:
                  class:
                    type: string
                  class_ua:
                    type: string
                  confidence_pct:
                    type: string
            inference_time_ms:
              type: number
              example: 12.4
      400:
        description: Зображення не передано
        schema:
          $ref: '#/definitions/Error'
      503:
        description: Модель не завантажена (потрібно запустити train.py)
        schema:
          $ref: '#/definitions/Error'
    """
    import time

    # Get image bytes from request
    if 'image' in request.files:
        image_bytes = request.files['image'].read()
    elif request.data:
        image_bytes = request.data
    else:
        return jsonify({'error': 'No image provided. Send image as multipart "image" field or raw bytes.'}), 400

    model = get_cnn_model()
    if model is None:
        return jsonify({'error': 'CNN model not loaded. Please run neural_network/train.py first.'}), 503

    try:
        from neural_network.data.preprocess import preprocess_real_photo
        arr = preprocess_real_photo(image_bytes)

        start = time.time()
        predictions = model.predict(arr, verbose=0)[0]
        elapsed_ms = round((time.time() - start) * 1000, 2)

        top_idx = int(np.argmax(predictions))
        top3 = sorted(range(10), key=lambda i: predictions[i], reverse=True)[:3]

        return jsonify({
            'class': CNN_CLASS_NAMES[top_idx],
            'class_ua': CNN_CLASS_UA[top_idx],
            'confidence': float(predictions[top_idx]),
            'confidence_pct': f"{float(predictions[top_idx]) * 100:.2f}%",
            'top3': [
                {
                    'class': CNN_CLASS_NAMES[i],
                    'class_ua': CNN_CLASS_UA[i],
                    'confidence_pct': f"{float(predictions[i]) * 100:.2f}%"
                }
                for i in top3
            ],
            'inference_time_ms': elapsed_ms,
        })

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({'error': f'Image processing failed: {str(e)}'}), 400


if __name__ == '__main__':
    app.run(debug=Config.DEBUG, port=Config.PORT, host='0.0.0.0')