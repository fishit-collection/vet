"""
PREMIUM SYSTEM FOR VECHNOST AUTOPOST BOT
Optimized for Railway UTC Timezone
"""

import json
import os
import random
import string
from datetime import datetime, timedelta
import time

# ========== TIMEZONE CONFIGURATION ==========
# Force UTC timezone untuk Railway
os.environ['TZ'] = 'UTC'
try:
    time.tzset()  # Unix only
except:
    pass

PREMIUM_FILE = "premium_data.json"

# ========== TIME FUNCTIONS ==========
def get_utc_now() -> datetime:
    """Get current UTC time"""
    return datetime.utcnow()

def format_datetime(dt: datetime) -> str:
    """Format datetime ke string"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string dari UTC"""
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

# ========== PREMIUM CODE GENERATION ==========
def generate_premium_code(duration_days: int, created_by: int) -> dict:
    """
    Generate kode premium unik dengan format: VECHNOST-XXXXXXXXXXXXXXX
    
    Args:
        duration_days: Durasi premium dalam hari (9999 untuk lifetime)
        created_by: ID Discord user yang membuat kode
    
    Returns:
        Dictionary dengan data kode premium
    """
    # Generate random part 15 karakter
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
    code = f"VECHNOST-{random_part}"
    
    created_at = get_utc_now()
    
    # Handle lifetime (9999 days = ~27 tahun)
    if duration_days == 9999:
        expires_at = datetime(2100, 1, 1)  # Tahun 2100 sebagai lifetime
    else:
        expires_at = created_at + timedelta(days=duration_days)
    
    return {
        "code": code,
        "duration_days": duration_days,
        "created_at": format_datetime(created_at),
        "expires_at": format_datetime(expires_at),
        "created_by": created_by,
        "used_by": None,
        "used_at": None,
        "status": "active"  # active, used, expired, revoked
    }

# ========== DATABASE OPERATIONS ==========
def load_premium_data() -> dict:
    """
    Load data premium dari file JSON
    
    Returns:
        Dictionary dengan struktur:
        {
            "premium_codes": {
                "VECHNOST-ABC123": { ... },
                ...
            },
            "user_subscriptions": {
                "123456789": { ... },
                ...
            }
        }
    """
    try:
        if os.path.exists(PREMIUM_FILE):
            with open(PREMIUM_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"premium_codes": {}, "user_subscriptions": {}}
    except Exception as e:
        print(f"❌ Error loading premium data: {e}")
        return {"premium_codes": {}, "user_subscriptions": {}}

