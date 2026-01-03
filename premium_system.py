import json
import os
import random
import string
from datetime import datetime, timedelta

PREMIUM_FILE = "premium_data.json"

def generate_premium_code(duration_days: int, created_by: int) -> dict:
    """Generate kode premium unik 15 karakter setelah VECHNOST-"""
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
    code = f"VECHNOST-{random_part}"
    
    created_at = datetime.now()
    if duration_days == 9999:
        expires_at = datetime(2100, 1, 1)  # Lifetime
    else:
        expires_at = created_at + timedelta(days=duration_days)
    
    return {
        "code": code,
        "duration_days": duration_days,
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "created_by": created_by,
        "used_by": None,
        "used_at": None,
        "status": "active"
    }

def load_premium_data():
    """Load data premium dari file"""
    try:
        if os.path.exists(PREMIUM_FILE):
            with open(PREMIUM_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"premium_codes": {}, "user_subscriptions": {}}
    except:
        return {"premium_codes": {}, "user_subscriptions": {}}

def save_premium_data(data):
    """Simpan data premium ke file"""
    with open(PREMIUM_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def validate_premium_code(code: str, user_id: int, guild=None) -> tuple:
    """Validasi kode premium"""
    data = load_premium_data()
    
    if code not in data["premium_codes"]:
        return False, "❌ Kode tidak valid!"
    
    code_data = data["premium_codes"][code]
    
    if code_data["status"] != "active":
        return False, "❌ Kode tidak aktif!"
    
    if code_data["used_by"]:
        return False, "❌ Kode sudah digunakan!"
    
    expires_at = datetime.strptime(code_data["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expires_at:
        return False, "❌ Kode sudah expired!"
    
    # Aktifkan untuk user
    code_data["used_by"] = user_id
    code_data["used_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code_data["status"] = "used"
    
    # Buat/update subscription user
    user_id_str = str(user_id)
    expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
    
    data["user_subscriptions"][user_id_str] = {
        "expires_at": expires_at_str,
        "plan": f"{code_data['duration_days']}d",
        "bots_allowed": 5,
        "used_bots": 0
    }
    
    save_premium_data(data)
    return True, "✅ Kode premium berhasil diaktifkan!"

def check_user_premium(user_id: int) -> tuple:
    """Cek status premium user"""
    data = load_premium_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data["user_subscriptions"]:
        return False, 0, "none", 0
    
    sub_data = data["user_subscriptions"][user_id_str]
    expires_at = datetime.strptime(sub_data["expires_at"], "%Y-%m-%d %H:%M:%S")
    
    if datetime.now() > expires_at:
        return False, 0, "expired", 0
    
    days_left = (expires_at - datetime.now()).days
    return True, days_left, sub_data["plan"], sub_data["bots_allowed"]

def get_user_bot_limit(user_id: int) -> int:
    """Get jumlah maksimal bot yang bisa dibuat user"""
    is_premium, _, _, _ = check_user_premium(user_id)
    return 5 if is_premium else 0  # 0 = tidak bisa buat bot