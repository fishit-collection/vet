import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput, Select
from discord import PartialEmoji
import json
import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

## ========== WEB SERVER UNTUK RAILWAY ==========
from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "🤖 Vechnost Bot is running on Railway!"

def run():
    # Railway memberikan PORT melalui environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# Import premium system
try:
    from premium_system import *
except ImportError:
    print("⚠️ premium_system.py not found, premium features disabled")
    async def validate_premium_code(*args): return False, "Premium system not loaded"
    def check_user_premium(user_id): return False, 0, "none", 0
    def get_user_bot_limit(user_id): return 0
    def generate_premium_code(*args): return {}
    def load_premium_data(): return {"premium_codes": {}, "user_subscriptions": {}}
    def save_premium_data(data): pass

# Load environment variables
load_dotenv()

# ========== KONFIGURASI ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Database
AUTOPOST_DATA = {}
DATA_FILE = "autopost_data.json"
PORTAL_FILE = "portal.json"

# Role IDs untuk ditambahkan otomatis
AUTOPOST_ROLE_ID = 1456729990824726528
CUSTOMER_ROLE_ID = 1452721209480450058

# Load portal.json
WEBHOOK_URLS = {}
EMOJIS = {}

try:
    if os.path.exists(PORTAL_FILE):
        with open(PORTAL_FILE, 'r', encoding='utf-8') as f:
            portal_data = json.load(f)
            WEBHOOK_URLS = portal_data.get('WEBHOOK', {})
            EMOJIS = portal_data.get('EMOJIS', {})
            print("✅ Loaded portal.json")
except Exception as e:
    print(f"❌ Error loading portal.json: {e}")

# Load env variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')

ADMIN_IDS = set()
if ADMIN_IDS_STR:
    for id_str in ADMIN_IDS_STR.split(','):
        try:
            ADMIN_IDS.add(int(id_str.strip()))
        except ValueError:
            pass

print(f"🤖 Admin IDs: {ADMIN_IDS}")

# ========== FUNGSI UTILITY ==========
def load_data():
    """Load data dari file JSON dengan struktur per user"""
    global AUTOPOST_DATA
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Konversi struktur lama ke baru jika diperlukan
                new_data = {}
                for guild_id, value in data.items():
                    if isinstance(value, list):
                        new_data[guild_id] = {0: value}
                    else:
                        new_data[guild_id] = value
                AUTOPOST_DATA = new_data
                print(f"✅ Loaded data: {len(AUTOPOST_DATA)} guild(s)")
        else:
            AUTOPOST_DATA = {}
            save_data()
            print(f"📁 File {DATA_FILE} dibuat baru")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        AUTOPOST_DATA = {}