def save_premium_data(data: dict):
    """
    Simpan data premium ke file JSON
    
    Args:
        data: Dictionary dengan data premium
    """
    try:
        with open(PREMIUM_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("💾 Premium data saved")
    except Exception as e:
        print(f"❌ Error saving premium data: {e}")

# ========== PREMIUM VALIDATION ==========
async def validate_premium_code(code: str, user_id: int, guild=None) -> tuple:
    """
    Validasi kode premium untuk user
    
    Args:
        code: Kode premium (case-insensitive)
        user_id: ID Discord user yang menggunakan kode
        guild: Discord guild object (optional)
    
    Returns:
        Tuple (success: bool, message: str)
    """
    code = code.strip().upper()
    
    # Load data
    data = load_premium_data()
    
    # Cek apakah kode ada
    if code not in data["premium_codes"]:
        return False, "❌ Kode premium tidak valid!"
    
    code_data = data["premium_codes"][code]
    
    # Cek status kode
    if code_data["status"] != "active":
        return False, "❌ Kode tidak aktif!"
    
    # Cek apakah sudah digunakan
    if code_data["used_by"]:
        return False, "❌ Kode sudah digunakan oleh user lain!"
    
    # Cek expiry date
    expires_at = parse_datetime(code_data["expires_at"])
    now = get_utc_now()
    
    if now > expires_at:
        code_data["status"] = "expired"
        save_premium_data(data)
        return False, "❌ Kode sudah expired!"
    
    # Aktifkan kode untuk user
    code_data["used_by"] = user_id
    code_data["used_at"] = format_datetime(now)
    code_data["status"] = "used"
    
    # Buat atau update subscription user
    user_id_str = str(user_id)
    expires_at_str = format_datetime(expires_at)
    
    data["user_subscriptions"][user_id_str] = {
        "expires_at": expires_at_str,
        "plan": f"{code_data['duration_days']}d",
        "bots_allowed": 5,  # Premium user dapat 5 bot
        "used_bots": 0
    }
    
    save_premium_data(data)
    
    return True, "✅ Kode premium berhasil diaktifkan!"

def check_user_premium(user_id: int) -> tuple:
    """
    Cek status premium user
    
    Args:
        user_id: ID Discord user
    
    Returns:
        Tuple (is_premium: bool, days_left: int, plan: str, bots_allowed: int, expires_at: str)
    """
    data = load_premium_data()
    user_id_str = str(user_id)
    
    # Cek apakah user memiliki subscription
    if user_id_str not in data["user_subscriptions"]:
        return False, 0, "none", 0, None
    
    sub_data = data["user_subscriptions"][user_id_str]
    expires_at = parse_datetime(sub_data["expires_at"])
    now = get_utc_now()
    
    # Cek apakah subscription sudah expired
    if now > expires_at:
        return False, 0, "expired", 0, sub_data["expires_at"]
    
    # Hitung sisa hari
    days_left = (expires_at - now).days
    
    return True, days_left, sub_data["plan"], sub_data["bots_allowed"], sub_data["expires_at"]

def get_user_bot_limit(user_id: int) -> int:
    """
    Get jumlah maksimal bot yang bisa dibuat user
    
    Args:
        user_id: ID Discord user
    
    Returns:
        int: Jumlah maksimal bot (0 = tidak bisa buat bot)
    """
    is_premium, _, _, bots_allowed, _ = check_user_premium(user_id)
    
    if not is_premium:
        return 0  # Non-premium tidak bisa buat bot
    
    return bots_allowed

def get_premium_time_details(user_id: int) -> dict:
    """
    Get detailed premium time info untuk user
    
    Args:
        user_id: ID Discord user
    
    Returns:
        Dictionary dengan detail waktu premium
    """
    data = load_premium_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data["user_subscriptions"]:
        return {
            "active": False,
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "seconds": 0,
            "plan": "none",
            "expires_at": None,
            "total_seconds": 0
        }
    
    sub_data = data["user_subscriptions"][user_id_str]
    expires_at = parse_datetime(sub_data["expires_at"])
    now = get_utc_now()
    
    if now > expires_at:
        return {
            "active": False,
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "seconds": 0,
            "plan": "expired",
            "expires_at": sub_data["expires_at"],
            "total_seconds": 0
        }
    
    # Hitung detail waktu
    delta = expires_at - now
    total_seconds = int(delta.total_seconds())
    
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    
    return {
        "active": True,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "plan": sub_data["plan"],
        "expires_at": sub_data["expires_at"],
        "total_seconds": total_seconds,
        "bots_allowed": sub_data.get("bots_allowed", 5),
        "used_bots": sub_data.get("used_bots", 0)
    }

def revoke_premium_code(code: str, admin_id: int) -> tuple:
    """
    Revoke kode premium (admin only)
    
    Args:
        code: Kode premium
        admin_id: ID admin yang melakukan revoke
    
    Returns:
        Tuple (success: bool, message: str)
    """
    code = code.strip().upper()
    data = load_premium_data()
    
    if code not in data["premium_codes"]:
        return False, "❌ Kode tidak ditemukan!"
    
    code_data = data["premium_codes"][code]
    
    # Jika kode sudah digunakan, hapus subscription user
    if code_data["used_by"]:
        user_id_str = str(code_data["used_by"])
        if user_id_str in data["user_subscriptions"]:
            del data["user_subscriptions"][user_id_str]
    
    # Hapus kode
    del data["premium_codes"][code]
    
    save_premium_data(data)
    
    return True, f"✅ Kode {code} berhasil di-revoke oleh admin {admin_id}"

def list_all_premium_codes(admin_id: int) -> list:
    """
    List semua kode premium (admin only)
    
    Args:
        admin_id: ID admin
    
    Returns:
        List of premium codes dengan status
    """
    data = load_premium_data()
    codes = []
    
    for code, code_data in data["premium_codes"].items():
        codes.append({
            "code": code,
            "duration": f"{code_data['duration_days']}d",
            "created_at": code_data["created_at"],
            "expires_at": code_data["expires_at"],
            "status": code_data["status"],
            "created_by": code_data["created_by"],
            "used_by": code_data["used_by"]
        })
    
    return codes

def list_all_subscriptions(admin_id: int) -> list:
    """
    List semua user subscription (admin only)
    
    Args:
        admin_id: ID admin
    
    Returns:
        List of user subscriptions
    """
    data = load_premium_data()
    subscriptions = []
    
    for user_id, sub_data in data["user_subscriptions"].items():
        expires_at = parse_datetime(sub_data["expires_at"])
        now = get_utc_now()
        
        is_active = now < expires_at
        days_left = (expires_at - now).days if is_active else 0
        
        subscriptions.append({
            "user_id": user_id,
            "plan": sub_data["plan"],
            "expires_at": sub_data["expires_at"],
            "is_active": is_active,
            "days_left": days_left,
            "bots_allowed": sub_data.get("bots_allowed", 5),
            "used_bots": sub_data.get("used_bots", 0)
        })
    
    return subscriptions

# ========== UTILITY FUNCTIONS ==========
def create_sample_codes():
    """
    Buat sample kode premium untuk testing
    """
    data = load_premium_data()
    
    # Sample 7-day code
    sample_7d = generate_premium_code(7, 1073527513671798845)
    data["premium_codes"][sample_7d["code"]] = sample_7d
    
    # Sample 30-day code
    sample_30d = generate_premium_code(30, 1073527513671798845)
    data["premium_codes"][sample_30d["code"]] = sample_30d
    
    save_premium_data(data)
    print(f"✅ Created sample codes: {sample_7d['code']}, {sample_30d['code']}")

def cleanup_expired_codes():
    """
    Cleanup kode yang sudah expired
    """
    data = load_premium_data()
    now = get_utc_now()
    expired_count = 0
    
    # Cleanup expired codes
    codes_to_remove = []
    for code, code_data in data["premium_codes"].items():
        expires_at = parse_datetime(code_data["expires_at"])
        if now > expires_at and code_data["status"] == "active":
            code_data["status"] = "expired"
            expired_count += 1
    
    # Cleanup expired subscriptions
    users_to_remove = []
    for user_id, sub_data in data["user_subscriptions"].items():
        expires_at = parse_datetime(sub_data["expires_at"])
        if now > expires_at:
            users_to_remove.append(user_id)
    
    for user_id in users_to_remove:
        del data["user_subscriptions"][user_id]
    
    if expired_count > 0 or users_to_remove:
        save_premium_data(data)
        print(f"🧹 Cleaned up {expired_count} expired codes and {len(users_to_remove)} expired subscriptions")
    
    return expired_count, len(users_to_remove)

# ========== TEST FUNCTIONS ==========
def test_premium_system():
    """Test fungsi premium system"""
    print("🧪 Testing Premium System...")
    
    # Generate test code
    test_code = generate_premium_code(7, 123456789)
    print(f"✅ Generated test code: {test_code['code']}")
    
    # Load data
    data = load_premium_data()
    print(f"✅ Loaded premium data: {len(data['premium_codes'])} codes, {len(data['user_subscriptions'])} subscriptions")
    
    # Check time functions
    now = get_utc_now()
    print(f"✅ UTC Time: {format_datetime(now)}")
    
    print("✅ Premium system test completed")

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    # Run cleanup on startup
    cleanup_expired_codes()
    
    # Uncomment untuk testing
    # test_premium_system()
    # create_sample_codes()
    
    print("✅ Premium system module loaded")
