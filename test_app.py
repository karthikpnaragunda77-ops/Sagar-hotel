import os
import json
import unittest
from datetime import datetime
from bson import ObjectId
from werkzeug.security import check_password_hash

from app import create_app
from db import get_db
from seed import seed_database

class SmartBreakfastHotelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Run seed to ensure baseline data exists
        seed_database()

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key-2026'
        self.client = self.app.test_client()
        self.db = get_db()

    def test_01_database_seeding(self):
        """Verify initial menu dishes, admin, user and tables in MongoDB."""
        # 1. Admin
        admin = self.db.admins.find_one({'email': 'admin@hotel.com'})
        self.assertIsNotNone(admin, "Admin should exist in MongoDB")
        self.assertTrue(check_password_hash(admin['password_hash'], 'admin123'))

        # 2. Tables
        table_count = self.db.tables.count_documents({})
        self.assertGreaterEqual(table_count, 10, "At least 10 tables should exist in MongoDB")

        # 3. 7 Initial Dishes
        expected_dishes = ['Appam', 'Poori', 'Idli', 'Dosa', 'Mix Breakfast', 'Mirchi', 'Vada']
        for dish_name in expected_dishes:
            dish = self.db.menu_items.find_one({'name': dish_name})
            self.assertIsNotNone(dish, f"Dish '{dish_name}' should exist in MongoDB menu_items")
            self.assertTrue(dish.get('is_available'), f"Dish '{dish_name}' should be available")
            self.assertGreater(dish.get('price'), 0, f"Dish '{dish_name}' should have valid price")

    def test_02_customer_authentication(self):
        """Test customer registration and login."""
        # Register new customer
        email = f"testdiner_{int(datetime.utcnow().timestamp())}@example.com"
        reg_res = self.client.post('/register', data={
            'name': 'Priya Patel',
            'email': email,
            'phone': '9876500000',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)

        # Verify user in database
        user = self.db.users.find_one({'email': email})
        self.assertIsNotNone(user)
        self.assertEqual(user['name'], 'Priya Patel')

        # Test login
        login_res = self.client.post('/login', data={
            'email': email,
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

    def test_03_admin_authentication(self):
        """Test admin login with segregation."""
        login_res = self.client.post('/admin/login', data={
            'email': 'admin@hotel.com',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Hotel Overview', login_res.data)

        # Access protected admin dashboard
        dash_res = self.client.get('/admin/dashboard')
        self.assertEqual(dash_res.status_code, 200)

    def test_04_qr_table_ordering_flow(self):
        """Test scanning Table 4 QR code, ordering, and tracking status."""
        # 1. Simulate QR Scan for Table 4
        scan_res = self.client.get('/table/4', follow_redirects=True)
        self.assertEqual(scan_res.status_code, 200)
        self.assertIn(b'TABLE #4 CONFIRMED', scan_res.data)

        # 2. Fetch dishes for order
        dosa = self.db.menu_items.find_one({'name': 'Dosa'})
        idli = self.db.menu_items.find_one({'name': 'Idli'})
        self.assertIsNotNone(dosa)
        self.assertIsNotNone(idli)

        # 3. Place order via API
        order_payload = {
            'table_number': 4,
            'customer_name': 'Rahul Verma',
            'customer_phone': '9123456780',
            'special_instructions': 'Extra crispy dosa and hot sambar please',
            'items': [
                {'item_id': str(dosa['_id']), 'name': dosa['name'], 'quantity': 2},
                {'item_id': str(idli['_id']), 'name': idli['name'], 'quantity': 1}
            ]
        }

        order_res = self.client.post('/api/order/place',
                                     data=json.dumps(order_payload),
                                     content_type='application/json')
        self.assertEqual(order_res.status_code, 200)
        order_data = json.loads(order_res.data)
        self.assertEqual(order_data['status'], 'success')
        self.assertTrue(order_data['order_number'].startswith('SBH-'))
        order_id = order_data['order_id']

        # 4. Verify order in MongoDB
        order_doc = self.db.orders.find_one({'_id': ObjectId(order_id)})
        self.assertIsNotNone(order_doc)
        self.assertEqual(order_doc['table_number'], 4)
        self.assertEqual(order_doc['status'], 'Placed')
        expected_subtotal = (dosa['price'] * 2) + (idli['price'] * 1)
        expected_tax = round(expected_subtotal * 0.05, 2)
        expected_total = round(expected_subtotal + expected_tax, 2)
        self.assertEqual(order_doc['subtotal'], expected_subtotal)
        self.assertEqual(order_doc['total_amount'], expected_total)

        # 5. Verify Table 4 marked occupied in MongoDB
        table_4 = self.db.tables.find_one({'table_number': 4})
        self.assertEqual(table_4.get('status'), 'occupied')

        # 6. Test Live Order Status Polling API
        poll_res = self.client.get(f'/api/order/status/{order_id}')
        self.assertEqual(poll_res.status_code, 200)
        poll_data = json.loads(poll_res.data)
        self.assertEqual(poll_data['order_status'], 'Placed')

    def test_05_admin_menu_crud_and_live_sync(self):
        """Test admin adding a new dish and verifying it immediately appears on user menu."""
        # 1. Login as Admin
        self.client.post('/admin/login', data={'email': 'admin@hotel.com', 'password': 'admin123'})

        # 2. Add New Dish: 'Rava Kesari'
        new_dish_name = f"Rava Kesari Special {int(datetime.utcnow().timestamp())}"
        add_res = self.client.post('/admin/menu/add', data={
            'name': new_dish_name,
            'category': 'Traditional',
            'price': 65,
            'prep_time_mins': 5,
            'description': 'Warm semolina pudding rich with pure ghee, saffron, and roasted cashews.',
            'badge': 'Chef Sweet Special',
            'image_url': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80',
            'is_veg': 'on'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)

        # 3. Verify dish is in MongoDB
        dish_doc = self.db.menu_items.find_one({'name': new_dish_name})
        self.assertIsNotNone(dish_doc, "Newly added dish must be present in MongoDB menu_items")
        self.assertEqual(dish_doc['price'], 65)

        # 4. Verify User Menu API returns newly added dish immediately without server restart
        user_menu_res = self.client.get('/api/menu')
        self.assertEqual(user_menu_res.status_code, 200)
        user_menu_data = json.loads(user_menu_res.data)
        found_in_user_menu = any(d['name'] == new_dish_name for d in user_menu_data['dishes'])
        self.assertTrue(found_in_user_menu, "New dish must immediately reflect in customer menu from MongoDB")

        # 5. Test Live Availability Toggle
        dish_id = str(dish_doc['_id'])
        toggle_res = self.client.post(f'/admin/menu/toggle/{dish_id}')
        self.assertEqual(toggle_res.status_code, 200)
        toggle_data = json.loads(toggle_res.data)
        self.assertFalse(toggle_data['is_available'])

        # Disabled dish should not be returned on active user menu API
        user_menu_res2 = self.client.get('/api/menu')
        user_menu_data2 = json.loads(user_menu_res2.data)
        found_after_disable = any(d['name'] == new_dish_name for d in user_menu_data2['dishes'])
        self.assertFalse(found_after_disable, "Disabled dish must not appear in customer active menu")

    def test_06_admin_kitchen_workflow_kanban(self):
        """Test complete order workflow transition: Placed -> Preparing -> Ready -> Served."""
        # 1. Admin login
        self.client.post('/admin/login', data={'email': 'admin@hotel.com', 'password': 'admin123'})

        # 2. Create an order for Table 2
        vada = self.db.menu_items.find_one({'name': 'Vada'})
        order_doc = {
            'order_number': 'SBH-TEST-99',
            'customer_name': 'Sneha Rao',
            'table_number': 2,
            'items': [{'name': 'Vada', 'price': 40, 'quantity': 2, 'subtotal': 80}],
            'subtotal': 80,
            'tax': 4,
            'total_amount': 84,
            'status': 'Placed',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        order_id = str(self.db.orders.insert_one(order_doc).inserted_id)

        # 3. Transition: Placed -> Preparing
        res1 = self.client.post(f'/admin/orders/update-status/{order_id}',
                                data=json.dumps({'status': 'Preparing'}),
                                content_type='application/json')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(self.db.orders.find_one({'_id': ObjectId(order_id)})['status'], 'Preparing')

        # 4. Transition: Preparing -> Ready
        res2 = self.client.post(f'/admin/orders/update-status/{order_id}',
                                data=json.dumps({'status': 'Ready'}),
                                content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(self.db.orders.find_one({'_id': ObjectId(order_id)})['status'], 'Ready')

        # 5. Transition: Ready -> Served
        res3 = self.client.post(f'/admin/orders/update-status/{order_id}',
                                data=json.dumps({'status': 'Served'}),
                                content_type='application/json')
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(self.db.orders.find_one({'_id': ObjectId(order_id)})['status'], 'Served')

    def test_07_table_and_qr_generation(self):
        """Test adding a dynamic table (Table 12) and generating branded QR code image."""
        self.client.post('/admin/login', data={'email': 'admin@hotel.com', 'password': 'admin123'})

        res = self.client.post('/admin/tables/add', data={
            'table_number': 12,
            'capacity': 6
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        table_12 = self.db.tables.find_one({'table_number': 12})
        self.assertIsNotNone(table_12)
        self.assertEqual(table_12['capacity'], 6)
        self.assertTrue(os.path.exists(os.path.join('static', 'qrcodes', 'table_12.png')))

    def test_08_template_renderings(self):
        """Test all admin and user template renders without template errors."""
        # 1. Admin login & render all admin views
        self.client.post('/admin/login', data={'email': 'admin@hotel.com', 'password': 'admin123'})
        
        dash_res = self.client.get('/admin/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'Hotel Overview', dash_res.data)

        orders_res = self.client.get('/admin/orders')
        self.assertEqual(orders_res.status_code, 200)
        self.assertIn(b'Kitchen Orders Workflow', orders_res.data)

        tables_res = self.client.get('/admin/tables')
        self.assertEqual(tables_res.status_code, 200)

        sales_res = self.client.get('/admin/sales')
        self.assertEqual(sales_res.status_code, 200)

        customers_res = self.client.get('/admin/customers')
        self.assertEqual(customers_res.status_code, 200)

        # 2. User Views
        menu_res = self.client.get('/menu')
        self.assertEqual(menu_res.status_code, 200)

        cart_res = self.client.get('/cart')
        self.assertEqual(cart_res.status_code, 200)

        orders_history_res = self.client.get('/orders')
        self.assertEqual(orders_history_res.status_code, 200)

        # Order status view with valid order
        sample_order = self.db.orders.find_one({})
        if sample_order:
            order_id = str(sample_order['_id'])
            status_res = self.client.get(f'/order/status/{order_id}')
            self.assertEqual(status_res.status_code, 200)
            self.assertIn(b'Live Kitchen Progress', status_res.data)

if __name__ == '__main__':
    unittest.main()

