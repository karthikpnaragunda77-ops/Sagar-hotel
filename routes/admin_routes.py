import os
from datetime import datetime, timedelta
from bson import ObjectId
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app

from config import Config
from db import get_db, serialize_doc, serialize_docs
from routes.auth_routes import admin_required
from seed import generate_table_qr

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# ================= DASHBOARD =================

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    db = get_db()
    
    # 1. Total Menu Items
    total_dishes = db.menu_items.count_documents({})
    available_dishes = db.menu_items.count_documents({'is_available': True})
    
    # 2. Orders Stats
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_orders_count = db.orders.count_documents({'created_at': {'$gte': today_start}})
    
    # Active orders (not yet Served or Cancelled)
    active_orders_count = db.orders.count_documents({'status': {'$in': ['Placed', 'Preparing', 'Ready']}})
    
    # Today's Revenue
    pipeline_today_rev = [
        {'$match': {'created_at': {'$gte': today_start}, 'status': {'$ne': 'Cancelled'}}},
        {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
    ]
    today_rev_res = list(db.orders.aggregate(pipeline_today_rev))
    today_revenue = round(today_rev_res[0]['total'], 2) if today_rev_res else 0.0

    # Total Lifetime Revenue
    pipeline_total_rev = [
        {'$match': {'status': {'$ne': 'Cancelled'}}},
        {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
    ]
    total_rev_res = list(db.orders.aggregate(pipeline_total_rev))
    total_revenue = round(total_rev_res[0]['total'], 2) if total_rev_res else 0.0
    
    # Tables stats
    total_tables = db.tables.count_documents({})
    occupied_tables = db.tables.count_documents({'status': 'occupied'})
    
    # Recent 10 Orders
    recent_orders = serialize_docs(db.orders.find({}).sort('created_at', -1).limit(10))
    
    # Top 5 Selling Dishes
    pipeline_top_dishes = [
        {'$unwind': '$items'},
        {'$match': {'status': {'$ne': 'Cancelled'}}},
        {'$group': {
            '_id': '$items.name',
            'total_qty': {'$sum': '$items.quantity'},
            'total_sales': {'$sum': '$items.subtotal'}
        }},
        {'$sort': {'total_qty': -1}},
        {'$limit': 5}
    ]
    top_dishes = list(db.orders.aggregate(pipeline_top_dishes))
    
    return render_template(
        'admin/dashboard.html',
        total_dishes=total_dishes,
        available_dishes=available_dishes,
        today_orders_count=today_orders_count,
        active_orders_count=active_orders_count,
        today_revenue=today_revenue,
        total_revenue=total_revenue,
        total_tables=total_tables,
        occupied_tables=occupied_tables,
        recent_orders=recent_orders,
        top_dishes=top_dishes
    )


# ================= MENU MANAGEMENT =================

@admin_bp.route('/menu')
@admin_required
def menu_management():
    db = get_db()
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    
    query = {}
    if category != 'all' and category:
        query['category'] = category
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]
        
    dishes = serialize_docs(db.menu_items.find(query).sort('created_at', -1))
    categories = db.menu_items.distinct('category')
    
    return render_template(
        'admin/menu_management.html',
        dishes=dishes,
        categories=categories,
        selected_category=category,
        search_query=search
    )

@admin_bp.route('/menu/add', methods=['POST'])
@admin_required
def add_dish():
    db = get_db()
    
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    price = request.form.get('price', type=float)
    prep_time = request.form.get('prep_time_mins', type=int) or 10
    description = request.form.get('description', '').strip()
    is_veg = request.form.get('is_veg') == 'on' or request.form.get('is_veg') == 'true'
    badge = request.form.get('badge', '').strip()
    image_url = request.form.get('image_url', '').strip()
    
    if not name or price is None or not category:
        flash('Dish Name, Price, and Category are required.', 'danger')
        return redirect(url_for('admin.menu_management'))
        
    # Check for file upload
    file = request.files.get('image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        image_url = f"/static/uploads/{filename}"
    elif not image_url:
        # High quality default breakfast placeholder
        image_url = "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80"
        
    dish_doc = {
        'name': name,
        'category': category,
        'price': price,
        'prep_time_mins': prep_time,
        'description': description,
        'is_veg': is_veg,
        'is_available': True,
        'badge': badge,
        'image_url': image_url,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    db.menu_items.insert_one(dish_doc)
    flash(f"Dish '{name}' added successfully! It is now live on the customer menu.", 'success')
    return redirect(url_for('admin.menu_management'))

@admin_bp.route('/menu/edit/<dish_id>', methods=['POST'])
@admin_required
def edit_dish(dish_id):
    db = get_db()
    try:
        obj_id = ObjectId(dish_id)
    except Exception:
        flash('Invalid Dish ID.', 'danger')
        return redirect(url_for('admin.menu_management'))
        
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    price = request.form.get('price', type=float)
    prep_time = request.form.get('prep_time_mins', type=int) or 10
    description = request.form.get('description', '').strip()
    is_veg = request.form.get('is_veg') == 'on' or request.form.get('is_veg') == 'true'
    is_available = request.form.get('is_available') == 'on' or request.form.get('is_available') == 'true'
    badge = request.form.get('badge', '').strip()
    image_url = request.form.get('image_url', '').strip()
    
    update_data = {
        'name': name,
        'category': category,
        'price': price,
        'prep_time_mins': prep_time,
        'description': description,
        'is_veg': is_veg,
        'is_available': is_available,
        'badge': badge,
        'updated_at': datetime.utcnow()
    }
    
    # Check for file upload
    file = request.files.get('image_file')
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        update_data['image_url'] = f"/static/uploads/{filename}"
    elif image_url:
        update_data['image_url'] = image_url

    db.menu_items.update_one({'_id': obj_id}, {'$set': update_data})
    flash(f"Dish '{name}' updated successfully.", 'success')
    return redirect(url_for('admin.menu_management'))

@admin_bp.route('/menu/toggle/<dish_id>', methods=['POST'])
@admin_required
def toggle_dish(dish_id):
    """Toggle dish availability."""
    db = get_db()
    try:
        obj_id = ObjectId(dish_id)
        dish = db.menu_items.find_one({'_id': obj_id})
        if not dish:
            return jsonify({'status': 'error', 'message': 'Dish not found'}), 404
            
        new_status = not dish.get('is_available', True)
        db.menu_items.update_one({'_id': obj_id}, {'$set': {'is_available': new_status, 'updated_at': datetime.utcnow()}})
        
        return jsonify({
            'status': 'success',
            'is_available': new_status,
            'message': f"'{dish.get('name')}' is now {'Available' if new_status else 'Disabled / Out of Stock'}"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@admin_bp.route('/menu/delete/<dish_id>', methods=['POST'])
@admin_required
def delete_dish(dish_id):
    db = get_db()
    try:
        obj_id = ObjectId(dish_id)
        dish = db.menu_items.find_one({'_id': obj_id})
        db.menu_items.delete_one({'_id': obj_id})
        flash(f"Dish '{dish.get('name') if dish else 'item'}' deleted from MongoDB.", 'info')
    except Exception as e:
        flash(f"Error deleting dish: {e}", 'danger')
    return redirect(url_for('admin.menu_management'))


# ================= ORDERS & KITCHEN BOARD =================

@admin_bp.route('/orders')
@admin_required
def orders_board():
    db = get_db()
    
    status_filter = request.args.get('status', 'all')
    table_filter = request.args.get('table', type=int)
    
    query = {}
    if status_filter != 'all' and status_filter:
        query['status'] = status_filter
    if table_filter:
        query['table_number'] = table_filter
        
    all_orders = serialize_docs(db.orders.find(query).sort('created_at', -1).limit(50))
    
    # Categorize orders for Kanban view
    placed_orders = [o for o in all_orders if o.get('status') == 'Placed']
    preparing_orders = [o for o in all_orders if o.get('status') == 'Preparing']
    ready_orders = [o for o in all_orders if o.get('status') == 'Ready']
    served_orders = [o for o in all_orders if o.get('status') == 'Served']
    
    tables = serialize_docs(db.tables.find({}).sort('table_number', 1))
    
    return render_template(
        'admin/orders_board.html',
        all_orders=all_orders,
        placed_orders=placed_orders,
        preparing_orders=preparing_orders,
        ready_orders=ready_orders,
        served_orders=served_orders,
        status_filter=status_filter,
        table_filter=table_filter,
        tables=tables
    )

@admin_bp.route('/orders/update-status/<order_id>', methods=['POST'])
@admin_required
def update_order_status(order_id):
    """Updates order status: Placed -> Preparing -> Ready -> Served."""
    db = get_db()
    new_status = request.form.get('status') or (request.get_json() or {}).get('status')
    
    valid_statuses = ['Placed', 'Preparing', 'Ready', 'Served', 'Cancelled']
    if new_status not in valid_statuses:
        return jsonify({'status': 'error', 'message': 'Invalid status'}), 400
        
    try:
        obj_id = ObjectId(order_id)
        order = db.orders.find_one({'_id': obj_id})
        if not order:
            return jsonify({'status': 'error', 'message': 'Order not found'}), 404
            
        status_entry = {
            'status': new_status,
            'timestamp': datetime.utcnow(),
            'note': f"Status updated by {session.get('admin_name', 'Admin')}"
        }
        
        db.orders.update_one(
            {'_id': obj_id},
            {
                '$set': {'status': new_status, 'updated_at': datetime.utcnow()},
                '$push': {'status_history': status_entry}
            }
        )
        
        # If order is served or cancelled, check if table can be marked available
        table_num = order.get('table_number')
        if new_status in ['Served', 'Cancelled'] and table_num:
            active_orders_for_table = db.orders.count_documents({
                'table_number': table_num,
                'status': {'$in': ['Placed', 'Preparing', 'Ready']}
            })
            if active_orders_for_table == 0:
                db.tables.update_one({'table_number': table_num}, {'$set': {'status': 'available'}})

        if request.is_json:
            return jsonify({
                'status': 'success',
                'new_status': new_status,
                'message': f"Order #{order.get('order_number')} is now {new_status}"
            })
            
        flash(f"Order #{order.get('order_number')} updated to {new_status}.", 'success')
        return redirect(request.referrer or url_for('admin.orders_board'))
        
    except Exception as e:
        if request.is_json:
            return jsonify({'status': 'error', 'message': str(e)}), 400
        flash(f"Error updating order: {e}", 'danger')
        return redirect(url_for('admin.orders_board'))


# ================= TABLES & QR CODES =================

@admin_bp.route('/tables')
@admin_required
def tables_view():
    db = get_db()
    tables = serialize_docs(db.tables.find({}).sort('table_number', 1))
    return render_template('admin/tables_qr.html', tables=tables)

@admin_bp.route('/tables/add', methods=['POST'])
@admin_required
def add_table():
    db = get_db()
    table_number = request.form.get('table_number', type=int)
    capacity = request.form.get('capacity', type=int) or 4
    
    if not table_number:
        flash('Table number is required.', 'danger')
        return redirect(url_for('admin.tables_view'))
        
    if db.tables.find_one({'table_number': table_number}):
        flash(f'Table #{table_number} already exists.', 'warning')
        return redirect(url_for('admin.tables_view'))
        
    # Generate QR Code image
    qr_path = generate_table_qr(table_number, Config.QRCODE_FOLDER)
    
    new_table = {
        'table_number': table_number,
        'capacity': capacity,
        'status': 'available',
        'qr_code_path': qr_path,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    db.tables.insert_one(new_table)
    flash(f"Table #{table_number} added with generated QR code!", 'success')
    return redirect(url_for('admin.tables_view'))

@admin_bp.route('/tables/toggle-status/<int:table_number>', methods=['POST'])
@admin_required
def toggle_table_status(table_number):
    db = get_db()
    table = db.tables.find_one({'table_number': table_number})
    if not table:
        return jsonify({'status': 'error', 'message': 'Table not found'}), 404
        
    current_st = table.get('status', 'available')
    next_st = 'occupied' if current_st == 'available' else 'available'
    
    db.tables.update_one({'table_number': table_number}, {'$set': {'status': next_st, 'updated_at': datetime.utcnow()}})
    
    return jsonify({'status': 'success', 'table_number': table_number, 'new_status': next_st})


# ================= CUSTOMERS & SALES =================

@admin_bp.route('/customers')
@admin_required
def customers_view():
    db = get_db()
    customers = serialize_docs(db.users.find({}).sort('created_at', -1))
    
    # Attach order count and total spend for each customer
    for c in customers:
        user_id_str = c.get('id')
        pipeline = [
            {'$match': {'user_id': user_id_str, 'status': {'$ne': 'Cancelled'}}},
            {'$group': {'_id': None, 'order_count': {'$sum': 1}, 'total_spent': {'$sum': '$total_amount'}}}
        ]
        res = list(db.orders.aggregate(pipeline))
        if res:
            c['order_count'] = res[0]['order_count']
            c['total_spent'] = round(res[0]['total_spent'], 2)
        else:
            c['order_count'] = 0
            c['total_spent'] = 0.0

    return render_template('admin/customers.html', customers=customers)

@admin_bp.route('/sales')
@admin_required
def sales_report():
    db = get_db()
    
    # 1. Total summary
    pipeline_summary = [
        {'$match': {'status': {'$ne': 'Cancelled'}}},
        {'$group': {
            '_id': None,
            'total_sales': {'$sum': '$total_amount'},
            'total_orders': {'$sum': 1},
            'avg_order_value': {'$avg': '$total_amount'}
        }}
    ]
    summary_res = list(db.orders.aggregate(pipeline_summary))
    summary = summary_res[0] if summary_res else {'total_sales': 0, 'total_orders': 0, 'avg_order_value': 0}
    
    # 2. Category sales breakdown
    pipeline_cat = [
        {'$unwind': '$items'},
        {'$match': {'status': {'$ne': 'Cancelled'}}},
        {'$lookup': {
            'from': 'menu_items',
            'localField': 'items.name',
            'foreignField': 'name',
            'as': 'menu_info'
        }},
        {'$unwind': {'path': '$menu_info', 'preserveNullAndEmptyArrays': True}},
        {'$group': {
            '_id': {'$ifNull': ['$menu_info.category', 'South Indian']},
            'category_sales': {'$sum': '$items.subtotal'},
            'category_items_sold': {'$sum': '$items.quantity'}
        }},
        {'$sort': {'category_sales': -1}}
    ]
    category_sales = list(db.orders.aggregate(pipeline_cat))
    
    # 3. Best Selling Dishes
    pipeline_items = [
        {'$unwind': '$items'},
        {'$match': {'status': {'$ne': 'Cancelled'}}},
        {'$group': {
            '_id': '$items.name',
            'quantity_sold': {'$sum': '$items.quantity'},
            'revenue': {'$sum': '$items.subtotal'}
        }},
        {'$sort': {'quantity_sold': -1}},
        {'$limit': 10}
    ]
    item_sales = list(db.orders.aggregate(pipeline_items))
    
    return render_template(
        'admin/sales_report.html',
        summary=summary,
        category_sales=category_sales,
        item_sales=item_sales
    )
