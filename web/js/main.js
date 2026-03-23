/**
 * FashionAI Shop - Main JavaScript
 * Handles products, blog, contact form, FAQ, navigation
 */

const API_BASE = 'http://localhost:5000/api';

// Category emoji map
const CATEGORY_EMOJI = {
  'T-Shirts': '👕',
  'Jeans': '👖',
  'Dresses': '👗',
  'Jackets': '🧥',
  'Shoes': '👟',
  'Sneakers': '👟',
  'Sweaters': '🧶',
  'Pants': '👖',
  'Shirts': '👔',
  'Bags': '👜',
  'default': '🛍️',
};

const BLOG_EMOJI = ['📝', '✨', '🌿', '👗', '💡', '🌸'];

// ─── Navigation ───────────────────────────────────────────────────────────────

function initNavigation() {
  const hamburger = document.querySelector('.hamburger');
  const navLinks = document.querySelector('.nav-links');

  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('open');
      navLinks.classList.toggle('open');
    });

    // Close nav on link click
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        hamburger.classList.remove('open');
        navLinks.classList.remove('open');
      });
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
        hamburger.classList.remove('open');
        navLinks.classList.remove('open');
      }
    });
  }

  // Mark active nav link
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href') || '';
    if (href === currentPath || (currentPath === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });
}

// ─── Products ─────────────────────────────────────────────────────────────────

async function loadProducts() {
  const grid = document.getElementById('products-grid');
  if (!grid) return;

  grid.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <p>Loading products...</p>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/products`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const products = await res.json();

    if (!products.length) {
      grid.innerHTML = '<p class="loading">No products available.</p>';
      return;
    }

    grid.innerHTML = '';
    products.forEach(product => {
      grid.appendChild(createProductCard(product));
    });

  } catch (err) {
    console.error('Failed to load products:', err);
    grid.innerHTML = `
      <div class="loading">
        <p>Could not load products. Make sure the backend is running.</p>
        <button class="btn btn-primary mt-2" onclick="loadProducts()">Retry</button>
      </div>
    `;
  }
}

function createProductCard(product) {
  const card = document.createElement('div');
  card.className = 'product-card';

  const emoji = CATEGORY_EMOJI[product.category] || CATEGORY_EMOJI['default'];
  const truncDesc = product.description
    ? (product.description.length > 80 ? product.description.slice(0, 80) + '...' : product.description)
    : '';

  card.innerHTML = `
    <div class="product-image">
      ${product.image_url
        ? `<img src="${escHtml(product.image_url)}" alt="${escHtml(product.name)}" loading="lazy">`
        : `<span>${emoji}</span>`}
      <span class="product-badge">${escHtml(product.category)}</span>
    </div>
    <div class="product-body">
      <div class="product-category">${escHtml(product.category)}</div>
      <div class="product-name">${escHtml(product.name)}</div>
      <div class="product-description">${escHtml(truncDesc)}</div>
      <div class="product-footer">
        <div class="product-price">
          ${product.price.toFixed(2)}<span class="currency">UAH</span>
        </div>
        <button class="btn-cart" onclick="addToCart(${product.id}, '${escHtml(product.name)}', ${product.price})">
          🛒 Add
        </button>
      </div>
    </div>
  `;

  return card;
}

// Simple cart stored in sessionStorage
function addToCart(id, name, price) {
  try {
    const cart = JSON.parse(sessionStorage.getItem('cart') || '{}');
    if (cart[id]) {
      cart[id].quantity += 1;
    } else {
      cart[id] = { id, name, price, quantity: 1 };
    }
    sessionStorage.setItem('cart', JSON.stringify(cart));
    showToast(`✅ ${name} added to cart!`);
  } catch (e) {
    console.warn('Cart error:', e);
  }
}

function showToast(message) {
  let toast = document.getElementById('toast-notification');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast-notification';
    toast.style.cssText = `
      position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
      background: #2d2d2d; color: white; padding: 0.8rem 1.5rem;
      border-radius: 50px; font-size: 0.9rem; font-weight: 600;
      z-index: 9000; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      transition: all 0.3s ease; opacity: 0;
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.opacity = '1';
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => { toast.style.opacity = '0'; }, 2500);
}

