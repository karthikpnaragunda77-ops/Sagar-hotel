/**
 * Admin Menu Management JavaScript
 */

function toggleDishAvailability(dishId, checkbox) {
  fetch(`/admin/menu/toggle/${dishId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      const statusLabel = document.getElementById(`status-label-${dishId}`);
      if (statusLabel) {
        statusLabel.textContent = data.is_available ? 'Available' : 'Disabled';
        statusLabel.className = data.is_available ? 'badge badge-veg' : 'badge badge-status-cancelled';
      }
    } else {
      alert('Error updating status: ' + data.message);
      checkbox.checked = !checkbox.checked;
    }
  })
  .catch(err => {
    console.error(err);
    alert('Failed to connect to server.');
    checkbox.checked = !checkbox.checked;
  });
}

function openEditDishModal(dish) {
  const modal = document.getElementById('edit-dish-modal');
  const form = document.getElementById('edit-dish-form');
  
  if (!modal || !form) return;

  form.action = `/admin/menu/edit/${dish.id || dish._id}`;
  
  document.getElementById('edit-dish-name').value = dish.name || '';
  document.getElementById('edit-dish-category').value = dish.category || 'South Indian';
  document.getElementById('edit-dish-price').value = dish.price || '';
  document.getElementById('edit-dish-prep-time').value = dish.prep_time_mins || 10;
  document.getElementById('edit-dish-badge').value = dish.badge || '';
  document.getElementById('edit-dish-description').value = dish.description || '';
  document.getElementById('edit-dish-image-url').value = dish.image_url || '';
  document.getElementById('edit-dish-veg').checked = !!dish.is_veg;
  document.getElementById('edit-dish-available').checked = dish.is_available !== false;

  modal.classList.add('active');
}

function closeEditModal() {
  const modal = document.getElementById('edit-dish-modal');
  if (modal) modal.classList.remove('active');
}

function openAddModal() {
  const modal = document.getElementById('add-dish-modal');
  if (modal) modal.classList.add('active');
}

function closeAddModal() {
  const modal = document.getElementById('add-dish-modal');
  if (modal) modal.classList.remove('active');
}