def save_data():
    """Simpan data ke file JSON"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(AUTOPOST_DATA, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error saving data: {e}")

def get_user_bots(guild_id: str, user_id: int) -> list:
    """Ambil daftar bot untuk user tertentu"""
    try:
        if guild_id in AUTOPOST_DATA:
            if str(user_id) in AUTOPOST_DATA[guild_id]:
                return AUTOPOST_DATA[guild_id][str(user_id)]
    except:
        pass
    return []

def save_user_bots(guild_id: str, user_id: int, bots: list):
    """Simpan daftar bot untuk user tertentu"""
    if guild_id not in AUTOPOST_DATA:
        AUTOPOST_DATA[guild_id] = {}
    AUTOPOST_DATA[guild_id][str(user_id)] = bots
    save_data()

def has_permission(member: discord.Member) -> bool:
    """Cek apakah user memiliki akses (admin atau premium)"""
    if member.id in ADMIN_IDS:
        return True
    
    # Cek status premium user
    is_premium, _, _, _ = check_user_premium(member.id)
    if is_premium:
        return True
    
    return False

def parse_channel_ids(text: str) -> List[str]:
    """Parse channel IDs dari text"""
    for sep in [',', ';', '|', ' ']:
        text = text.replace(sep, '\n')
    
    lines = text.split('\n')
    channel_ids = []
    
    for line in lines:
        line = line.strip()
        clean_id = ''.join(filter(str.isdigit, line))
        
        if clean_id and len(clean_id) >= 17:
            channel_ids.append(clean_id)
        
        if len(channel_ids) >= 20:
            break
    
    return channel_ids

async def get_user_info_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Dapatkan info user dari token USER"""
    headers = {
        'Authorization': token.strip(),
        'Content-Type': 'application/json'
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
                    return None
    except:
        return None

async def add_premium_roles(member: discord.Member):
    """Tambahkan role premium ke user"""
    try:
        # Ambil role dari guild
        autopost_role = member.guild.get_role(AUTOPOST_ROLE_ID)
        customer_role = member.guild.get_role(CUSTOMER_ROLE_ID)
        
        roles_to_add = []
        
        if autopost_role:
            roles_to_add.append(autopost_role)
            print(f"✅ Found autopost role: {autopost_role.name}")
        
        if customer_role:
            roles_to_add.append(customer_role)
            print(f"✅ Found customer role: {customer_role.name}")
        
        if roles_to_add:
            await member.add_roles(*roles_to_add, reason="Premium user activation")
            print(f"✅ Added roles to {member.name} ({member.id})")
            return True
        else:
            print("⚠️ One or more roles not found")
            return False
            
    except Exception as e:
        print(f"❌ Error adding roles: {e}")
        return False

# ========== WEBHOOK FUNCTIONS ==========
async def send_login_webhook(bot_name: str, status: str, user_info: Dict, action_user: discord.User, action: str = "Setup"):
    """Kirim webhook login dengan username mention"""
    if not WEBHOOK_URLS.get('LOGIN_WEBHOOK_URL'):
        print("⚠️ Login webhook URL not set")
        return
    
    current_time = datetime.now().strftime('%d %B %Y %H:%M:%S %p')
    
    # Tentukan emoji berdasarkan status
    status_emoji = EMOJIS.get('ONLINE_EMOJI', '🟢') if status.lower() == "online" else EMOJIS.get('OFFLINE_EMOJI', '🔴')
    
    # Format username dengan mention
    user_id = user_info.get('id', '')
    username = user_info.get('global_name', user_info.get('username', 'Unknown'))
    user_mention = f"<@{user_id}>"
    
    embed_data = {
        "embeds": [{
            "title": f"{EMOJIS.get('TITLE_EMOJI', '🤖')} **𝗔𝘂𝘁𝗼 𝗣𝗼𝘀𝘁 𝗟𝗼𝗴𝗶𝗻** {EMOJIS.get('TITLE_EMOJI', '🤖')}",
            "color": 0x00FF00 if status.lower() == "online" else 0xFF0000,
            "fields": [
                {
                    "name": f"{EMOJIS.get('INFO_EMOJI', '📋')} **𝗗𝗲𝘁𝗮𝗶𝗹𝘀 𝗜𝗻𝗳𝗼**",
                    "value": "",
                    "inline": True
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
                    "name": f"{EMOJIS.get('USER_EMOJI', '👤')} **𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {user_mention}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('TIME_EMOJI', '⏰')} **𝗗𝗮𝘁𝗲 𝗧𝗶𝗺𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {current_time}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "𝗔𝘂𝘁𝗼 𝗣𝗼𝘀𝘁 𝗕𝘆 Vechnost 𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆"
            }
        }],
        "username": "Vechnost - Autopost"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URLS['LOGIN_WEBHOOK_URL'],
                json=embed_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200 or response.status == 204:
                    print(f"✅ Login webhook sent: {bot_name}")
                else:
                    print(f"❌ Failed to send login webhook: {response.status}")
    except Exception as e:
        print(f"❌ Error sending login webhook: {e}")

async def send_log_webhook(bot_name: str, channel_id: str, status: str, user_info: Dict, message: str = ""):
    """Kirim webhook log dengan username mention"""
    if not WEBHOOK_URLS.get('LOG_WEBHOOK_URL'):
        print("⚠️ Log webhook URL not set")
        return
    
    current_time = datetime.now().strftime('%d %B %Y %H:%M:%S %p')
    
    if status.lower() == "success":
        status_emoji = EMOJIS.get('SUCCESS_EMOJI', '✅')
        embed_color = 0x00FF00
    else:
        status_emoji = EMOJIS.get('FAILED_EMOJI', '❌')
        embed_color = 0xFF0000
    
    # Format username dengan mention
    user_id = user_info.get('id', '')
    user_mention = f"<@{user_id}>"
    
    embed_data = {
        "embeds": [{
            "title": f"{EMOJIS.get('TITLE_EMOJI', '🤖')} **𝗔𝘂𝘁𝗼 𝗣𝗼𝘀𝘁 𝗗𝗶𝘀𝗰𝗼𝗿𝗱** {EMOJIS.get('TITLE_EMOJI', '🤖')}",
            "color": embed_color,
            "fields": [
                {
                    "name": f"{EMOJIS.get('INFO_EMOJI', '📋')} **𝗗𝗲𝘁𝗮𝗶𝗹𝘀 𝗜𝗻𝗳𝗼**",
                    "value": "",
                    "inline": True
                },
                {
                    "name": f"{status_emoji} **𝗦𝘁𝗮𝘁𝘂𝘀 𝗟𝗼𝗴**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {status}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('USER_EMOJI', '👤')} **𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {user_mention}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('TIME_EMOJI', '⏰')} **𝗗𝗮𝘁𝗲 𝗧𝗶𝗺𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {current_time}",
                    "inline": True
                },
                {
                    "name": f"{EMOJIS.get('CHANNEL_EMOJI', '📺')} **𝗖𝗵𝗮𝗻𝗻𝗲𝗹 𝗧𝗮𝗿𝗴𝗲𝘁**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} <#{channel_id}>",
                    "inline": True
                },
                {
                    "name": f"{status_emoji} **𝗦𝘁𝗮𝘁𝘂𝘀 𝗠𝗲𝘀𝘀𝗮𝗴𝗲**",
                    "value": f"{EMOJIS.get('ARROW_EMOJI', '➡️')} {message}",
                    "inline": True
                }
            ],
            "footer": {
                "text": "𝗔𝘂𝘁𝗼 𝗣𝗼𝘀𝘁 𝗕𝘆 Vechnost 𝗖𝗼𝗺𝗺𝘂𝗻𝗶𝘁𝘆"
            }
        }],
        "username": "Vechnost - Autopost"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URLS['LOG_WEBHOOK_URL'],
                json=embed_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200 or response.status == 204:
                    print(f"✅ Log webhook sent: {bot_name} -> {channel_id}")
                else:
                    print(f"❌ Failed to send log webhook: {response.status}")
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
                    try:
                        data = await response.json()
                        retry_after = data.get('retry_after', 5)
                        await asyncio.sleep(retry_after)
                        return await send_message_to_channel(token, channel_id, message)
                    except:
                        await asyncio.sleep(5)
                        return await send_message_to_channel(token, channel_id, message)
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'status': response.status,
                        'error': error_text[:100]
                    }
                    
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def autopost_task(bot_id: str, config: dict):
    """Task utama untuk autoposting"""
    if not isinstance(config, dict):
        return
    
    bot_name = config.get('name', 'Unknown')
    guild_id = config.get('guild_id', '')
    user_id = config.get('setup_by', 0)
    
    # Cek premium setiap 1 jam
    last_premium_check = datetime.now()
    
    while config.get('is_running', False):
        try:
            # Cek premium setiap jam
            current_time = datetime.now()
            if (current_time - last_premium_check).total_seconds() >= 3600:
                is_premium, days_left, _, _ = check_user_premium(user_id)
                if not is_premium and user_id not in ADMIN_IDS:
                    print(f"⏰ Premium expired for user {user_id}, stopping bot")
                    config['is_running'] = False
                    
                    user_bots = get_user_bots(guild_id, user_id)
                    for bot in user_bots:
                        if isinstance(bot, dict) and bot.get('name') == bot_name:
                            bot['is_running'] = False
                            save_user_bots(guild_id, user_id, user_bots)
                            break
                    
                    if bot_id in active_tasks:
                        del active_tasks[bot_id]
                    
                    break
                last_premium_check = current_time
            
            token = config.get('token', '')
            channels = config.get('channels', [])
            message = config.get('message', '')
            
            if not token or not channels or not message:
                break
            
            for channel_id in channels:
                if not config.get('is_running', False):
                    break
                
                result = await send_message_to_channel(token, channel_id, message)
                
                if result.get('success'):
                    # Update total_sent
                    user_bots = get_user_bots(guild_id, user_id)
                    for bot in user_bots:
                        if isinstance(bot, dict) and bot.get('name') == bot_name:
                            bot['total_sent'] = bot.get('total_sent', 0) + 1
                            bot['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            save_user_bots(guild_id, user_id, user_bots)
                            break
                    
                    # Kirim webhook log
                    await send_log_webhook(
                        bot_name=bot_name,
                        channel_id=channel_id,
                        status="Success",
                        user_info=config.get('user_info', {}),
                        message=f"Message Successfully Sent: <#{channel_id}>."
                    )
                else:
                    # Kirim webhook error
                    await send_log_webhook(
                        bot_name=bot_name,
                        channel_id=channel_id,
                        status="Failed",
                        user_info=config.get('user_info', {}),
                        message=f"Failed to send message: {result.get('error', 'Unknown error')}"
                    )
                
                await asyncio.sleep(10)
            
            delay_minutes = config.get('delay', 30)
            await asyncio.sleep(delay_minutes * 60)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ Error in autopost task: {e}")
            await asyncio.sleep(60)

# ========== MODAL PREMIUM CODE ==========
class PremiumCodeModal(Modal, title='🔑 VERIFIKASI PREMIUM'):
    def __init__(self):
        super().__init__(timeout=300)
    
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
        
        # Tambahkan role ke user
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

# ========== MODAL SETUP BOT ==========
class SetupModal(Modal, title='⚙️ SETUP AUTOPOST BOT'):
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
                    description="Anda harus memiliki kode premium terlebih dahulu!\n\nKlik tombol **ACCESS** untuk memasukkan kode premium.",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        # CEK LIMIT BOT
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        bot_limit = 5  # Premium user limit 5 bot
        
        if interaction.user.id not in ADMIN_IDS and len(user_bots) >= bot_limit:
            embed = discord.Embed(
                title="❌ **LIMIT BOT TERCAPAI**",
                description=f"Anda sudah memiliki {len(user_bots)}/{bot_limit} bot.\n\nStop bot lain atau hubungi admin untuk upgrade.",
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
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
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
        preview_embed.add_field(name="👤 **User Token**", value=f"`{token[:15]}...`", inline=True)
        
        # Kirim webhook login
        await send_login_webhook(
            bot_name=bot_name,
            status="Online",
            user_info=user_info,
            action_user=interaction.user,
            action="Edit" if self.edit_bot_name else "Setup"
        )
        
        await interaction.followup.send(embed=preview_embed, ephemeral=True)

# ========== VIEW UNTUK SETTINGS ==========
class SettingsView(View):
    def __init__(self, user_bots: list):
        super().__init__(timeout=180)  # Timeout lebih lama untuk settings
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
        
        # Informasi Bot
        bot_status = "🟢 ONLINE" if selected_bot.get('is_running', False) else "🔴 OFFLINE"
        embed.add_field(
            name=f"{EMOJIS.get('BOT_EMOJI', '🤖')} ၊| 𝖡𝗈𝗍",
            value=f"{EMOJIS.get('ARROW_EMOJI', '➡️')} **{selected_bot.get('name', 'Unknown')}** - {bot_status}",
            inline=False
        )
        
        # Channel List (maksimal 20 channel)
        channels_text = ""
        channels = selected_bot.get('channels', [])
        for i, channel_id in enumerate(channels[:18]):  # Maks 18 untuk formatting
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
        edit_button = Button(label='Edit', style=discord.ButtonStyle.primary, emoji='✏️')
        delete_button = Button(label='Hapus', style=discord.ButtonStyle.danger, emoji='🗑️')
        
        async def edit_callback(interaction: discord.Interaction):
            # Buat modal edit dengan data sebelumnya
            edit_modal = SetupModal(edit_bot_name=selected_bot.get('name'))
            
            # Isi field dengan data lama
            edit_modal.token.default = selected_bot.get('token', '')
            edit_modal.bot_name.default = selected_bot.get('name', '')
            edit_modal.channels.default = ', '.join(selected_bot.get('channels', []))
            edit_modal.message.default = selected_bot.get('message', '')
            edit_modal.delay.default = str(selected_bot.get('delay', 30))
            
            await interaction.response.send_modal(edit_modal)
        
        async def delete_callback(interaction: discord.Interaction):
            # Konfirmasi hapus
            confirm_embed = discord.Embed(
                title="⚠️ **KONFIRMASI HAPUS**",
                description=f"Apakah Anda yakin ingin menghapus bot **{selected_bot.get('name', 'Unknown')}**?\n\nTindakan ini tidak dapat dibatalkan!",
                color=0xFFA500
            )
            
            confirm_view = View(timeout=30)
            
            yes_button = Button(label='Ya, Hapus', style=discord.ButtonStyle.danger, emoji='✅')
            no_button = Button(label='Batal', style=discord.ButtonStyle.secondary, emoji='❌')
            
            async def yes_callback(interaction: discord.Interaction):
                guild_id = str(interaction.guild_id)
                user_bots = get_user_bots(guild_id, interaction.user.id)
                
                # Hapus bot dari list
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
        
        action_view = View(timeout=180)
        action_view.add_item(edit_button)
        action_view.add_item(delete_button)
        
        await interaction.response.edit_message(embed=embed, view=action_view)

# ========== MAIN VIEW DENGAN BUTTON EMOJI ==========
class AutopostView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='<:access:1456791739175145665>', row=0)
    async def premium_button(self, interaction: discord.Interaction, button: Button):
        # Semua user bisa input kode premium
        modal = PremiumCodeModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='<:SETUP:1456791578143096914>', row=0)
    async def setup_button(self, interaction: discord.Interaction, button: Button):
        # Cek premium/admin
        if interaction.user.id not in ADMIN_IDS:
            is_premium, _, _, _ = check_user_premium(interaction.user.id)
            if not is_premium:
                embed = discord.Embed(
                    title="❌ **AKSES DITOLAK**",
                    description="Anda harus memiliki kode premium untuk menggunakan fitur ini.\n\nKlik tombol **ACCESS** untuk memasukkan kode premium.",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        modal = SetupModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='<:SETTING:1456791618488373453>', row=0)
    async def settings_button(self, interaction: discord.Interaction, button: Button):
        # Cek premium/admin
        if interaction.user.id not in ADMIN_IDS:
            is_premium, _, _, _ = check_user_premium(interaction.user.id)
            if not is_premium:
                embed = discord.Embed(
                    title="❌ **AKSES DITOLAK**",
                    description="Anda harus memiliki kode premium untuk menggunakan fitur ini.\n\nKlik tombol **ACCESS** untuk memasukkan kode premium.",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        
        if not user_bots:
            embed = discord.Embed(
                title="❌ **BELUM ADA BOT**",
                description="Anda belum membuat bot. Klik tombol **SETUP** untuk membuat bot pertama.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Tampilkan view dengan dropdown
        view = SettingsView(user_bots)
        
        # Buat embed awal
        embed = discord.Embed(
            title=f"{EMOJIS.get('SETTING_EMOJI', '⚙️')} **𝚂𝚎𝚝𝚝𝚒𝚗𝚐**",
            description="Pilih bot dari dropdown di bawah untuk melihat dan mengatur detailnya.",
            color=0x5865F2
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='<:PLAY:1456791513010012342>', row=0)
    async def start_button(self, interaction: discord.Interaction, button: Button):
        # Cek premium/admin
        if interaction.user.id not in ADMIN_IDS:
            is_premium, _, _, _ = check_user_premium(interaction.user.id)
            if not is_premium:
                embed = discord.Embed(
                    title="❌ **AKSES DITOLAK**",
                    description="Anda harus memiliki kode premium untuk menggunakan fitur ini.\n\nKlik tombol **ACCESS** untuk memasukkan kode premium.",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        
        if not user_bots:
            embed = discord.Embed(
                title="❌ **BELUM ADA BOT**",
                description="Anda belum membuat bot. Klik tombol **SETUP** untuk membuat bot pertama.",
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
            
            # Kirim webhook login untuk start
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
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='<:stop:1456791308743086090>', row=0)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        # Cek premium/admin
        if interaction.user.id not in ADMIN_IDS:
            is_premium, _, _, _ = check_user_premium(interaction.user.id)
            if not is_premium:
                embed = discord.Embed(
                    title="❌ **AKSES DITOLAK**",
                    description="Anda harus memiliki kode premium untuk menggunakan fitur ini.\n\nKlik tombol **ACCESS** untuk memasukkan kode premium.",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        
        if not user_bots:
            embed = discord.Embed(
                title="❌ **BELUM ADA BOT**",
                description="Anda belum membuat bot. Klik tombol **SETUP** untuk membuat bot pertama.",
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
            
            # Kirim webhook login untuk stop
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
    
    @discord.ui.button(label='', style=discord.ButtonStyle.gray, emoji='<:STATUS:1456791217567174887>', row=1)
    async def status_button(self, interaction: discord.Interaction, button: Button):
        # Cek premium/admin
        if interaction.user.id not in ADMIN_IDS:
            is_premium, _, _, _ = check_user_premium(interaction.user.id)
            if not is_premium:
                embed = discord.Embed(
                    title="❌ **AKSES DITOLAK**",
                    description="Anda harus memiliki kode premium untuk menggunakan fitur ini.\n\nKlik tombol **ACCESS** untuk memasukkan kode premium.",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        guild_id = str(interaction.guild_id)
        user_bots = get_user_bots(guild_id, interaction.user.id)
        
        if not user_bots:
            embed = discord.Embed(
                title="❌ **BELUM ADA BOT**",
                description="Anda belum membuat bot. Klik tombol **SETUP** untuk membuat bot pertama.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Cek status premium user
        is_premium, days_left, plan, _ = check_user_premium(interaction.user.id)
        
        # Hitung total channel (unik)
        all_channels = set()
        total_success = 0
        total_fail = 0  # Ini perlu disimpan di data bot jika ada
        
        # Buat list bot dengan status
        bot_list_text = ""
        for i, bot in enumerate(user_bots):
            if not isinstance(bot, dict):
                continue
                
            bot_name = bot.get('name', f'Bot_{i+1}')
            status_emoji = EMOJIS.get('ONLINE_EMOJI', '🟢') if bot.get('is_running', False) else EMOJIS.get('OFFLINE_EMOJI', '🔴')
            
            # Tambahkan channel ke set
            for channel in bot.get('channels', []):
                all_channels.add(channel)
            
            # Akumulasi total success
            total_success += bot.get('total_sent', 0)
            
            # Format bot list
            prefix = "├" if i < len(user_bots) - 1 else "╰┈"
            bot_list_text += f"{prefix}{EMOJIS.get('ARROW_EMOJI', '➡️')} {bot_name}\n"
        
        # Hitung waktu premium dengan lebih akurat (hari, jam, menit, detik)
        if is_premium:
            # Import untuk perhitungan waktu
            from datetime import datetime
            
            # Ambil expires_at dari check_user_premium yang sudah dimodifikasi
            # Untuk sekarang, kita hitung dari days_left (untuk sementara)
            # NOTE: Ini perlu disesuaikan jika check_user_premium mengembalikan expires_at
            total_seconds = days_left * 24 * 60 * 60
            days = days_left
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds // 60) % 60
            seconds = total_seconds % 60
            
            premium_info = f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} {plan}\n"
            premium_info += f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} {days} hari\n"
            premium_info += f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} {hours} jam\n"
            premium_info += f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} {minutes} menit\n"
            premium_info += f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {seconds} detik"
        else:
            premium_info = f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} Belum Premium"
        
        # Buat embed status
        embed = discord.Embed(
            title=f"**𝚂𝚃𝙰𝚃𝚄𝚂 𝙱𝙾𝚃**",
            color=0x5865F2
        )
        
        # Status bot
        if any(b.get('is_running', False) for b in user_bots if isinstance(b, dict)):
            status_emoji = EMOJIS.get('ONLINE_EMOJI', '🟢')
        else:
            status_emoji = EMOJIS.get('OFFLINE_EMOJI', '🔴')
        
        embed.add_field(
            name=f"{status_emoji} ၊| 𝖡𝗈𝗍",
            value=bot_list_text if bot_list_text else f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} Tidak ada bot",
            inline=False
        )
        
        # Channel
        embed.add_field(
            name=f"{EMOJIS.get('CHANNEL_EMOJI', '📺')} ၊| 𝖢𝗁𝖺𝗇𝗇𝖾𝗅",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {len(all_channels)} channel",
            inline=True
        )
        
        # Delay (ambil dari bot pertama)
        if user_bots and isinstance(user_bots[0], dict):
            delay = user_bots[0].get('delay', 30)
            embed.add_field(
                name=f"{EMOJIS.get('TIME_EMOJI', '⏰')} ၊| 𝖣𝖾𝗅𝖺𝗒",
                value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {delay} menit",
                inline=True
            )
        
        # Success
        embed.add_field(
            name=f"{EMOJIS.get('SUCCESS_EMOJI', '✅')} ၊| 𝖲𝗎𝖼𝖼𝖾𝗌",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {total_success} pesan",
            inline=True
        )
        
        # Fail (belum diimplementasikan)
        embed.add_field(
            name=f"{EMOJIS.get('FAILED_EMOJI', '❌')} ၊| 𝖥𝖺𝗂𝗅",
            value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} {total_fail} pesan",
            inline=True
        )
        
        # Access
        embed.add_field(
            name=f"{EMOJIS.get('ACCESS_EMOJI', '<:access:1456791739175145665>')} ၊| 𝖠𝖼𝖼𝖾𝗌𝗌",
            value=premium_info,
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== FUNGSI EMBED STATIS ==========
def create_autopost_embed() -> discord.Embed:
    embed = discord.Embed(
        title="𝚅𝙴𝙲𝙷𝙽𝙾𝚂𝚃 - 𝙰𝚄𝚃𝙾𝙿𝙾𝚂𝚃",
        description="",
        color=0x5865F2
    )
    
    # ACCESS SECTION
    embed.add_field(
        name=f"<:access:1456791739175145665> ၊| 𝖠𝖼𝖼𝖾𝗌𝗌",
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
        name=f"<:SETUP:1456791578143096914> ၊| 𝖲𝖾𝗍𝗎𝗉",
        value=(
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} TOKEN\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} NAMA BOT\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} CHANNEL ID\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} MESSAGE\n"
            f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} DELAY"
        ),
        inline=False
    )
    
    # SETTING SECTION
    embed.add_field(
        name=f"<:SETTING:1456791618488373453> ၊| 𝖲𝖾𝗍𝗍𝗂𝗇𝗀",
        value=(
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} NAMA BOT\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} CHANNEL ID\n"
            f"├{EMOJIS.get('ARROW_EMOJI', '➡️')} MESSAGE\n"
            f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} DELAY"
        ),
        inline=False
    )
    
    # PLAY SECTION
    embed.add_field(
        name=f"<:PLAY:1456791513010012342> ၊| 𝖯𝗅𝖺𝗒",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} START BOT",
        inline=True
    )
    
    # STOP SECTION
    embed.add_field(
        name=f"<:stop:1456791308743086090> ၊| 𝖲𝗍𝗈𝗉",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} STOP BOT",
        inline=True
    )
    
    # STATUS SECTION
    embed.add_field(
        name=f"<:STATUS:1456791217567174887> ၊| 𝖲𝗍𝖺𝗍𝗎𝗌",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} CHECK BOT",
        inline=True
    )
    
    # BUY ACCESS SECTION
    embed.add_field(
        name=f"<a:vechnostproduct:1456517219528736810> ၊| 𝖡𝗎𝗒 𝖠𝖼𝖼𝖾𝗌𝗌",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} <#1452670503633551545>",
        inline=False
    )
    
     # CHECK WEBHOOK SECTION
    embed.add_field(
        name=f":webhook: ၊| 𝖢𝗁𝖾𝖼𝗄 𝖶𝖾𝖻𝗁𝗈𝗈𝗄",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} <#1452672717475151995>",
        inline=False
    )

      # PREVIEW  SECTION
    embed.add_field(
        name=f":preview: ၊| 𝖯𝗋𝖾𝗏𝗂𝖾𝗐",
        value=f"╰┈{EMOJIS.get('ARROW_EMOJI', '➡️')} <#1456860477928898754>",
        inline=False
    )
    # Banner image
    embed.set_image(url="https://cdn.discordapp.com/attachments/1452678223094747240/1452767072198070382/banner.gif")
    
    # Footer text tanpa timestamp
    embed.set_footer(text="AutoPost By Vechnost Community")
    
    return embed

