import random
from datetime import datetime
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from db import get_db, serialize_doc, serialize_docs

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
@user_bp.route('/menu')
def menu_view():
    db = get_db()
    
    # Extract filter parameters
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    
    # Query MongoDB for enabled dishes
    query = {"is_available": True}
    if category != 'all' and category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
        
    dishes = serialize_docs(db.menu_items.find(query).sort("category", 1))
    
    # Get distinct categories from active dishes
    categories = db.menu_items.distinct("category")
    
    # Get table list for manual table selection modal if needed
    all_tables = serialize_docs(db.tables.find({}).sort("table_number", 1))
    
    current_table = session.get('table_number')
    
    return render_template(
        'user/menu.html',
        dishes=dishes,
        categories=categories,
        selected_category=category,
        search_query=search,
        current_table=current_table,
        all_tables=all_tables
    )

@user_bp.route('/table/<int:table_number>')
def table_landing(table_number):
    """Entry point when customer scans Table QR Code."""
    db = get_db()
    table = db.tables.find_one({"table_number": table_number})
    
    session['table_number'] = table_number
    
    if table:
        # Mark table occupied or active
        db.tables.update_one(
            {"table_number": table_number},
            {"$set": {"last_scanned_at": datetime.utcnow()}}
        )
    
    return render_template('user/table_landing.html', table_number=table_number, table=serialize_doc(table))

@user_bp.route('/set-table', methods=['POST'])
def set_table():
    table_num = request.form.get('table_number', type=int)
    if table_num:
        session['table_number'] = table_num
        flash(f'Table #{table_num} selected! Your order will be served directly to your table.', 'success')
    return redirect(request.referrer or url_for('user.menu_view'))

@user_bp.route('/clear-table')
def clear_table():
    session.pop('table_number', None)
    flash('Table selection cleared.', 'info')
    return redirect(url_for('user.menu_view'))

@user_bp.route('/api/menu')
def api_menu():
    """Returns live menu JSON for instant client-side reactivity."""
    db = get_db()
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    
    query = {"is_available": True}
    if category != 'all' and category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
        
    dishes = serialize_docs(db.menu_items.find(query).sort("name", 1))
    return jsonify({"status": "success", "dishes": dishes})

@user_bp.route('/cart')
def cart_view():
    db = get_db()
    current_table = session.get('table_number')
    all_tables = serialize_docs(db.tables.find({}).sort("table_number", 1))
    return render_template('user/cart.html', current_table=current_table, all_tables=all_tables)

