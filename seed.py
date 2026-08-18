import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash
import qrcode
from PIL import Image, ImageDraw, ImageFont

from config import Config
from db import get_db

def generate_table_qr(table_num, output_folder, base_url="http://localhost:5000"):
    """Generates a branded QR Code image for a hotel table."""
    os.makedirs(output_folder, exist_ok=True)
    target_url = f"{base_url}/table/{table_num}"
    
    # Create QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF").convert('RGB')
    
    # Create a nice frame with text "Table {table_num} - Smart Breakfast Hotel"
    width, height = qr_img.size
    card_width = width + 40
    card_height = height + 90
    card = Image.new('RGB', (card_width, card_height), color='#FFFBEB') # soft warm amber background
    
    draw = ImageDraw.Draw(card)
    # Draw border
    draw.rectangle([5, 5, card_width - 6, card_height - 6], outline="#D97706", width=3)
    
    # Paste QR code in center
    card.paste(qr_img, (20, 20))
    
    # Text caption
    caption = f"TABLE {table_num}"
    subcaption = "Scan to Order Fresh Breakfast"
    
    # Draw simple text using default font
    draw.text((card_width // 2, height + 35), caption, fill="#92400E", anchor="mm")
    draw.text((card_width // 2, height + 60), subcaption, fill="#B45309", anchor="mm")
    
    filename = f"table_{table_num}.png"
    filepath = os.path.join(output_folder, filename)
    card.save(filepath)
    return f"/static/qrcodes/{filename}"

def seed_database():
    db = get_db()
    print("Seeding database:", db.name)
    
    # 1. Seed Admin
    admin_email = "sagarallu36@gmail.com"
    existing_admin = db.admins.find_one({"email": admin_email})
    if not existing_admin:
        admin_doc = {
            "name": "Head Chef & Manager",
            "email": admin_email,
            "password_hash": generate_password_hash("Sagar@1234"),
            "role": "superadmin",
            "created_at": datetime.utcnow()
        }
        db.admins.insert_one(admin_doc)
        print(f"[OK] Admin created: {admin_email} (Password: Sagar@1234)")
    else:
        print(f"[INFO] Admin already exists: {admin_email}")

    # 2. Seed Sample Customer User
    user_email = "guest@hotel.com"
    if not db.users.find_one({"email": user_email}):
        user_doc = {
            "name": "Arjun Sharma",
            "email": user_email,
            "phone": "9876543210",
            "password_hash": generate_password_hash("user123"),
            "created_at": datetime.utcnow()
        }
        db.users.insert_one(user_doc)
        print(f"[OK] Sample Customer created: {user_email} (Password: user123)")

    # 3. Seed Tables (1 to 10) and generate QR codes
    qr_dir = Config.QRCODE_FOLDER
    os.makedirs(qr_dir, exist_ok=True)
    
    for t_num in range(1, 11):
        qr_path = generate_table_qr(t_num, qr_dir)
        db.tables.update_one(
            {"table_number": t_num},
            {
                "$set": {
                    "table_number": t_num,
                    "capacity": 4 if t_num <= 6 else (6 if t_num <= 8 else 2),
                    "status": "available",
                    "qr_code_path": qr_path,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    print("[OK] 10 Tables created with generated QR codes.")

    # 4. Seed Initial 7 Menu Items
    # Real, reliable CDN food photos tailored to South Indian breakfast
    initial_dishes = [
        {
            "name": "Appam",
            "price": 40,
            "category": "South Indian",
            "description": "Soft and fluffy fermented rice pancake with a thick pillowy center and delicate crispy lace edges. Served with sweet coconut milk and seasoned vegetable stew.",
            "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsrI6efYh5reUNJ0H26k1DBB5OZajIZtEVQ-EqSos2Ag&s",
            "prep_time_mins": 10,
            "is_veg": True,
            "is_available": True,
            "badge": "Chef Special"
        },
        {
            "name": "Poori",
            "price": 40,
            "category": "Traditional",
            "description": "Golden-brown puffed whole wheat pooris (3 pcs) served hot with aromatic spiced potato bhaji masala and freshly grated coconut chutney.",
            "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSvh_89xj-_sNFyhHfbqOERvCFLAHQvYUGIupsh594shg&s=10",
            "prep_time_mins": 12,
            "is_veg": True,
            "is_available": True,
            "badge": "Popular"
        },
        {
            "name": "Idli",
            "price": 40,
            "category": "South Indian",
            "description": "Steamed soft, melt-in-mouth savory rice and black lentil cakes (2 pcs). Accompanied by piping hot vegetable sambar and freshly ground coconut-mint chutney duo.",
            "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQFxuI3Ghz9SQeC-HuvJ5-TQBSc6ZJkGfM-9iG0h8_QLQ&s=10",
            "prep_time_mins": 8,
            "is_veg": True,
            "is_available": True,
            "badge": "Healthy Choice"
        },
        {
            "name": "Dosa",
            "price": 50,
            "category": "South Indian",
            "description": "Classic crisp golden crepe roasted to perfection with pure ghee, stuffed with spiced onion-potato masala, served with traditional sambar and chutneys.",
            "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS9WyKuI4-uV3ANwi4SBA-PEoTGA0wdAFKApGmSl7YkQw&s=10",
            "prep_time_mins": 15,
            "is_veg": True,
            "is_available": True,
            "badge": "Bestseller"
        },
        {
            "name": "Mix Breakfast",
            "price": 100,
            "category": "Combos",
            "description": "The Grand Hotel Special: 1 Mini Masala Dosa, 1 Steamed Soft Idli, 1 Crispy Medu Vada, Kesari Bath (Sweet), Chow-Chow Upma, and authentic South Indian Filter Coffee.",
            "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTWX680NspNmeeQMiLOJ5ingCLyeERppFW1MMGLg3z1-g&s=10",
            "prep_time_mins": 15,
            "is_veg": True,
            "is_available": True,
            "badge": "Value Combo"
        },
        {
            "name": "Mirchi",
            "price": 30,
            "category": "Snacks",
            "description": "Crispy golden gram-flour battered Bhavnagri chili fritters (Mirchi Bajji) sprinkled with tangy chaat masala, served with mint-coriander dip.",
            "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRbsc-U9aMI2vhVQ9StdMZHaDhZyijfmpNxMrJMmftUzA&s=10",
            "prep_time_mins": 10,
            "is_veg": True,
            "is_available": True,
            "badge": "Crispy Snack"
        },
        {
            "name": "Vada",
            "price": 40,
            "category": "South Indian",
            "description": "Crispy golden medu vada (2 pcs) with a crunchy outer shell and fluffy interior seasoned with crushed black peppercorns, curry leaves, and fresh ginger.",
            "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTxjzDFIYwpbTxae6qDdijt7dNkwCW3hx6pjIa4w2eReQ&s=10",
            "prep_time_mins": 8,
            "is_veg": True,
            "is_available": True,
            "badge": "Must Try"
        }
    ]

    for dish in initial_dishes:
        db.menu_items.update_one(
            {"name": dish["name"]},
            {
                "$set": {
                    "name": dish["name"],
                    "price": dish["price"],
                    "category": dish["category"],
                    "description": dish["description"],
                    "image_url": dish["image_url"],
                    "prep_time_mins": dish["prep_time_mins"],
                    "is_veg": dish["is_veg"],
                    "is_available": dish["is_available"],
                    "badge": dish.get("badge", ""),
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    print(f"[OK] Seeded {len(initial_dishes)} breakfast menu items in MongoDB.")
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
