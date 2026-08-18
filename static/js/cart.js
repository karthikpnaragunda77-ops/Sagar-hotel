/**
 * Smart Breakfast Hotel - Client-Side Cart Manager
 */

const Cart = {
  KEY: 'sbh_cart_v1',

  getItems() {
    try {
      return JSON.parse(localStorage.getItem(this.KEY)) || [];
    } catch (e) {
      return [];
    }
  },

  save(items) {
    localStorage.setItem(this.KEY, JSON.stringify(items));
    this.updateUI();
  },

  addItem(dish) {
    let items = this.getItems();
    const existing = items.find(i => i.id === dish.id || i.name === dish.name);
    if (existing) {
      existing.quantity += 1;
    } else {
      items.push({
        id: dish.id,
        name: dish.name,
        price: parseFloat(dish.price),
        quantity: 1,
        image_url: dish.image_url || '',
        category: dish.category || '',
        prep_time_mins: dish.prep_time_mins || 10,
        notes: ''
      });
    }
    this.save(items);
    this.showToast(`Added "${dish.name}" to cart!`);
  },

  updateQuantity(id, delta) {
    let items = this.getItems();
    const item = items.find(i => i.id === id);
    if (!item) return;

    item.quantity += delta;
    if (item.quantity <= 0) {
      items = items.filter(i => i.id !== id);
    }
    this.save(items);
  },

  removeItem(id) {
    let items = this.getItems().filter(i => i.id !== id);
    this.save(items);
    this.showToast('Item removed from cart');
  },

  clear() {
    localStorage.removeItem(this.KEY);
    this.updateUI();
  },

  getCount() {
    return this.getItems().reduce((sum, item) => sum + item.quantity, 0);
  },

  getSubtotal() {
    return this.getItems().reduce((sum, item) => sum + (item.price * item.quantity), 0);
  },

  updateUI() {
    const count = this.getCount();
    const subtotal = this.getSubtotal();
    const tax = Math.round(subtotal * 0 * 100) / 100;
    const total = Math.round((subtotal + tax) * 100) / 100;

    // 1. Update Header Cart Badges
    document.querySelectorAll('.cart-badge-count').forEach(el => {
      el.textContent = count;
      el.style.display = count > 0 ? 'inline-flex' : 'none';
    });

    // 2. Update Floating Cart Bar
    const floatingBar = document.getElementById('floating-cart-bar');
    if (floatingBar) {
      if (count > 0 && !window.location.pathname.includes('/cart')) {
        floatingBar.classList.add('visible');
        const countText = document.getElementById('floating-cart-count');
        const totalText = document.getElementById('floating-cart-total');
        if (countText) countText.textContent = `${count} ${count === 1 ? 'item' : 'items'}`;
        if (totalText) totalText.textContent = `₹${total.toFixed(2)}`;
      } else {
        floatingBar.classList.remove('visible');
      }
    }

    // 3. Update Cart Page table if on /cart
    const cartItemsContainer = document.getElementById('cart-items-tbody');
    const emptyState = document.getElementById('cart-empty-state');
    const cartContent = document.getElementById('cart-content-wrapper');

    if (cartItemsContainer) {
      const items = this.getItems();
      if (items.length === 0) {
        if (emptyState) emptyState.style.display = 'block';
        if (cartContent) cartContent.style.display = 'none';
      } else {
        if (emptyState) emptyState.style.display = 'none';
        if (cartContent) cartContent.style.display = 'grid';

        cartItemsContainer.innerHTML = items.map(item => `
          <tr>
            <td>
              <div class="cart-item-info">
                <img src="${item.image_url || '/static/images/dish-placeholder.jpg'}" alt="${item.name}" class="cart-item-thumb" onerror="this.src='https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=150&q=80'">
                <div>
                  <div class="cart-item-name">${item.name}</div>
                  <div class="cart-item-price">₹${item.price.toFixed(2)} each</div>
                </div>
              </div>
            </td>
            <td>
              <div class="qty-controller">
                <button type="button" class="qty-btn" onclick="Cart.updateQuantity('${item.id}', -1)">−</button>
                <span class="qty-value">${item.quantity}</span>
                <button type="button" class="qty-btn" onclick="Cart.updateQuantity('${item.id}', 1)">+</button>
              </div>
            </td>
            <td style="font-weight: 700;">₹${(item.price * item.quantity).toFixed(2)}</td>
            <td style="text-align: right;">
              <button type="button" class="btn btn-sm btn-outline" style="color: #DC2626; border-color: #FCA5A5;" onclick="Cart.removeItem('${item.id}')" title="Remove item">
                ✕
              </button>
            </td>
          </tr>
        `).join('');

        // Summary values
        const subtotalEl = document.getElementById('cart-subtotal');
        const taxEl = document.getElementById('cart-tax');
        const totalEl = document.getElementById('cart-total');

        if (subtotalEl) subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
        if (taxEl) taxEl.textContent = `₹${tax.toFixed(2)}`;
        if (totalEl) totalEl.textContent = `₹${total.toFixed(2)}`;
      }
    }
  },

  async placeOrder() {
    const items = this.getItems();
    if (items.length === 0) {
      alert('Your cart is empty.');
      return;
    }

    const tableInput = document.getElementById('order-table-number');
    const nameInput = document.getElementById('order-customer-name');
    const phoneInput = document.getElementById('order-customer-phone');
    const notesInput = document.getElementById('order-special-notes');
    const submitBtn = document.getElementById('btn-place-order');

    const tableNumber = tableInput ? tableInput.value : '';
    if (!tableNumber) {
      alert('Please select or confirm your Table Number.');
      if (tableInput) tableInput.focus();
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = 'Sending to Kitchen...';
    }

    try {
      const response = await fetch('/api/order/place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table_number: tableNumber,
          customer_name: nameInput ? nameInput.value : '',
          customer_phone: phoneInput ? phoneInput.value : '',
          special_instructions: notesInput ? notesInput.value : '',
          items: items
        })
      });

      const resData = await response.json();

      if (response.ok && resData.status === 'success') {
        this.clear();
        window.location.href = resData.redirect_url;
      } else {
        alert(resData.message || 'Failed to place order. Please try again.');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = 'Place Breakfast Order ⚡';
        }
      }
    } catch (err) {
      console.error(err);
      alert('Network error while connecting to hotel kitchen. Please retry.');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Place Breakfast Order ⚡';
      }
    }
  },

  showToast(message) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>
      <span>${message}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(20px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  Cart.updateUI();
});