@user_bp.route('/api/order/place', methods=['POST'])
def place_order():
    """Places customer order directly into MongoDB 'orders' collection."""
    data = request.get_json() or {}
    
    items = data.get('items', [])
    table_number = data.get('table_number') or session.get('table_number')
    customer_name = data.get('customer_name') or session.get('user_name', 'Guest Diner')
    customer_phone = data.get('customer_phone') or session.get('user_phone', '')
    special_notes = data.get('special_instructions', '').strip()
    
    if not items:
        return jsonify({'status': 'error', 'message': 'Your cart is empty. Please add delicious breakfast items!'}), 400
        
    if not table_number:
        return jsonify({'status': 'error', 'message': 'Please select your Table Number before placing your order.'}), 400

    try:
        table_number = int(table_number)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid table number format.'}), 400

    db = get_db()
    
    # Validate each item from MongoDB to guarantee pricing integrity
    validated_items = []
    subtotal = 0.0
    max_prep_time = 10
    
    for item in items:
        item_id_str = item.get('item_id') or item.get('id')
        qty = int(item.get('quantity', 1))
        if qty <= 0:
            continue
            
        try:
            db_item = db.menu_items.find_one({'_id': ObjectId(item_id_str)})
        except Exception:
            db_item = db.menu_items.find_one({'name': item.get('name')})
            
        if not db_item:
            continue
            
        price = float(db_item.get('price', 0))
        item_subtotal = round(price * qty, 2)
        subtotal += item_subtotal
        
        prep_time = db_item.get('prep_time_mins', 10)
        if prep_time > max_prep_time:
            max_prep_time = prep_time
            
        validated_items.append({
            'item_id': str(db_item['_id']),
            'name': db_item.get('name'),
            'price': price,
            'quantity': qty,
            'subtotal': item_subtotal,
            'image_url': db_item.get('image_url', ''),
            'notes': item.get('notes', '')
        })

    if not validated_items:
        return jsonify({'status': 'error', 'message': 'No valid menu items found in your order.'}), 400

    # 5% GST tax calculation
    tax = round(subtotal * 0.05, 2)
    total_amount = round(subtotal + tax, 2)
    
    # Generate human readable order number e.g. SBH-7821
    order_num = f"SBH-{random.randint(1000, 9999)}"
    
    order_doc = {
        'order_number': order_num,
        'user_id': session.get('user_id'),
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'table_number': table_number,
        'items': validated_items,
        'item_count': sum(i['quantity'] for i in validated_items),
        'subtotal': subtotal,
        'tax': tax,
        'total_amount': total_amount,
        'status': 'Placed',  # Placed -> Preparing -> Ready -> Served
        'status_history': [
            {'status': 'Placed', 'timestamp': datetime.utcnow(), 'note': 'Order received by hotel kitchen'}
        ],
        'estimated_prep_time_mins': max_prep_time,
        'notes': special_notes,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    result = db.orders.insert_one(order_doc)
    order_id_str = str(result.inserted_id)
    
    # Update table status in MongoDB to occupied
    db.tables.update_one(
        {'table_number': table_number},
        {'$set': {'status': 'occupied', 'current_order_id': order_id_str, 'updated_at': datetime.utcnow()}}
    )
    
    # Persist active table in session
    session['table_number'] = table_number
    session['last_order_id'] = order_id_str
    
    return jsonify({
        'status': 'success',
        'message': f'Order #{order_num} placed successfully!',
        'order_id': order_id_str,
        'order_number': order_num,
        'redirect_url': url_for('user.order_status_view', order_id=order_id_str)
    })

@user_bp.route('/order/status/<order_id>')
def order_status_view(order_id):
    db = get_db()
    try:
        order = db.orders.find_one({'_id': ObjectId(order_id)})
    except Exception:
        order = None
        
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('user.menu_view'))
        
    return render_template('user/order_status.html', order=serialize_doc(order))

@user_bp.route('/api/order/status/<order_id>')
def api_order_status(order_id):
    """Real-time polling endpoint for live order progress stepper."""
    db = get_db()
    try:
        order = db.orders.find_one({'_id': ObjectId(order_id)})
    except Exception:
        return jsonify({'status': 'error', 'message': 'Invalid order ID'}), 404
        
    if not order:
        return jsonify({'status': 'error', 'message': 'Order not found'}), 404
        
    # Calculate elapsed minutes
    created_at = order.get('created_at')
    elapsed_mins = 0
    if isinstance(created_at, datetime):
        elapsed_mins = int((datetime.utcnow() - created_at).total_seconds() / 60)
        
    return jsonify({
        'status': 'success',
        'order_status': order.get('status', 'Placed'),
        'order_number': order.get('order_number'),
        'table_number': order.get('table_number'),
        'estimated_prep_time_mins': order.get('estimated_prep_time_mins', 12),
        'elapsed_mins': elapsed_mins,
        'updated_at': order.get('updated_at').strftime('%H:%M:%S') if isinstance(order.get('updated_at'), datetime) else ''
    })

@user_bp.route('/orders')
def order_history_view():
    """View customer order history."""
    db = get_db()
    user_id = session.get('user_id')
    
    query = {}
    if user_id:
        query = {'user_id': user_id}
    elif session.get('user_phone'):
        query = {'customer_phone': session.get('user_phone')}
    elif session.get('last_order_id'):
        try:
            query = {'_id': ObjectId(session.get('last_order_id'))}
        except Exception:
            pass
            
    orders = serialize_docs(db.orders.find(query).sort('created_at', -1).limit(25))
    return render_template('user/order_history.html', orders=orders)
