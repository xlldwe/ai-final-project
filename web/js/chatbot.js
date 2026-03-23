/**
 * FashionAI Shop - Chatbot Widget
 * Connects to Flask backend at /api/chat
 */

class ChatbotWidget {
  constructor() {
    this.isOpen = false;
    this.isLoading = false;
    this.apiUrl = 'http://localhost:5000/api/chat';
    this.storageKey = 'fashionai_chat_history';

    this.widget = null;
    this.toggleBtn = null;
    this.window = null;
    this.messagesContainer = null;
    this.input = null;
    this.sendBtn = null;

    this.init();
  }

  init() {
    this.createWidget();
    this.bindEvents();
    this.loadHistory();
    this.showWelcomeMessage();
  }

  createWidget() {
    // Main container
    this.widget = document.createElement('div');
    this.widget.id = 'chatbot-widget';

    this.widget.innerHTML = `
      <button id="chatbot-toggle" aria-label="Open chat assistant">
        <span>💬</span>
        <span class="badge"></span>
      </button>

      <div id="chatbot-window" role="dialog" aria-label="Chat with FashionAI Assistant">
        <div class="chatbot-header">
          <div class="chatbot-avatar">🤖</div>
          <div class="chatbot-header-info">
            <h4>FashionAI Assistant</h4>
            <span>Online • Ready to help</span>
          </div>
          <span class="chatbot-status-dot"></span>
          <button class="chatbot-close" id="chatbot-close" aria-label="Close chat">✕</button>
        </div>

        <div id="chatbot-messages" aria-live="polite"></div>

        <div class="chatbot-input-area">
          <textarea
            id="chatbot-input"
            placeholder="Ask about our products..."
            rows="1"
            aria-label="Type your message"
          ></textarea>
          <button id="chatbot-send" aria-label="Send message" disabled>➤</button>
        </div>
      </div>
    `;

    document.body.appendChild(this.widget);

    this.toggleBtn = document.getElementById('chatbot-toggle');
    this.window = document.getElementById('chatbot-window');
    this.messagesContainer = document.getElementById('chatbot-messages');
    this.input = document.getElementById('chatbot-input');
    this.sendBtn = document.getElementById('chatbot-send');
  }

  bindEvents() {
    // Toggle open/close
    this.toggleBtn.addEventListener('click', () => this.toggle());
    document.getElementById('chatbot-close').addEventListener('click', () => this.close());

    // Send on button click
    this.sendBtn.addEventListener('click', () => this.sendMessage());

    // Send on Enter (Shift+Enter for newline)
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!this.isLoading && this.input.value.trim()) {
          this.sendMessage();
        }
      }
    });

    // Enable/disable send button based on input
    this.input.addEventListener('input', () => {
      const hasText = this.input.value.trim().length > 0;
      this.sendBtn.disabled = !hasText || this.isLoading;
      // Auto-resize textarea
      this.input.style.height = 'auto';
      this.input.style.height = Math.min(this.input.scrollHeight, 100) + 'px';
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (this.isOpen &&
          !this.widget.contains(e.target) &&
          e.target !== this.toggleBtn) {
        // Don't auto-close; user experience is better keeping it open
      }
    });
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    this.isOpen = true;
    this.window.classList.add('open');
    this.toggleBtn.querySelector('span').textContent = '✕';
    this.input.focus();
    this.scrollToBottom();
  }

  close() {
    this.isOpen = false;
    this.window.classList.remove('open');
    this.toggleBtn.querySelector('span').textContent = '💬';
  }

  showWelcomeMessage() {
    const history = this.getHistory();
    if (history.length === 0) {
      this.displayMessage(
        "👋 Hello! Welcome to FashionAI Shop! I'm your AI shopping assistant.\n\nI can help you with:\n• Finding the perfect outfit\n• Product information & sizing\n• Shipping & returns\n• Order tracking\n\nHow can I help you today?",
        'bot'
      );
    }
  }

  async sendMessage() {
    const text = this.input.value.trim();
    if (!text || this.isLoading) return;

    // Display user message
    this.displayMessage(text, 'user');
    this.saveToHistory({ role: 'user', text, time: new Date().toISOString() });

    // Clear input
    this.input.value = '';
    this.input.style.height = 'auto';
    this.sendBtn.disabled = true;

    // Show typing
    this.isLoading = true;
    const typingId = this.showTypingIndicator();

    try {
      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ message: text }),
      });

      this.hideTypingIndicator(typingId);

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Server error: ${response.status}`);
      }

      const data = await response.json();
      const botResponse = data.response || 'Sorry, I could not process your request.';

      this.displayMessage(botResponse, 'bot');
      this.saveToHistory({ role: 'bot', text: botResponse, time: new Date().toISOString() });

    } catch (error) {
      this.hideTypingIndicator(typingId);
      console.error('Chatbot error:', error);

      let errorMsg = 'Sorry, I\'m having connection issues. Please try again or contact support@fashionai.shop';
      if (error.message.includes('fetch')) {
        errorMsg = 'Cannot connect to server. Make sure the backend is running on localhost:5000';
      }
      this.displayMessage(errorMsg, 'bot');
    } finally {
      this.isLoading = false;
      this.sendBtn.disabled = this.input.value.trim().length === 0;
    }
  }

  displayMessage(text, sender) {
    const messageEl = document.createElement('div');
    messageEl.className = `chat-message ${sender}`;

    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    let formattedText;
    if (sender === 'user') {
      // Escape HTML for user input (security)
      formattedText = this.escapeHtml(text).replace(/\n/g, '<br>');
    } else {
      // Bot messages: render HTML tags + replace newlines
      formattedText = text.replace(/\n/g, '<br>');
    }

    messageEl.innerHTML = `
      <div class="message-bubble">${formattedText}</div>
      <span class="message-time">${time}</span>
    `;

    this.messagesContainer.appendChild(messageEl);
    this.scrollToBottom();
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
  }

  showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const typingEl = document.createElement('div');
    typingEl.className = 'chat-message bot';
    typingEl.id = id;
    typingEl.innerHTML = `
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    `;
    this.messagesContainer.appendChild(typingEl);
    this.scrollToBottom();
    return id;
  }

  hideTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  scrollToBottom() {
    requestAnimationFrame(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    });
  }

  // Session storage for chat history
  getHistory() {
    try {
      return JSON.parse(sessionStorage.getItem(this.storageKey) || '[]');
    } catch {
      return [];
    }
  }

  saveToHistory(message) {
    try {
      const history = this.getHistory();
      history.push(message);
      // Keep last 50 messages
      const trimmed = history.slice(-50);
      sessionStorage.setItem(this.storageKey, JSON.stringify(trimmed));
    } catch (e) {
      console.warn('Could not save chat history:', e);
    }
  }

  loadHistory() {
    const history = this.getHistory();
    // Only restore last 10 messages on page load
    const recent = history.slice(-10);
    recent.forEach(msg => {
      if (msg.role && msg.text) {
        this.displayMessage(msg.text, msg.role);
      }
    });
  }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.chatbot = new ChatbotWidget();
});