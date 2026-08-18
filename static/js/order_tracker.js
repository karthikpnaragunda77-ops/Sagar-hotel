/**
 * Live Order Status Polling & Stepper Animation
 */

class OrderTracker {
  constructor(orderId, initialStatus) {
    this.orderId = orderId;
    this.currentStatus = initialStatus;
    this.pollInterval = null;
    this.statusMap = {
      'Placed': 1,
      'Preparing': 2,
      'Ready': 3,
      'Served': 4,
      'Cancelled': 0
    };

    this.init();
  }

  init() {
    this.updateStepperUI(this.currentStatus);
    // Start live polling every 3.5 seconds if order is not completed
    if (this.currentStatus !== 'Served' && this.currentStatus !== 'Cancelled') {
      this.pollInterval = setInterval(() => this.checkStatus(), 3500);
    }
  }

  async checkStatus() {
    try {
      const res = await fetch(`/api/order/status/${this.orderId}`);
      if (!res.ok) return;

      const data = await res.json();
      if (data.status === 'success' && data.order_status) {
        if (data.order_status !== this.currentStatus) {
          this.currentStatus = data.order_status;
          this.updateStepperUI(this.currentStatus);
          this.showStatusNotification(this.currentStatus);
        }

        // Stop polling if served or cancelled
        if (this.currentStatus === 'Served' || this.currentStatus === 'Cancelled') {
          clearInterval(this.pollInterval);
        }
      }
    } catch (e) {
      console.warn('Live order polling error:', e);
    }
  }

  updateStepperUI(status) {
    const stepNumber = this.statusMap[status] || 1;
    const progressEl = document.getElementById('stepper-progress-bar');
    const badgeEl = document.getElementById('order-status-badge');
    const statusMsgEl = document.getElementById('order-status-message');

    // Update Progress line width / height
    if (progressEl) {
      const percentage = status === 'Cancelled' ? 0 : ((stepNumber - 1) / 3) * 100;
      progressEl.style.width = `${percentage}%`;
      if (window.innerWidth <= 840) {
        progressEl.style.height = `${percentage}%`;
      }
    }

    // Update Step items
    const steps = ['Placed', 'Preparing', 'Ready', 'Served'];
    steps.forEach((st, idx) => {
      const stepIdx = idx + 1;
      const stepEl = document.getElementById(`step-${st.toLowerCase()}`);
      if (!stepEl) return;

      stepEl.classList.remove('active', 'completed');

      if (status === 'Cancelled') {
        // do nothing
      } else if (stepIdx < stepNumber) {
        stepEl.classList.add('completed');
      } else if (stepIdx === stepNumber) {
        stepEl.classList.add('active');
      }
    });

    // Update Status Badge
    if (badgeEl) {
      badgeEl.className = `badge badge-status-${status.toLowerCase()}`;
      badgeEl.textContent = status;
    }

    // Dynamic encouraging message based on breakfast status
    if (statusMsgEl) {
      if (status === 'Placed') {
        statusMsgEl.innerHTML = '<strong>Order Received!</strong> The chef is queueing your fresh breakfast.';
      } else if (status === 'Preparing') {
        statusMsgEl.innerHTML = '<strong>Cooking in Kitchen!</strong> Your crisp Dosas & steaming Idlis are being prepared.';
      } else if (status === 'Ready') {
        statusMsgEl.innerHTML = '<strong>Order Ready!</strong> Your hot breakfast is plated and on its way to your table.';
      } else if (status === 'Served') {
        statusMsgEl.innerHTML = '<strong>Served & Enjoy!</strong> Delicious breakfast served at your table. Bon Appétit!';
      } else if (status === 'Cancelled') {
        statusMsgEl.innerHTML = '<strong>Order Cancelled.</strong> Please contact the front desk for assistance.';
      }
    }
  }

  showStatusNotification(status) {
    if (typeof Cart !== 'undefined' && Cart.showToast) {
      Cart.showToast(`Order status updated to: ${status}`);
    }
  }
}
