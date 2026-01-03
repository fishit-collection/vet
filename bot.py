"""
VECHNOST AUTOPOST BOT - RAILWAY OPTIMIZED
Version 2.0 - Optimized for 24/7 Railway Deployment
"""

# ========== IMPORT DENGAN TIMEZONE FIX ==========
import os
import sys
import time

# Set timezone ke UTC untuk Railway
os.environ['TZ'] = 'UTC'
try:
    time.tzset()  # Unix only
except:
    pass

# ========== IMPORT LIBRARIES ==========
import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput, Select
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# ========== RAILWAY WEB SERVER ==========
from flask import Flask
from threading import Thread

# Setup Flask app untuk Railway health checks
app = Flask('')

@app.route('/')
def home():
    """Home page untuk Railway health check"""
    return f"""
    <html>
        <head>
            <title>🤖 Vechnost AutoPost Bot</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{ 
                    max-width: 800px; 
                    margin: 0 auto;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 30px;
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                }}
                h1 {{ font-size: 3em; margin-bottom: 20px; }}
                .status {{ 
                    background: rgba(0, 255, 0, 0.2);
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Vechnost AutoPost Bot</h1>
                <div class="status">
                    <h2>✅ STATUS: ONLINE</h2>
                    <p>Bot is running on Railway 24/7</p>
                    <p>UTC Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                <h3>📊 Bot Features:</h3>
                <ul style="text-align: left; display: inline-block;">
                    <li>🔑 Premium Code System</li>
                    <li>⚙️ AutoPost Setup</li>
                    <li>📨 Multi-Channel Posting</li>
                    <li>📊 Real-time Status</li>
                    <li>🔔 Discord Webhook Logs</li>
                </ul>
                <p style="margin-top: 30px;">
                    <strong>🚀 Powered by Railway.app</strong>
                </p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check endpoint untuk Railway"""
    return "OK", 200

@app.route('/status')
def status():
    """Status endpoint untuk monitoring"""
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "vechnost-autopost-bot",
        "version": "2.0"
    }

def run_web_server():
    """Start Flask web server untuk Railway"""
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Starting web server on port {port}")
    # Nonaktifkan debug mode untuk production
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

def keep_alive():
    """Start keep-alive web server di background"""
    t = Thread(target=run_web_server, daemon=True)
    t.start()
    print("✅ Web server started for Railway health checks")

# ========== LOAD ENVIRONMENT VARIABLES ==========
# Railway menyediakan env vars langsung, tapi kita load dotenv untuk local
load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_IDS_STR = os.environ.get('ADMIN_IDS', '')

# Parse admin IDs
ADMIN_IDS = set()
if ADMIN_IDS_STR:
    for id_str in ADMIN_IDS_STR.split(','):
        try:
            ADMIN_IDS.add(int(id_str.strip()))
        except ValueError:
            pass

# Fallback untuk local development
if not BOT_TOKEN:
    print("⚠️ Warning: BOT_TOKEN not found in environment variables")
    print("⚠️ Make sure to set BOT_TOKEN in Railway Variables")

if not ADMIN_IDS:
    # Default admin ID (ganti dengan ID Discord Anda)
    ADMIN_IDS = {1073527513671798845}
    print(f"⚠️ Using default admin ID: {ADMIN_IDS}")

