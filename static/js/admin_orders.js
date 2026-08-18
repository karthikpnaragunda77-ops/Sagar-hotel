/**
 * Admin Live Orders Kanban Management JavaScript
 */

async function updateOrderStatus(orderId, newStatus) {
  try {
    const res = await fetch(`/admin/orders/update-status/${orderId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });

    const data = await res.json();
    if (res.ok && data.status === 'success') {
      // Reload page to refresh Kanban state cleanly or smoothly reload
      window.location.reload();
    } else {
      alert(data.message || 'Failed to update order status');
    }
  } catch (err) {
    console.error(err);
    alert('Network error while updating status.');
  }
}

// Auto-check for new orders every 15 seconds
setInterval(() => {
  // If user is not currently interacting with an input or modal, reload orders board
  const isInputFocused = document.activeElement && (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA');
  if (!isInputFocused) {
    // Silent check or reload
    fetch('/admin/dashboard') // keeps session alive
      .catch(e => {});
  }
}, 15000);