// ─── Blog ─────────────────────────────────────────────────────────────────────

async function loadBlogPosts() {
  const grid = document.getElementById('blog-grid');
  if (!grid) return;

  grid.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <p>Loading articles...</p>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/blog`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const posts = await res.json();

    if (!posts.length) {
      grid.innerHTML = '<p class="loading">No blog posts yet.</p>';
      return;
    }

    grid.innerHTML = '';
    posts.forEach((post, idx) => {
      grid.appendChild(createBlogCard(post, idx));
    });

  } catch (err) {
    console.error('Failed to load blog posts:', err);
    grid.innerHTML = `
      <div class="loading">
        <p>Could not load blog posts. Make sure the backend is running.</p>
        <button class="btn btn-primary mt-2" onclick="loadBlogPosts()">Retry</button>
      </div>
    `;
  }
}

function createBlogCard(post, idx) {
  const card = document.createElement('div');
  card.className = 'blog-card';

  const emoji = BLOG_EMOJI[idx % BLOG_EMOJI.length];
  const date = post.created_at
    ? new Date(post.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    : 'Recent';
  const excerpt = post.content.length > 160 ? post.content.slice(0, 160) + '...' : post.content;

  card.innerHTML = `
    <div class="blog-card-image">${emoji}</div>
    <div class="blog-card-body">
      <div class="blog-meta">
        <span class="blog-author">✍️ ${escHtml(post.author || 'Admin')}</span>
        <span class="blog-date">📅 ${date}</span>
      </div>
      <h3>${escHtml(post.title)}</h3>
      <p>${escHtml(excerpt)}</p>
      <a href="#" class="btn-read-more" onclick="return false;">Read More</a>
    </div>
  `;

  return card;
}

// ─── Contact Form ─────────────────────────────────────────────────────────────

function handleContactForm() {
  const form = document.getElementById('contact-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Clear previous errors
    form.querySelectorAll('.form-error').forEach(el => el.style.display = 'none');
    form.querySelectorAll('input, textarea').forEach(el => el.classList.remove('error'));

    const name = form.querySelector('#contact-name')?.value.trim() || '';
    const email = form.querySelector('#contact-email')?.value.trim() || '';
    const message = form.querySelector('#contact-message')?.value.trim() || '';

    let valid = true;

    if (name.length < 2) {
      showFieldError('name-error', 'Please enter your name (at least 2 characters).');
      form.querySelector('#contact-name')?.classList.add('error');
      valid = false;
    }

    if (!email.includes('@') || email.length < 5) {
      showFieldError('email-error', 'Please enter a valid email address.');
      form.querySelector('#contact-email')?.classList.add('error');
      valid = false;
    }

    if (message.length < 10) {
      showFieldError('message-error', 'Please enter a message (at least 10 characters).');
      form.querySelector('#contact-message')?.classList.add('error');
      valid = false;
    }

    if (!valid) return;

    const submitBtn = form.querySelector('.btn-submit');
    const successEl = document.getElementById('form-success');
    const originalText = submitBtn.textContent;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';

    try {
      const res = await fetch(`${API_BASE}/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, message }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        form.reset();
        if (successEl) {
          successEl.style.display = 'block';
          successEl.textContent = data.message || 'Your message has been sent!';
          setTimeout(() => { successEl.style.display = 'none'; }, 5000);
        }
      } else {
        throw new Error(data.error || 'Failed to send message.');
      }
    } catch (err) {
      console.error('Contact form error:', err);
      alert('Could not send message. Please try again or email us directly at support@fashionai.shop');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  });
}

function showFieldError(id, message) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent = message;
    el.style.display = 'block';
  }
}

// ─── FAQ Accordion ────────────────────────────────────────────────────────────

function initFaqAccordion() {
  const faqItems = document.querySelectorAll('.faq-item');

  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    if (!question) return;

    question.addEventListener('click', () => {
      const isActive = item.classList.contains('active');

      // Close all
      faqItems.forEach(fi => fi.classList.remove('active'));

      // Open clicked if it was not active
      if (!isActive) {
        item.classList.add('active');
      }
    });
  });
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── Initialize ───────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initFaqAccordion();
  loadProducts();
  loadBlogPosts();
  handleContactForm();
});