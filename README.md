# FashionAI Shop — Complete AI Project

A unified Python project covering 4 topics:
1. **Web Resource with AI Chatbot** — Flask + Anthropic Claude
2. **TelebotAPI Telegram Bot** — pyTelegramBotAPI
3. **Aiogram 3.0 Telegram Bot** — aiogram
4. **CNN Image Classification** — TensorFlow/Keras on Fashion MNIST

---

## Project Structure


```
ai-final-project/
├── requirements.txt
├── .env.example
├── web/                    # Frontend (HTML/CSS/JS)
├── backend/                # Flask API + AI chatbot
├── bot_telebot/            # TelebotAPI Telegram bot
├── bot_aiogram/            # Aiogram 3.0 Telegram bot
└── neural_network/         # CNN classifier (Fashion MNIST)
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

---

## Running Each Component

### Web Backend (Flask)
```bash
python backend/app.py
# Serves at http://localhost:5000
# Frontend at http://localhost:5000/ (serves web/ directory)
```

### TelebotAPI Bot
```bash
python bot_telebot/bot.py
```

### Aiogram Bot
```bash
python bot_aiogram/bot.py
```

### Train Neural Network
```bash
python neural_network/train.py
```

### Evaluate Neural Network
```bash
python neural_network/evaluate.py
```

### Run Predictions (demo)
```bash
python neural_network/predict.py
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `FLASK_SECRET_KEY` | Flask session secret |
| `ANTHROPIC_API_KEY` | Claude API key for web chatbot |
| `TELEBOT_TOKEN` | TelebotAPI bot token |
| `TELEBOT_ADMIN_IDS` | Comma-separated admin user IDs |
| `AIOGRAM_TOKEN` | Aiogram bot token |
| `AIOGRAM_ADMIN_IDS` | Comma-separated admin user IDs |
| `PAYMENT_PROVIDER_TOKEN` | Telegram payment provider token |

---

## Features

### Web + Chatbot
- Responsive fashion store website (4 pages)
- AI chatbot powered by Claude (demo mode if no API key)
- Product catalog loaded from SQLite via REST API
- Blog posts from database
- Contact form with validation
- FAQ accordion

### TelebotAPI Bot
- Product catalog browsing with inline keyboards
- Multi-step order flow with FSM
- Shopping cart (in-memory)
- Feedback collection
- Admin panel: add/remove products, view orders, view feedback

### Aiogram Bot
- Same features as TelebotAPI but using aiogram 3.0 patterns
- FSMContext for cart and order state
- Logging middleware
- Telegram Payments integration
- Async SQLite (aiosqlite)

### CNN Classifier
- Fashion MNIST (10 classes of clothing)
- CNN with 3 conv blocks + batch norm + dropout
- Data augmentation pipeline
- Training history plots
- Confusion matrix evaluation
- Single-image and batch prediction API