print("=" * 60)
print("🚀 VECHNOST AUTOPOST BOT - RAILWAY EDITION")
print("📅 UTC Time:", datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
print("🤖 Admin IDs:", ADMIN_IDS)
print("=" * 60)

# ========== DISCORD BOT SETUP ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ========== IMPORT PREMIUM SYSTEM ==========
try:
    from premium_system import *
    print("✅ Premium system loaded successfully")
except ImportError as e:
    print(f"❌ Error loading premium system: {e}")
    # Fallback functions jika premium system tidak ada
    async def validate_premium_code(*args): 
        return False, "Premium system not loaded"
    def check_user_premium(user_id): 
        return False, 0, "none", 0, None
    def get_user_bot_limit(user_id): 
        return 0
    def generate_premium_code(*args): 
        return {}
    def load_premium_data(): 
        return {"premium_codes": {}, "user_subscriptions": {}}
    def save_premium_data(data): 
        pass

# ========== DATABASE & CONFIG ==========
AUTOPOST_DATA = {}
DATA_FILE = "autopost_data.json"
PORTAL_FILE = "portal.json"

# Role IDs untuk ditambahkan otomatis
AUTOPOST_ROLE_ID = 1456729990824726528
CUSTOMER_ROLE_ID = 1452721209480450058

# Load portal.json untuk webhook dan emoji
WEBHOOK_URLS = {}
EMOJIS = {}

try:
    if os.path.exists(PORTAL_FILE):
        with open(PORTAL_FILE, 'r', encoding='utf-8') as f:
            portal_data = json.load(f)
            WEBHOOK_URLS = portal_data.get('WEBHOOK', {})
            EMOJIS = portal_data.get('EMOJIS', {})
            print("✅ Loaded portal.json configuration")
except Exception as e:
    print(f"❌ Error loading portal.json: {e}")
    # Default emoji fallback
    EMOJIS = {
        "ARROW_EMOJI": "➡️",
        "SUCCESS_EMOJI": "✅",
        "FAILED_EMOJI": "❌",
        "INFO_EMOJI": "📋",
        "BOT_EMOJI": "🤖",
        "USER_EMOJI": "👤",
        "TIME_EMOJI": "⏰",
        "CHANNEL_EMOJI": "📺",
        "TITLE_EMOJI": "🤖",
        "SETTING_EMOJI": "⚙️",
        "ACCESS_EMOJI": "🔑"
    }

# ========== TIMEZONE AWARE FUNCTIONS ==========
def get_utc_now():
    """Get current UTC time"""
    return datetime.utcnow()

def format_datetime(dt: datetime) -> str:
    """Format datetime ke string"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string dari UTC"""
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")

# ========== DATABASE FUNCTIONS ==========
def load_data():
    """Load data dari file JSON"""
    global AUTOPOST_DATA
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Konversi struktur lama ke baru jika diperlukan
                new_data = {}
                for guild_id, value in data.items():
                    if isinstance(value, list):
                        # Struktur lama: {guild_id: [bots]}
                        new_data[guild_id] = {"0": value}
                    else:
                        # Struktur baru: {guild_id: {user_id: [bots]}}
                        new_data[guild_id] = value
                AUTOPOST_DATA = new_data
                print(f"✅ Loaded data from {DATA_FILE}: {len(AUTOPOST_DATA)} guild(s)")
        else:
            AUTOPOST_DATA = {}
            print("📁 Created new data structure")
            save_data()
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        AUTOPOST_DATA = {}

def save_data():
    """Simpan data ke file JSON"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(AUTOPOST_DATA, f, indent=2, ensure_ascii=False)
        print(f"💾 Data saved to {DATA_FILE}")
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def get_user_bots(guild_id: str, user_id: int) -> list:
    """Ambil daftar bot untuk user tertentu"""
    try:
        if guild_id in AUTOPOST_DATA:
            user_id_str = str(user_id)
            if user_id_str in AUTOPOST_DATA[guild_id]:
                return AUTOPOST_DATA[guild_id][user_id_str]
    except Exception as e:
        print(f"❌ Error getting user bots: {e}")
    return []

def save_user_bots(guild_id: str, user_id: int, bots: list):
    """Simpan daftar bot untuk user tertentu"""
    if guild_id not in AUTOPOST_DATA:
        AUTOPOST_DATA[guild_id] = {}
    
    user_id_str = str(user_id)
    AUTOPOST_DATA[guild_id][user_id_str] = bots
    save_data()

def has_permission(member: discord.Member) -> bool:
    """Cek apakah user memiliki akses (admin atau premium)"""
    if member.id in ADMIN_IDS:
        return True
    
    # Cek status premium user
    is_premium, _, _, _ = check_user_premium(member.id)
    return is_premium

# ========== UTILITY FUNCTIONS ==========
def parse_channel_ids(text: str) -> List[str]:
    """Parse channel IDs dari text (support multiple formats)"""
    # Replace semua separator dengan newline
    for sep in [',', ';', '|', ' ']:
        text = text.replace(sep, '\n')
    
    lines = text.split('\n')
    channel_ids = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Ekstrak hanya angka dari line
        clean_id = ''.join(filter(str.isdigit, line))
        
        if clean_id and len(clean_id) >= 17:  # Discord ID minimal 17 digit
            channel_ids.append(clean_id)
        
        # Limit maksimal 20 channel
        if len(channel_ids) >= 20:
            break
    
    return channel_ids[:20]  # Max 20 channel

async def get_user_info_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Dapatkan info user dari Discord token"""
    headers = {
        'Authorization': token.strip(),
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'https://discord.com/api/v10/users/@me',
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'id': data.get('id'),
                        'username': data.get('username', 'Unknown'),
                        'global_name': data.get('global_name', data.get('username', 'Unknown')),
                        'discriminator': data.get('discriminator', '0'),
                        'avatar': data.get('avatar'),
                        'bot': data.get('bot', False)
                    }
                else:
                    print(f"❌ Token validation failed: {response.status}")
                    return None
    except Exception as e:
        print(f"❌ Error validating token: {e}")
        return None

async def add_premium_roles(member: discord.Member) -> bool:
    """Tambahkan role premium ke user"""
    try:
        # Ambil role dari guild
        autopost_role = member.guild.get_role(AUTOPOST_ROLE_ID)
        customer_role = member.guild.get_role(CUSTOMER_ROLE_ID)
        
        roles_to_add = []
        
        if autopost_role:
            roles_to_add.append(autopost_role)
        
        if customer_role:
            roles_to_add.append(customer_role)
        
        if roles_to_add:
            await member.add_roles(*roles_to_add, reason="Premium user activation")
            print(f"✅ Added premium roles to {member.name}")
            return True
        else:
            print("⚠️ Premium roles not found in guild")
            return False
    except Exception as e:
        print(f"❌ Error adding roles: {e}")
        return False

# ========== WEBHOOK FUNCTIONS ==========
async def send_login_webhook(bot_name: str, status: str, user_info: Dict, action_user: discord.User, action: str = "Setup"):
    """Kirim webhook login"""
    if not WEBHOOK_URLS.get('LOGIN_WEBHOOK_URL'):
        print("⚠️ Login webhook URL not configured")
        return
    
    current_time = get_utc_now().strftime('%d %B %Y %H:%M:%S UTC')
    
    status_emoji = EMOJIS.get('ONLINE_EMOJI', '🟢') if status.lower() == "online" else EMOJIS.get('OFFLINE_EMOJI', '🔴')
    
    embed_data = {
        "embeds": [{
            "title": f"{EMOJIS.get('TITLE_EMOJI', '🤖')} **𝗔𝘂𝘁𝗼 𝗣𝗼𝘀𝘁 𝗟𝗼𝗴𝗶𝗻**",
            "color": 0x00FF00 if status.lower() == "online" else 0xFF0000,
            "fields": [
                {
                    "name": f"{EMOJIS.get('INFO_EMOJI', '📋')} **𝗗𝗲𝘁𝗮𝗶𝗹𝘀 𝗜𝗻𝗳𝗼**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} **Action:** {action}",
                    "inline": False
                },
                {
                    "name": f"{status_emoji} **𝗦𝘁𝗮𝘁𝘂𝘀 𝗕𝗼𝘁**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {status}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('BOT_EMOJI', '🤖')} **𝗕𝗼𝘁 𝗡𝗮𝗺𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {bot_name}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('USER_EMOJI', '👤')} **𝗨𝘀𝗲𝗿**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {user_info.get('global_name', 'Unknown')}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('TIME_EMOJI', '⏰')} **𝗧𝗶𝗺𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {current_time}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "𝗔𝘂𝘁𝗼 𝗣𝗼𝘀𝘁 𝗕𝘆 Vechnost"
            }
        }],
        "username": "Vechnost - Autopost",
        "avatar_url": "https://cdn.discordapp.com/attachments/1452678223094747240/1452767072198070382/banner.gif"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URLS['LOGIN_WEBHOOK_URL'],
                json=embed_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status in [200, 204]:
                    print(f"✅ Login webhook sent for {bot_name}")
                else:
                    print(f"❌ Webhook failed: {response.status}")
    except Exception as e:
        print(f"❌ Error sending webhook: {e}")

async def send_log_webhook(bot_name: str, channel_id: str, status: str, user_info: Dict, message: str = ""):
    """Kirim webhook log"""
    if not WEBHOOK_URLS.get('LOG_WEBHOOK_URL'):
        return
    
    current_time = get_utc_now().strftime('%d %B %Y %H:%M:%S UTC')
    
    if status.lower() == "success":
        status_emoji = EMOJIS.get('SUCCESS_EMOJI', '✅')
        embed_color = 0x00FF00
    else:
        status_emoji = EMOJIS.get('FAILED_EMOJI', '❌')
        embed_color = 0xFF0000
    
    embed_data = {
        "embeds": [{
            "title": f"{EMOJIS.get('TITLE_EMOJI', '🤖')} **𝗔𝘂𝘁𝗼 𝗣𝗼𝘀𝘁 𝗟𝗼𝗴**",
            "color": embed_color,
            "fields": [
                {
                    "name": f"{status_emoji} **𝗦𝘁𝗮𝘁𝘂𝘀**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {status}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('BOT_EMOJI', '🤖')} **𝗕𝗼𝘁**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {bot_name}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('USER_EMOJI', '👤')} **𝗨𝘀𝗲𝗿**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} <@{user_info.get('id', '')}>",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('TIME_EMOJI', '⏰')} **𝗧𝗶𝗺𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {current_time}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('CHANNEL_EMOJI', '📺')} **𝗖𝗵𝗮𝗻𝗻𝗲𝗹**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} <#{channel_id}>",
                    "inline": True
                },
                {
                    "name": f"{status_emoji} **𝗠𝗲𝘀𝘀𝗮𝗴𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {message[:100]}{'...' if len(message) > 100 else ''}",
                    "inline": False
                }
            ],
            "footer": {
                "text": "𝗔𝘂𝘁𝗼 𝗣𝗼𝘀𝘁 𝗕𝘆 Vechnost "
            }
        }],
        "username": "Vechnost - Logs"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URLS['LOG_WEBHOOK_URL'],
                json=embed_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status not in [200, 204]:
                    print(f"❌ Log webhook failed: {response.status}")
    except Exception as e:
        print(f"❌ Error sending log webhook: {e}")

# ========== TASK MANAGEMENT ==========
active_tasks = {}

async def send_message_to_channel(token: str, channel_id: str, message: str) -> Dict[str, Any]:
    """Kirim pesan ke channel menggunakan USER TOKEN"""
    headers = {
        'Authorization': token.strip(),
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    payload = {'content': message}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'https://discord.com/api/v10/channels/{channel_id}/messages',
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                
                if response.status == 200:
                    return {'success': True, 'status': response.status}
                elif response.status == 429:
                    # Rate limit handling
                    try:
                        data = await response.json()
                        retry_after = data.get('retry_after', 5)
                        print(f"⏳ Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        return await send_message_to_channel(token, channel_id, message)
                    except:
                        await asyncio.sleep(5)
                        return await send_message_to_channel(token, channel_id, message)
                else:
                    error_text = await response.text()[:200]
                    return {
                        'success': False,
                        'status': response.status,
                        'error': error_text
                    }
                    
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def autopost_task(bot_id: str, config: dict):
    """Main autopost task - Railway Optimized"""
    if not isinstance(config, dict):
        return
    
    bot_name = config.get('name', 'Unknown')
    guild_id = config.get('guild_id', '')
    user_id = config.get('setup_by', 0)
    
    print(f"🚀 Starting autopost task: {bot_name} (User: {user_id})")
    
    # Variables untuk tracking
    first_run = True
    last_premium_check = get_utc_now()
    
    while config.get('is_running', False):
        try:
            # Check premium status every hour
            current_time = get_utc_now()
            if (current_time - last_premium_check).total_seconds() >= 3600:
                is_premium, days_left, _, _ = check_user_premium(user_id)
                if not is_premium and user_id not in ADMIN_IDS:
                    print(f"⏰ Premium expired for user {user_id}, stopping bot {bot_name}")
                    config['is_running'] = False
                    
                    # Update in database
                    user_bots = get_user_bots(guild_id, user_id)
                    for bot in user_bots:
                        if isinstance(bot, dict) and bot.get('name') == bot_name:
                            bot['is_running'] = False
                            save_user_bots(guild_id, user_id, user_bots)
                            break
                    
                    # Remove from active tasks
                    if bot_id in active_tasks:
                        del active_tasks[bot_id]
                    
                    break
                last_premium_check = current_time
            
            # Only wait if NOT first run
            if not first_run:
                delay_minutes = config.get('delay', 30)
                print(f"⏰ [{bot_name}] Waiting {delay_minutes} minutes before next send...")
                await asyncio.sleep(delay_minutes * 60)
            else:
                first_run = False
                print(f"🚀 [{bot_name}] First run - sending immediately!")
            
            # Get config
            token = config.get('token', '')
            channels = config.get('channels', [])
            message = config.get('message', '')
            
            if not token or not channels or not message:
                print(f"❌ [{bot_name}] Invalid config, stopping")
                config['is_running'] = False
                break
            
            # Send to all channels
            for idx, channel_id in enumerate(channels):
                if not config.get('is_running', False):
                    print(f"🛑 [{bot_name}] Stopped during execution")
                    break
                
                print(f"📤 [{bot_name}] Sending to channel {idx+1}/{len(channels)}: {channel_id}")
                result = await send_message_to_channel(token, channel_id, message)
                
                if result.get('success'):
                    # Update statistics
                    user_bots = get_user_bots(guild_id, user_id)
                    for bot in user_bots:
                        if isinstance(bot, dict) and bot.get('name') == bot_name:
                            bot['total_sent'] = bot.get('total_sent', 0) + 1
                            bot['last_updated'] = format_datetime(get_utc_now())
                            save_user_bots(guild_id, user_id, user_bots)
                            break
                    
                    # Send success webhook
                    await send_log_webhook(
                        bot_name=bot_name,
                        channel_id=channel_id,
                        status="Success",
                        user_info=config.get('user_info', {}),
                        message=f"Message successfully sent to <#{channel_id}>"
                    )
                else:
                    # Send error webhook
                    await send_log_webhook(
                        bot_name=bot_name,
                        channel_id=channel_id,
                        status="Failed",
                        user_info=config.get('user_info', {}),
                        message=f"Failed to send: {result.get('error', 'Unknown error')}"
                    )
                
                # Wait between channels (avoid rate limit)
                if idx < len(channels) - 1:
                    await asyncio.sleep(10)  # 10 detik antar channel
            
            print(f"✅ [{bot_name}] Cycle completed, waiting for next cycle")
            
        except asyncio.CancelledError:
            print(f"🛑 [{bot_name}] Task cancelled")
            break
        except Exception as e:
            print(f"⚠️ [{bot_name}] Error in task: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry

# ========== DISCORD UI COMPONENTS ==========
class PremiumCodeModal(Modal, title='🔑 VERIFIKASI PREMIUM'):
    """Modal untuk input kode premium"""
    premium_code = TextInput(
        label='MASUKKAN KODE PREMIUM ANDA',
        placeholder='Contoh: VECHNOST-ABC123DEF456GHI',
        style=discord.TextStyle.short,
        required=True,
        max_length=50
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        code = self.premium_code.value.strip().upper()
        valid, message = await validate_premium_code(code, interaction.user.id, interaction.guild)
        
        if not valid:
            embed = discord.Embed(
                title="❌ **Validasi Gagal**",
                description=message,
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Add premium roles
        await add_premium_roles(interaction.user)
        
        is_premium, days_left, plan, _ = check_user_premium(interaction.user.id)
        
        embed = discord.Embed(
            title="✅ **PREMIUM AKTIF**",
            description=f"Kode premium berhasil diaktifkan! Role premium telah ditambahkan.",
            color=0x00FF00
        )
        
        embed.add_field(name="📅 **Durasi**", value=f"{plan}", inline=True)
        embed.add_field(name="⏳ **Sisa Waktu**", value=f"{days_left} hari", inline=True)
        embed.add_field(name="🤖 **Limit Bot**", value="5 bot", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class SetupModal(Modal, title='⚙️ SETUP AUTOPOST BOT'):
    """Modal untuk setup bot"""
    def __init__(self, edit_bot_name: str = None):
        super().__init__(timeout=300)
        self.edit_bot_name = edit_bot_name
        
        if edit_bot_name:
            self.title = f'⚙️ EDIT BOT: {edit_bot_name}'
    
    token = TextInput(
        label='USER TOKEN',
        placeholder='Masukkan USER TOKEN Discord...',
        style=discord.TextStyle.short,
        required=True,
        max_length=100
    )
    
    bot_name = TextInput(
        label='NAMA BOT (BEBAS)',
        placeholder='Contoh: Bot_1, BotPromo, dll...',
        style=discord.TextStyle.short,
        required=True,
        max_length=50
    )
    
    channels = TextInput(
        label='CHANNEL ID (MAX 20)',
        placeholder='Pisahkan dengan koma atau baris baru',
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    message = TextInput(
        label='MESSAGE',
        placeholder='Masukkan pesan yang akan dikirim...',
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    
    delay = TextInput(
        label='DELAY (MENIT)',
        placeholder='Contoh: 30 (untuk 30 menit)',
        style=discord.TextStyle.short,
        required=True,
        max_length=4,
        default='30'
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # CEK PREMIUM/ADMIN
        if interaction.user.id not in ADMIN_IDS:
            is_premium, _, _, _ = check_user_premium(interaction.user.id)
            if not is_premium:
                embed = discord.Embed(
                    title="❌ **AKSES DITOLAK**",
                    description="Anda harus memiliki kode premium terlebih dahulu!",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        # CEK LIMIT BOT
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        bot_limit = 5
        
        if interaction.user.id not in ADMIN_IDS and len(user_bots) >= bot_limit:
            embed = discord.Embed(
                title="❌ **LIMIT BOT TERCAPAI**",
                description=f"Anda sudah memiliki {len(user_bots)}/{bot_limit} bot.",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Validasi input
        channel_ids = parse_channel_ids(self.channels.value)
        if not channel_ids:
            embed = discord.Embed(
                title="❌ **INPUT TIDAK VALID**",
                description="Tidak ada Channel ID yang valid ditemukan!",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        token = self.token.value.strip()
        user_info = await get_user_info_from_token(token)
        if not user_info:
            embed = discord.Embed(
                title="❌ **TOKEN TIDAK VALID**",
                description="Token Discord tidak valid atau sudah expired!",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        bot_name = self.bot_name.value.strip()
        
        # Cek duplikasi nama
        if not self.edit_bot_name:
            for bot_data in user_bots:
                if isinstance(bot_data, dict) and bot_data.get('name') == bot_name:
                    embed = discord.Embed(
                        title="❌ **NAMA BOT DUPLIKAT**",
                        description=f"Nama bot '{bot_name}' sudah digunakan!",
                        color=0xFF0000
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
        
        # Buat/update config
        bot_config = {
            'token': token,
            'name': bot_name,
            'channels': channel_ids,
            'message': self.message.value,
            'delay': int(self.delay.value) if self.delay.value.isdigit() else 30,
            'is_running': False,
            'setup_by': interaction.user.id,
            'setup_by_name': interaction.user.name,
            'user_info': user_info,
            'guild_id': guild_id,
            'last_updated': format_datetime(get_utc_now()),
            'total_sent': 0
        }
        
        # Jika edit mode, replace bot lama
        if self.edit_bot_name:
            new_user_bots = []
            for bot in user_bots:
                if isinstance(bot, dict) and bot.get('name') == self.edit_bot_name:
                    bot_config['is_running'] = bot.get('is_running', False)
                    bot_config['total_sent'] = bot.get('total_sent', 0)
                    
                    if bot_config['is_running']:
                        old_bot_id = f"{guild_id}_{interaction.user.id}_{self.edit_bot_name}"
                        new_bot_id = f"{guild_id}_{interaction.user.id}_{bot_name}"
                        
                        if old_bot_id in active_tasks:
                            active_tasks[old_bot_id].cancel()
                            del active_tasks[old_bot_id]
                        
                        task = asyncio.create_task(autopost_task(new_bot_id, bot_config))
                        active_tasks[new_bot_id] = task
                    
                    new_user_bots.append(bot_config)
                else:
                    new_user_bots.append(bot)
        else:
            user_bots.append(bot_config)
            new_user_bots = user_bots
        
        save_user_bots(guild_id, interaction.user.id, new_user_bots)
        
        # PREVIEW MESSAGE
        preview_text = self.message.value[:500] + "..." if len(self.message.value) > 500 else self.message.value
        preview_embed = discord.Embed(
            title="📝 **PREVIEW MESSAGE**",
            description=f"```\n{preview_text}\n```",
            color=0x00FF00
        )
        preview_embed.add_field(name="🤖 **Bot Name**", value=bot_name, inline=True)
        preview_embed.add_field(name="📺 **Channels**", value=len(channel_ids), inline=True)
        preview_embed.add_field(name="⏰ **Delay**", value=f"{self.delay.value} menit", inline=True)
        
        # Kirim webhook login
        await send_login_webhook(
            bot_name=bot_name,
            status="Online",
            user_info=user_info,
            action_user=interaction.user,
            action="Edit" if self.edit_bot_name else "Setup"
        )
        
        await interaction.followup.send(embed=preview_embed, ephemeral=True)

class SettingsView(View):
    """View untuk settings dengan dropdown"""
    def __init__(self, user_bots: list):
        super().__init__(timeout=180)
        self.user_bots = user_bots
        
        # Buat Select dropdown
        self.select = Select(
            placeholder="Pilih bot yang ingin dilihat detailnya...",
            options=[
                discord.SelectOption(
                    label=bot.get('name', 'Unknown'),
                    description=f"{len(bot.get('channels', []))} channels, Delay: {bot.get('delay', 30)}m",
                    value=str(i)
                ) for i, bot in enumerate(user_bots) if isinstance(bot, dict)
            ]
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
    
    async def on_select(self, interaction: discord.Interaction):
        bot_index = int(self.select.values[0])
        selected_bot = self.user_bots[bot_index]
        
        # Buat embed detail bot
        embed = discord.Embed(
            title=f"{EMOJIS.get('SETTING_EMOJI', '⚙️')} **𝚂𝚎𝚝𝚝𝚒𝚗𝚐**",
            color=0x5865F2
        )
        
        bot_status = "🟢 ONLINE" if selected_bot.get('is_running', False) else "🔴 OFFLINE"
        embed.add_field(
            name=f"{EMOJIS.get('BOT_EMOJI', '🤖')} ၊| 𝖡𝗈𝗍",
            value=f"{EMOJIS.get('ARROW_EMOJI', '➡️')} **{selected_bot.get('name', 'Unknown')}** - {bot_status}",
            inline=False
        )
        
        # Channel List
        channels_text = ""
        channels = selected_bot.get('channels', [])
        for i, channel_id in enumerate(channels[:18]):
            prefix = "├" if i < len(channels) - 1 else "╰┈"
            channels_text += f"{prefix}{EMOJIS.get('ARROW_EMOJI', '➡️')} <#{channel_id}>\n"
        
        if len(channels) > 18:
            channels_text += f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} ... dan {len(channels) - 18} lainnya"
        
        if not channels_text:
            channels_text = f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} Tidak ada channel"
        
        embed.add_field(
            name=f"{EMOJIS.get('CHANNEL_EMOJI', '📺')} ၊| 𝖢𝗁𝖺𝗇𝗇𝖾𝗅",
            value=channels_text,
            inline=False
        )
        
        # Message Preview
        message = selected_bot.get('message', '')
        if len(message) > 100:
            message_preview = message[:100] + "..."
        else:
            message_preview = message
        
        embed.add_field(
            name=f"💬 ၊| 𝖬𝖾𝗌𝗌𝖺𝗀𝖾",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} ```{message_preview}```",
            inline=False
        )
        
        # Delay
        embed.add_field(
            name=f"{EMOJIS.get('TIME_EMOJI', '⏰')} ၊| 𝖣𝖾𝗅𝖺𝗒",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {selected_bot.get('delay', 30)} menit",
            inline=True
        )
        
        # Total Sent
        embed.add_field(
            name=f"{EMOJIS.get('SUCCESS_EMOJI', '✅')} ၊| 𝖳𝗈𝗍𝖺𝗅 𝖲𝖾𝗇𝗍",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {selected_bot.get('total_sent', 0)} pesan",
            inline=True
        )
        
        # Last Updated
        embed.add_field(
            name=f"{EMOJIS.get('TIME_EMOJI', '⏰')} ၊| 𝖫𝖺𝗌𝗍 𝖴𝗉𝖽𝖺𝗍𝖾𝖽",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {selected_bot.get('last_updated', 'N/A')}",
            inline=True
        )
        
        # Tambahkan tombol edit dan delete
        action_view = View(timeout=180)
        
        edit_button = Button(label='Edit', style=discord.ButtonStyle.primary, emoji='✏️')
        delete_button = Button(label='Hapus', style=discord.ButtonStyle.danger, emoji='🗑️')
        
        async def edit_callback(interaction: discord.Interaction):
            edit_modal = SetupModal(edit_bot_name=selected_bot.get('name'))
            
            # Isi field dengan data lama
            edit_modal.token.default = selected_bot.get('token', '')
            edit_modal.bot_name.default = selected_bot.get('name', '')
            edit_modal.channels.default = ', '.join(selected_bot.get('channels', []))
            edit_modal.message.default = selected_bot.get('message', '')
            edit_modal.delay.default = str(selected_bot.get('delay', 30))
            
            await interaction.response.send_modal(edit_modal)
        
        async def delete_callback(interaction: discord.Interaction):
            confirm_embed = discord.Embed(
                title="⚠️ **KONFIRMASI HAPUS**",
                description=f"Apakah Anda yakin ingin menghapus bot **{selected_bot.get('name', 'Unknown')}**?",
                color=0xFFA500
            )
            
            confirm_view = View(timeout=30)
            
            yes_button = Button(label='Ya, Hapus', style=discord.ButtonStyle.danger, emoji='✅')
            no_button = Button(label='Batal', style=discord.ButtonStyle.secondary, emoji='❌')
            
            async def yes_callback(interaction: discord.Interaction):
                guild_id = str(interaction.guild_id)
                user_bots = get_user_bots(guild_id, interaction.user.id)
                
                new_user_bots = []
                for bot in user_bots:
                    if isinstance(bot, dict) and bot.get('name') != selected_bot.get('name'):
                        new_user_bots.append(bot)
                    else:
                        # Stop task jika sedang running
                        if bot.get('is_running', False):
                            bot_id = f"{guild_id}_{interaction.user.id}_{selected_bot.get('name')}"
                            if bot_id in active_tasks:
                                active_tasks[bot_id].cancel()
                                del active_tasks[bot_id]
                
                save_user_bots(guild_id, interaction.user.id, new_user_bots)
                
                success_embed = discord.Embed(
                    title="✅ **BOT DIHAPUS**",
                    description=f"Bot **{selected_bot.get('name', 'Unknown')}** berhasil dihapus!",
                    color=0x00FF00
                )
                
                await interaction.response.edit_message(embed=success_embed, view=None)
            
            async def no_callback(interaction: discord.Interaction):
                await interaction.response.edit_message(content="❌ Penghapusan dibatalkan.", embed=None, view=None)
            
            yes_button.callback = yes_callback
            no_button.callback = no_callback
            
            confirm_view.add_item(yes_button)
            confirm_view.add_item(no_button)
            
            await interaction.response.send_message(embed=confirm_embed, view=confirm_view, ephemeral=True)
        
        edit_button.callback = edit_callback
        delete_button.callback = delete_callback
        
        action_view.add_item(edit_button)
        action_view.add_item(delete_button)
        
        await interaction.response.edit_message(embed=embed, view=action_view)

class AutopostView(View):
    """Main view dengan 6 tombol"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='🔑', row=0)
    async def premium_button(self, interaction: discord.Interaction, button: Button):
        modal = PremiumCodeModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='⚙️', row=0)
    async def setup_button(self, interaction: discord.Interaction, button: Button):
        if not has_permission(interaction.user):
            embed = discord.Embed(
                title="❌ **AKSES DITOLAK**",
                description="Anda harus premium untuk menggunakan fitur ini.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        modal = SetupModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='⚙️', row=0)
    async def settings_button(self, interaction: discord.Interaction, button: Button):
        if not has_permission(interaction.user):
            embed = discord.Embed(
                title="❌ **AKSES DITOLAK**",
                description="Anda harus premium untuk menggunakan fitur ini.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        
        if not user_bots:
            embed = discord.Embed(
                title="❌ **BELUM ADA BOT**",
                description="Klik tombol **SETUP** untuk membuat bot pertama.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        view = SettingsView(user_bots)
        
        embed = discord.Embed(
            title=f"{EMOJIS.get('SETTING_EMOJI', '⚙️')} **𝚂𝚎𝚝𝚝𝚒𝚗𝚐**",
            description="Pilih bot dari dropdown di bawah:",
            color=0x5865F2
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='▶️', row=0)
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if not has_permission(interaction.user):
            embed = discord.Embed(
                title="❌ **AKSES DITOLAK**",
                description="Anda harus premium untuk menggunakan fitur ini.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        
        if not user_bots:
            embed = discord.Embed(
                title="❌ **BELUM ADA BOT**",
                description="Klik tombol **SETUP** untuk membuat bot pertama.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        stopped_bots = [b for b in user_bots if isinstance(b, dict) and not b.get('is_running', False)]
        
        if not stopped_bots:
            embed = discord.Embed(
                title="✅ **SEMUA BOT BERJALAN**",
                description="Semua bot Anda sudah berjalan!",
                color=0x00FF00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        started_count = 0
        for bot_config in stopped_bots:
            bot_name = bot_config.get('name', 'Unknown')
            bot_config['is_running'] = True
            bot_id = f"{guild_id}_{interaction.user.id}_{bot_name}"
            
            task = asyncio.create_task(autopost_task(bot_id, bot_config))
            active_tasks[bot_id] = task
            
            await send_login_webhook(
                bot_name=bot_name,
                status="Online",
                user_info=bot_config.get('user_info', {}),
                action_user=interaction.user,
                action="Start"
            )
            
            started_count += 1
        
        save_user_bots(guild_id, interaction.user.id, user_bots)
        
        embed = discord.Embed(
            title="✅ **BOT DIMULAI**",
            description=f"**{started_count} bot** berhasil dimulai!",
            color=0x00FF00
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='⏹️', row=0)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        if not has_permission(interaction.user):
            embed = discord.Embed(
                title="❌ **AKSES DITOLAK**",
                description="Anda harus premium untuk menggunakan fitur ini.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        
        if not user_bots:
            embed = discord.Embed(
                title="❌ **BELUM ADA BOT**",
                description="Klik tombol **SETUP** untuk membuat bot pertama.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        running_bots = [b for b in user_bots if isinstance(b, dict) and b.get('is_running', False)]
        
        if not running_bots:
            embed = discord.Embed(
                title="🛑 **TIDAK ADA BOT BERJALAN**",
                description="Tidak ada bot yang sedang berjalan.",
                color=0xFFA500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        stopped_count = 0
        for bot_config in running_bots:
            bot_name = bot_config.get('name', 'Unknown')
            bot_config['is_running'] = False
            
            bot_id = f"{guild_id}_{interaction.user.id}_{bot_name}"
            if bot_id in active_tasks:
                active_tasks[bot_id].cancel()
                del active_tasks[bot_id]
            
            await send_login_webhook(
                bot_name=bot_name,
                status="Offline",
                user_info=bot_config.get('user_info', {}),
                action_user=interaction.user,
                action="Stop"
            )
            
            stopped_count += 1
        
        save_user_bots(guild_id, interaction.user.id, user_bots)
        
        embed = discord.Embed(
            title="🛑 **BOT DIHENTIKAN**",
            description=f"**{stopped_count} bot** berhasil dihentikan!",
            color=0xFF0000
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='📊', row=1)
    async def status_button(self, interaction: discord.Interaction, button: Button):
        if not has_permission(interaction.user):
            embed = discord.Embed(
                title="❌ **AKSES DITOLAK**",
                description="Anda harus premium untuk menggunakan fitur ini.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        
        if not user_bots:
            embed = discord.Embed(
                title="❌ **BELUM ADA BOT**",
                description="Klik tombol **SETUP** untuk membuat bot pertama.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Cek status premium user
        is_premium, days_left, plan, _, expires_at_str = check_user_premium(interaction.user.id)
        
        # Hitung total channel dan success
        all_channels = set()
        total_sent = 0
        
        for bot in user_bots:
            if isinstance(bot, dict):
                for channel in bot.get('channels', []):
                    all_channels.add(channel)
                total_sent += bot.get('total_sent', 0)
        
        # Buat embed status
        embed = discord.Embed(
            title=f"**𝚂𝚃𝙰𝚃𝚄𝚂 𝙱𝙾𝚃**",
            color=0x5865F2,
            timestamp=get_utc_now()
        )
        
        # Status bot
        running_count = sum(1 for b in user_bots if isinstance(b, dict) and b.get('is_running', False))
        total_count = len(user_bots)
        
        embed.add_field(
            name=f"{EMOJIS.get('BOT_EMOJI', '🤖')} ၊| 𝖡𝗈𝗍",
            value=f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} Total: {total_count} bot\n╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} Running: {running_count} bot",
            inline=False
        )
        
        # Channel
        embed.add_field(
            name=f"{EMOJIS.get('CHANNEL_EMOJI', '📺')} ၊| 𝖢𝗁𝖺𝗇𝗇𝖾𝗅",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {len(all_channels)} channel",
            inline=True
        )
        
        # Success
        embed.add_field(
            name=f"{EMOJIS.get('SUCCESS_EMOJI', '✅')} ၊| 𝖲𝗎𝖼𝖼𝖾𝗌",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {total_sent} pesan",
            inline=True
        )
        
        # Premium Status
        if is_premium and expires_at_str:
            expires_at = parse_datetime(expires_at_str)
            now = get_utc_now()
            
            if now < expires_at:
                delta = expires_at - now
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                seconds = delta.seconds % 60
                
                premium_info = (
                    f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} {plan}\n"
                    f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} {days} hari\n"
                    f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} {hours} jam\n"
                    f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} {minutes} menit\n"
                    f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {seconds} detik"
                )
            else:
                premium_info = f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} Expired"
        else:
            premium_info = f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} Belum Premium"
        
        embed.add_field(
            name=f"{EMOJIS.get('ACCESS_EMOJI', '🔑')} ၊| 𝖠𝖼𝖼𝖾𝗌𝗌",
            value=premium_info,
            inline=False
        )
        
        embed.set_footer(text="Status Bot • UTC Time")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== EMBED CREATION ==========
def create_autopost_embed() -> discord.Embed:
    """Buat embed utama untuk panel autopost"""
    embed = discord.Embed(
        title="𝚅𝙴𝙲𝙷𝙽𝙾𝚂𝚃 - 𝙰𝚄𝚃𝙾𝙿𝙾𝚂𝚃",
        description="**Panel kontrol autoposting untuk Discord**",
        color=0x5865F2
    )
    
    # ACCESS SECTION
    embed.add_field(
        name=f"🔑 ၊| 𝖠𝖼𝖼𝖾𝗌𝗌",
        value=(
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} **1 DAY** - Rp 5.000\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} **7 DAY** - Rp 10.000\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} **30 DAY** - Rp 25.000\n"
            f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} **LIFETIME** - Rp 40.000"
        ),
        inline=False
    )
    
    # SETUP SECTION
    embed.add_field(
        name=f"⚙️ ၊| 𝖲𝖾𝗍𝗎𝗉",
        value=(
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} TOKEN Discord\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} NAMA BOT\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} CHANNEL ID\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} MESSAGE\n"
            f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} DELAY"
        ),
        inline=False
    )
    
    # SETTING SECTION
    embed.add_field(
        name=f"⚙️ ၊| 𝖲𝖾𝗍𝗍𝗂𝗇𝗀",
        value=(
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} Edit bot\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} Hapus bot\n"
            f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} Lihat detail"
        ),
        inline=False
    )
    
    # PLAY & STOP SECTION
    embed.add_field(
        name=f"▶️ ၊| 𝖯𝗅𝖺𝗒",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} START BOT",
        inline=True
    )
    
    embed.add_field(
        name=f"⏹️ ၊| 𝖲𝗍𝗈𝗉",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} STOP BOT",
        inline=True
    )
    
    # STATUS SECTION
    embed.add_field(
        name=f"📊 ၊| 𝖲𝗍𝖺𝗍𝗎𝗌",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} CHECK BOT",
        inline=True
    )
    
    # INFO SECTION
    embed.add_field(
        name=f"📋 ၊| 𝖨𝗇𝖿𝗈",
        value=(
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} **24/7 Hosting:** Railway\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} **Limit Bot:** 5 bot/user\n"
            f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} **Support:** Vechnost Community"
        ),
        inline=False
    )
    
    # Banner image
    embed.set_image(url="https://cdn.discordapp.com/attachments/1452678223094747240/1452767072198070382/banner.gif")
    
    # Footer
    embed.set_footer(text="AutoPost By Vechnost Community • Powered by Railway")
    
    return embed

# ========== SLASH COMMANDS ==========
@tree.command(name="autopost", description="Tampilkan panel kontrol autoposting")
@app_commands.checks.has_permissions(administrator=True)
async def autopost_command(interaction: discord.Interaction):
    """Command utama untuk menampilkan panel"""
    if interaction.user.id not in ADMIN_IDS:
        embed = discord.Embed(
            title="🔒 **Akses Ditolak**",
            description="Hanya admin yang bisa menggunakan command ini!",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = create_autopost_embed()
    view = AutopostView()
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="create_code", description="Buat kode premium (Admin only)")
@app_commands.describe(
    duration="Durasi premium: 1d, 7d, 30d, lifetime",
    user="User yang akan dikirim kode (opsional)"
)
@app_commands.checks.has_permissions(administrator=True)
async def create_code(interaction: discord.Interaction, 
                     duration: str,
                     user: discord.User = None):
    
    if interaction.user.id not in ADMIN_IDS:
        embed = discord.Embed(
            title="🔒 **Akses Ditolak**",
            description="Hanya admin yang bisa menggunakan command ini!",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    duration_map = {
        "1d": 1,
        "7d": 7,
        "30d": 30,
        "lifetime": 9999
    }
    
    if duration not in duration_map:
        embed = discord.Embed(
            title="❌ **Duration Tidak Valid**",
            description="Pilihan: `1d`, `7d`, `30d`, `lifetime`",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    days = duration_map[duration]
    code_data = generate_premium_code(days, interaction.user.id)
    code = code_data["code"]
    
    data = load_premium_data()
    data["premium_codes"][code] = code_data
    save_premium_data(data)
    
    # Embed untuk admin
    admin_embed = discord.Embed(
        title="🎫 **PREMIUM CODE CREATED**",
        color=0x00FF00
    )
    
    admin_embed.add_field(name="🔑 **Code**", value=f"`{code}`", inline=False)
    admin_embed.add_field(name="⏰ **Duration**", value=f"{days} hari", inline=True)
    admin_embed.add_field(name="📅 **Expires**", value=code_data["expires_at"], inline=True)
    
    await interaction.response.send_message(embed=admin_embed, ephemeral=True)
    
    # Kirim ke user jika disebutkan
    if user:
        try:
            user_embed = discord.Embed(
                title="🔑 **PREMIUM ACCESS CODE**",
                description=f"Kode premium untuk {user.mention}",
                color=0x5865F2
            )
            
            user_embed.add_field(name="🎫 **Code**", value=f"```{code}```", inline=False)
            user_embed.add_field(name="⏳ **Duration**", value=f"{days} hari", inline=True)
            user_embed.add_field(name="📅 **Expires**", value=code_data["expires_at"], inline=True)
            user_embed.add_field(
                name="🚀 **Cara Pakai**",
                value="1. Klik tombol **ACCESS** di panel\n2. Masukkan kode di atas\n3. Premium akan aktif otomatis",
                inline=False
            )
            
            await user.send(embed=user_embed)
            
            success_embed = discord.Embed(
                title="✅ **Kode Dikirim**",
                description=f"Kode premium berhasil dikirim ke DM {user.mention}",
                color=0x00FF00
            )
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ **Gagal Mengirim DM**",
                description=f"Tidak bisa mengirim DM ke {user.mention}",
                color=0xFF0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

# ========== DISCORD EVENT HANDLERS ==========
@bot.event
async def on_ready():
    """Event ketika bot siap"""
    print("=" * 60)
    print(f"🤖 Controller Bot: {bot.user.name}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"🌐 Guilds: {len(bot.guilds)}")
    print(f"🕐 UTC Time: {get_utc_now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Sync commands
    try:
        synced = await tree.sync()
        print(f"✅ Commands synced: {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
    
    # Load data
    load_data()
    
    # Restart semua bot yang sedang running
    task_count = 0
    for guild_id, users_data in AUTOPOST_DATA.items():
        if not isinstance(users_data, dict):
            continue
            
        for user_id_str, bots in users_data.items():
            if not isinstance(bots, list):
                continue
                
            for bot_config in bots:
                if not isinstance(bot_config, dict):
                    continue
                    
                if bot_config.get('is_running', False):
                    bot_name = bot_config.get('name', 'Unknown')
                    bot_id = f"{guild_id}_{user_id_str}_{bot_name}"
                    
                    # Cek premium status
                    try:
                        user_id = int(user_id_str)
                        if user_id != 0 and user_id not in ADMIN_IDS:
                            is_premium, _, _, _ = check_user_premium(user_id)
                            if not is_premium:
                                print(f"⚠️ User {user_id} premium expired, stopping {bot_name}")
                                bot_config['is_running'] = False
                                continue
                    except:
                        pass
                    
                    # Validasi config
                    required = ['token', 'channels', 'message', 'delay']
                    missing = [f for f in required if f not in bot_config]
                    
                    if missing:
                        print(f"❌ Missing fields for {bot_name}: {missing}")
                        bot_config['is_running'] = False
                        continue
                    
                    bot_config['guild_id'] = guild_id
                    task = asyncio.create_task(autopost_task(bot_id, bot_config))
                    active_tasks[bot_id] = task
                    task_count += 1
                    print(f"🔄 Restarted: {bot_name}")
    
    print(f"✅ {task_count} bot task(s) restarted")
    
    # Set bot presence
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="/autopost 24/7"
        ),
        status=discord.Status.online
    )
    
    print("✅ Bot is ready for use!")
    print("=" * 60)

@bot.event
async def on_guild_join(guild):
    """Event ketika bot join server baru"""
    print(f"🎉 Joined new guild: {guild.name} ({guild.id})")
    
    # Kirim welcome message
    try:
        system_channel = guild.system_channel
        if system_channel and system_channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="🤖 Vechnost AutoPost Bot",
                description=(
                    "Terima kasih telah menambahkan Vechnost AutoPost Bot!\n\n"
                    "**Fitur Utama:**\n"
                    "• 🔑 Premium Code System\n"
                    "• ⚙️ AutoPost Setup\n"
                    "• 📨 Multi-Channel Posting\n"
                    "• 📊 Real-time Status\n"
                    "• 🔔 Discord Webhook Logs\n\n"
                    "**Cara Mulai:**\n"
                    "1. Gunakan command `/autopost`\n"
                    "2. Klik tombol **ACCESS** untuk premium\n"
                    "3. Setup bot pertama Anda!\n\n"
                    "**Support:** Vechnost Community"
                ),
                color=0x5865F2
            )
            await system_channel.send(embed=embed)
    except:
        pass

# ========== MAIN EXECUTION ==========
if __name__ == "__main__":
    """Main entry point untuk Railway"""
    
    print("🚀 Initializing Vechnost AutoPost Bot for Railway...")
    
    # Start web server untuk Railway health checks
    keep_alive()
    
    # Load data
    load_data()
    
    # Validasi token
    if not BOT_TOKEN:
        print("=" * 60)
        print("❌ CRITICAL ERROR: BOT_TOKEN not found!")
        print("=" * 60)
        print("SOLUTION: Set BOT_TOKEN in Railway Variables:")
        print("1. Go to Railway Dashboard")
        print("2. Select your project")
        print("3. Click 'Variables' tab")
        print("4. Add: BOT_TOKEN = your_discord_bot_token")
        print("5. Redeploy the project")
        print("=" * 60)
        sys.exit(1)
    
    print("✅ Bot configuration loaded")
    print(f"🌐 Web server: http://0.0.0.0:{os.environ.get('PORT', 8080)}")
    print(f"📊 Health check: /health")
    print(f"📈 Status: /status")
    print("🔄 Starting Discord bot...")
    
    # Run bot dengan error handling
    try:
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid BOT_TOKEN")
        print("Please check your bot token in Railway Variables")
    except discord.PrivilegedIntentsRequired:
        print("❌ ERROR: Privileged Intents not enabled")
        print("Enable them at: https://discord.com/developers/applications")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        print("The bot will restart automatically on Railway")
    
    print("👋 Bot shutdown complete")