# ========== SLASH COMMAND ==========
@tree.command(name="autopost", description="Tampilkan panel kontrol autoposting (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def autopost_command(interaction: discord.Interaction):
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
        "1d": 1, "7d": 7, "30d": 30, "lifetime": 9999
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
    
    # Buat embed untuk admin
    admin_embed = discord.Embed(
        title="🎫 **PREMIUM CODE CREATED**",
        color=0x00FF00
    )
    
    admin_embed.add_field(name="🔑 **Code**", value=f"`{code}`", inline=False)
    admin_embed.add_field(name="⏰ **Duration**", value=f"{days} hari", inline=True)
    admin_embed.add_field(name="📅 **Expires**", value=code_data["expires_at"], inline=True)
    admin_embed.add_field(name="👤 **Created By**", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=admin_embed, ephemeral=True)
    
    # Kirim embed ke user jika disebutkan
    if user:
        try:
            user_embed = discord.Embed(
                title="𝚅𝚎𝚌𝚑𝚗𝚘𝚜𝚝 - 𝙰𝚌𝚌𝚎𝚜",
                color=0x5865F2
            )
            
            user_embed.add_field(
                name=f"🔑 ၊| 𝖢𝗈𝖽𝖾",
                value=f"```{code}```",
                inline=False
            )
            
            user_embed.add_field(
                name=f"⏳၊| Durasi",
                value=f"{days} hari",
                inline=True
            )
            
            user_embed.add_field(
                name=f"📅 ၊| Expired at",
                value=code_data["expires_at"],
                inline=True
            )
            
            user_embed.add_field(
                name=f"🚀 **Cara Pakai**",
                value="Pergi ke <#1452672717475151995>\nmasukan code yang di berikan",
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
                description=f"Tidak bisa mengirim DM ke {user.mention}\nBerikan kode ini manual: `{code}`",
                color=0xFF0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

# ========== EVENT HANDLERS ==========
@bot.event
async def on_ready():
    print("=" * 50)
    print(f"🤖 Controller Bot: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print("=" * 50)
    
    try:
        synced = await tree.sync()
        print(f"✅ Commands synced: {len(synced)} command")
        
        for cmd in synced:
            print(f"  - /{cmd.name}")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")
    
    load_data()
    
    task_count = 0
    for guild_id, users_data in AUTOPOST_DATA.items():
        for user_id_str, bots in users_data.items():
            if not isinstance(bots, list):
                continue
                
            for bot_config in bots:
                if not isinstance(bot_config, dict):
                    continue
                    
                if bot_config.get('is_running', False):
                    bot_name = bot_config.get('name', 'Unknown')
                    bot_id = f"{guild_id}_{user_id_str}_{bot_name}"
                    
                    try:
                        user_id = int(user_id_str)
                        if user_id != 0 and user_id not in ADMIN_IDS:
                            is_premium, _, _, _ = check_user_premium(user_id)
                            if not is_premium:
                                print(f"⚠️ User {user_id} tidak premium, skip bot {bot_name}")
                                bot_config['is_running'] = False
                                continue
                    except:
                        pass
                    
                    required_fields = ['token', 'channels', 'message', 'delay']
                    missing_fields = [field for field in required_fields if field not in bot_config]
                    
                    if missing_fields:
                        bot_config['is_running'] = False
                        continue
                    
                    bot_config['guild_id'] = guild_id
                    task = asyncio.create_task(autopost_task(bot_id, bot_config))
                    active_tasks[bot_id] = task
                    task_count += 1
    
    print(f"🔄 {task_count} task(s) restarted")
    print("✅ Bot controller siap digunakan!")
    print("=" * 50)
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Panel Autopost"
        ),
        status=discord.Status.online
    )

# ========== RUN BOT ==========
if __name__ == "__main__":
    # Start web server untuk keep alive
    try:
        keep_alive()
        print("✅ Web server started on port 8080")
    except Exception as e:
        print(f"⚠️ Failed to start web server: {e}")
    
    load_data()
    
    if not BOT_TOKEN:
        print("❌ ERROR: Token bot controller tidak ditemukan!")
        print("Pastikan sudah set Secrets di Replit:")
        print("BOT_TOKEN=your_bot_token_here")
        print("ADMIN_IDS=123456789012345678")
        exit(1)
    
    print("🚀 Starting bot controller...")
    
    try:
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Token bot controller salah atau expired!")
    except Exception as e:
        print(f"❌ ERROR: {e}")