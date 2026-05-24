"""
LUXalpha Trading Bot - Bale Messenger
=====================================
نسخه پیش‌نمایش - قبل از استفاده توکن را تغییر دهید
"""

import asyncio
import logging
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx

# ===================== تنظیمات =====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_NEW_TOKEN_HERE")

BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

ADMIN_IDS = [123456789]  # ← آیدی عددی ادمین‌ها

WALLET_TRC20 = "TXXXxxxxYourTRC20AddressHere"   # ← آدرس ولت TRC20
WALLET_BEP20 = "0xXXXxxxxYourBEP20AddressHere"  # ← آدرس ولت BEP20

# قیمت‌های اشتراک (دلار)
PLANS = {
    "basic":  {"name": "ALPHA-BASIC",  "price": 49,  "win": "60%", "desc": "Classic accuracy. Consistent results."},
    "pro":    {"name": "ALPHA-PRO",    "price": 89,  "win": "68%", "desc": "Advanced signals. Higher precision."},
    "elite":  {"name": "ALPHA-ELITE",  "price": 149, "win": "75%", "desc": "Elite setups. Superior performance."},
    "vip":    {"name": "VIP BUNDLE",   "price": 249, "win": "ALL 4", "desc": "All 4 Indicators. Maximum Advantage."},
}

# ===================== دیتابیس =====================
def init_db():
    conn = sqlite3.connect("luxalpha.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id     INTEGER PRIMARY KEY,
            full_name   TEXT,
            market      TEXT,
            tv_username TEXT,
            status      TEXT DEFAULT 'new',
            plan        TEXT,
            sub_expire  TEXT,
            registered  TEXT,
            last_follow INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id     INTEGER,
            plan        TEXT,
            network     TEXT,
            amount      REAL,
            tx_hash     TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect("luxalpha.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        keys = ["chat_id","full_name","market","tv_username","status","plan","sub_expire","registered","last_follow"]
        return dict(zip(keys, row))
    return None

def save_user(data: dict):
    conn = sqlite3.connect("luxalpha.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (chat_id, full_name, market, tv_username, status, registered)
        VALUES (:chat_id, :full_name, :market, :tv_username, 'registered', :registered)
        ON CONFLICT(chat_id) DO UPDATE SET
            full_name=excluded.full_name,
            market=excluded.market,
            tv_username=excluded.tv_username
    """, data)
    conn.commit()
    conn.close()

def update_user_status(chat_id, status, plan=None, expire=None):
    conn = sqlite3.connect("luxalpha.db")
    c = conn.cursor()
    if plan and expire:
        c.execute("UPDATE users SET status=?, plan=?, sub_expire=? WHERE chat_id=?",
                  (status, plan, expire, chat_id))
    else:
        c.execute("UPDATE users SET status=? WHERE chat_id=?", (status, chat_id))
    conn.commit()
    conn.close()

def add_payment(chat_id, plan, network, amount, tx_hash):
    conn = sqlite3.connect("luxalpha.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO payments (chat_id, plan, network, amount, tx_hash, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (chat_id, plan, network, amount, tx_hash, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("luxalpha.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    conn.close()
    keys = ["chat_id","full_name","market","tv_username","status","plan","sub_expire","registered","last_follow"]
    return [dict(zip(keys, r)) for r in rows]

# ===================== API بله =====================
async def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
        except Exception as e:
            logging.error(f"send_message error: {e}")

async def send_document(chat_id, file_path, caption=""):
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                await client.post(
                    f"{BASE_URL}/sendDocument",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"document": f},
                    timeout=30
                )
        except Exception as e:
            logging.error(f"send_document error: {e}")

async def send_video(chat_id, file_path, caption=""):
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                await client.post(
                    f"{BASE_URL}/sendVideo",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"video": f},
                    timeout=60
                )
        except Exception as e:
            logging.error(f"send_video error: {e}")

async def get_updates(offset=0):
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{BASE_URL}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35
            )
            return r.json().get("result", [])
        except Exception as e:
            logging.error(f"get_updates error: {e}")
            return []

# ===================== متون پیام‌ها =====================
# برای تغییر متون فقط همین بخش رو ویرایش کنید

MSG_WELCOME = """
🌟 *به LUXalpha خوش آمدید!*

سیستم هوشمند اندیکاتورهای معاملاتی با دقت بالا.

برای شروع، لطفاً *نام و نام‌خانوادگی* خود را وارد کنید:
"""

MSG_ASK_MARKET = """
✅ ممنون، *{name}* عزیز!

بازار مورد فعالیت شما را انتخاب کنید:
"""

MSG_ASK_TV = """
✅ بازار انتخاب شد: *{market}*

لطفاً *یوزرنیم TradingView* خود را وارد کنید:
(مثال: john_trader)
"""

MSG_REGISTERED = """
🎉 *ثبت‌نام شما تکمیل شد!*

━━━━━━━━━━━━━━━
👤 نام: {name}
📊 بازار: {market}
📈 TradingView: {tv}
━━━━━━━━━━━━━━━

در حال ارسال محتوای آموزشی...
"""

MSG_PLANS = """
💎 *پلن‌های اشتراک LUXalpha*
🔥 تخفیف ۵۰٪ لانچ اکتیوه!

━━━━━━━━━━━━━━━
1️⃣ *ALPHA-BASIC* — $49/ماه
   📊 Win Rate: 60% | دقت کلاسیک

2️⃣ *ALPHA-PRO* — $89/ماه
   📊 Win Rate: 68% | سیگنال‌های پیشرفته

3️⃣ *ALPHA-ELITE* — $149/ماه
   📊 Win Rate: 75% | ستاپ‌های الیت

4️⃣ *VIP BUNDLE* — $249/ماه
   💎 تمام ۴ اندیکاتور | حداکثر مزیت
━━━━━━━━━━━━━━━

یک پلن انتخاب کنید:
"""

MSG_PAYMENT = """
💳 *پرداخت پلن {plan}*
💰 مبلغ: *${amount} USDT*

شبکه پرداخت را انتخاب کنید:
🔹 TRC20 (Tron) — کارمزد کمتر
🔸 BEP20 (BSC) — سریع‌تر
"""

MSG_WALLET = """
📤 *آدرس ولت {network}:*

`{wallet}`

✅ مبلغ: *${amount} USDT*

پس از واریز، *Hash تراکنش* را ارسال کنید.
⚠️ حتماً روی شبکه {network} ارسال کنید.
"""

MSG_PAYMENT_RECEIVED = """
⏳ *درخواست پرداخت دریافت شد*

Hash: `{tx_hash}`

در حال بررسی (معمولاً ۱-۳ ساعت)
پس از تأیید، اشتراک فعال می‌شود. ✅
"""

MSG_FOLLOW_DAY1 = """
👋 سلام {name} عزیز!

می‌دونیم که مشغول بودی 😊
اگه سوالی داری درباره پلن‌های LUXalpha، اینجام!

برای دیدن پلن‌ها /plans بزن.
"""

MSG_FOLLOW_DAY3 = """
🔥 {name} عزیز، فرصت رو از دست نده!

تخفیف ۵۰٪ لانچ محدوده!
پلن ALPHA-BASIC فقط $49/ماه

برای خرید /plans بزن 💎
"""

MSG_SUB_EXPIRY = """
⚠️ {name} عزیز،

اشتراک شما *{days} روز دیگر* منقضی می‌شود.

برای تمدید /plans بزن تا سیگنال‌ها قطع نشن! 🔄
"""

# ===================== State مدیریت =====================
user_states = {}  # {chat_id: {"step": "...", "data": {}}}

def get_state(chat_id):
    return user_states.get(chat_id, {"step": "start", "data": {}})

def set_state(chat_id, step, data=None):
    if data is None:
        data = user_states.get(chat_id, {}).get("data", {})
    user_states[chat_id] = {"step": step, "data": data}

# ===================== کیبورد =====================
def keyboard_market():
    return {
        "keyboard": [
            [{"text": "📊 Forex"}, {"text": "₿ Crypto"}],
            [{"text": "📈 Indices"}, {"text": "🔢 همه بازارها"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

def keyboard_plans():
    return {
        "inline_keyboard": [
            [{"text": "1️⃣ ALPHA-BASIC — $49", "callback_data": "plan_basic"}],
            [{"text": "2️⃣ ALPHA-PRO — $89", "callback_data": "plan_pro"}],
            [{"text": "3️⃣ ALPHA-ELITE — $149", "callback_data": "plan_elite"}],
            [{"text": "4️⃣ VIP BUNDLE — $249", "callback_data": "plan_vip"}],
        ]
    }

def keyboard_network():
    return {
        "inline_keyboard": [
            [{"text": "🔹 TRC20 (Tron)", "callback_data": "net_trc20"}],
            [{"text": "🔸 BEP20 (BSC)", "callback_data": "net_bep20"}],
        ]
    }

def keyboard_admin():
    return {
        "inline_keyboard": [
            [{"text": "👥 لیست کاربران", "callback_data": "admin_users"}],
            [{"text": "📢 ارسال پیام گروهی", "callback_data": "admin_broadcast"}],
            [{"text": "💳 پرداخت‌های انتظار", "callback_data": "admin_payments"}],
        ]
    }

# ===================== هندلرها =====================
async def handle_start(chat_id, user_db):
    if user_db and user_db["status"] not in ["new", "registered"]:
        await send_message(chat_id, f"👋 خوش برگشتی!\n\nبرای مشاهده پلن‌ها /plans بزن.")
        return
    set_state(chat_id, "ask_name", {})
    await send_message(chat_id, MSG_WELCOME)

async def handle_plans(chat_id):
    await send_message(chat_id, MSG_PLANS, reply_markup=keyboard_plans())

async def handle_text(chat_id, text, user_db):
    state = get_state(chat_id)
    step = state["step"]
    data = state["data"]

    # --- ثبت‌نام ---
    if step == "ask_name":
        data["full_name"] = text
        set_state(chat_id, "ask_market", data)
        await send_message(chat_id,
            MSG_ASK_MARKET.format(name=text),
            reply_markup=keyboard_market()
        )

    elif step == "ask_market":
        markets = ["Forex", "Crypto", "Indices", "همه بازارها", "📊 Forex", "₿ Crypto", "📈 Indices", "🔢 همه بازارها"]
        if text not in markets:
            await send_message(chat_id, "لطفاً از دکمه‌ها انتخاب کنید ⬇️")
            return
        data["market"] = text.replace("📊 ","").replace("₿ ","").replace("📈 ","").replace("🔢 ","")
        set_state(chat_id, "ask_tv", data)
        await send_message(chat_id, MSG_ASK_TV.format(market=data["market"]))

    elif step == "ask_tv":
        data["tv_username"] = text
        set_state(chat_id, "done", data)
        # ذخیره در دیتابیس
        save_user({
            "chat_id": chat_id,
            "full_name": data["full_name"],
            "market": data["market"],
            "tv_username": data["tv_username"],
            "registered": datetime.now().isoformat()
        })
        await send_message(chat_id, MSG_REGISTERED.format(
            name=data["full_name"], market=data["market"], tv=data["tv_username"]
        ))
        # ارسال ویدیو و PDF
        await asyncio.sleep(1)
        if os.path.exists("intro_video.mp4"):
            await send_video(chat_id, "intro_video.mp4", "🎬 ویدیوی آموزشی LUXalpha")
        else:
            await send_message(chat_id, "🎬 *ویدیوی آموزشی*\n\n_(فایل intro_video.mp4 را در کنار ربات قرار دهید)_")
        await asyncio.sleep(1)
        if os.path.exists("rules.pdf"):
            await send_document(chat_id, "rules.pdf", "📋 قوانین و شرایط استفاده")
        else:
            await send_message(chat_id, "📋 *قوانین استفاده*\n\n_(فایل rules.pdf را در کنار ربات قرار دهید)_")
        await asyncio.sleep(1)
        await send_message(chat_id, MSG_PLANS, reply_markup=keyboard_plans())

    # --- پرداخت: hash ---
    elif step == "await_hash":
        tx_hash = text.strip()
        plan_key = data.get("plan")
        network = data.get("network")
        plan = PLANS.get(plan_key, {})
        add_payment(chat_id, plan_key, network, plan.get("price", 0), tx_hash)
        set_state(chat_id, "done")
        await send_message(chat_id, MSG_PAYMENT_RECEIVED.format(tx_hash=tx_hash))
        # اطلاع به ادمین
        user = get_user(chat_id)
        for admin_id in ADMIN_IDS:
            await send_message(admin_id,
                f"💳 *پرداخت جدید!*\n"
                f"👤 {user['full_name'] if user else chat_id}\n"
                f"📦 پلن: {plan_key}\n"
                f"🌐 شبکه: {network}\n"
                f"💰 ${plan.get('price',0)}\n"
                f"🔗 Hash: `{tx_hash}`\n\n"
                f"برای تأیید:\n`/approve {chat_id} {plan_key}`"
            )

    # --- broadcast ادمین ---
    elif step == "admin_broadcast" and chat_id in ADMIN_IDS:
        users = get_all_users()
        count = 0
        for u in users:
            try:
                await send_message(u["chat_id"], text)
                count += 1
                await asyncio.sleep(0.1)
            except:
                pass
        set_state(chat_id, "done")
        await send_message(chat_id, f"✅ پیام به {count} کاربر ارسال شد.")

    else:
        await send_message(chat_id, "برای شروع /start یا برای پلن‌ها /plans بزن.")

async def handle_callback(chat_id, callback_data, message_id=None):
    state = get_state(chat_id)

    # انتخاب پلن
    if callback_data.startswith("plan_"):
        plan_key = callback_data.replace("plan_", "")
        plan = PLANS.get(plan_key)
        if not plan:
            return
        data = state["data"]
        data["plan"] = plan_key
        set_state(chat_id, "ask_network", data)
        await send_message(chat_id,
            MSG_PAYMENT.format(plan=plan["name"], amount=plan["price"]),
            reply_markup=keyboard_network()
        )

    # انتخاب شبکه
    elif callback_data.startswith("net_"):
        network = callback_data.replace("net_", "").upper()
        data = state["data"]
        data["network"] = network
        plan_key = data.get("plan")
        plan = PLANS.get(plan_key, {})
        wallet = WALLET_TRC20 if network == "TRC20" else WALLET_BEP20
        set_state(chat_id, "await_hash", data)
        await send_message(chat_id,
            MSG_WALLET.format(network=network, wallet=wallet, amount=plan.get("price", 0))
        )

    # ادمین
    elif callback_data == "admin_users" and chat_id in ADMIN_IDS:
        users = get_all_users()
        text = f"👥 *کاربران ({len(users)} نفر)*\n\n"
        for u in users[:20]:
            text += f"• {u['full_name']} | {u['status']} | {u.get('plan','—')}\n"
        if len(users) > 20:
            text += f"\n...و {len(users)-20} کاربر دیگر"
        await send_message(chat_id, text)

    elif callback_data == "admin_broadcast" and chat_id in ADMIN_IDS:
        set_state(chat_id, "admin_broadcast")
        await send_message(chat_id, "📢 متن پیام گروهی را بفرستید:")

    elif callback_data == "admin_payments" and chat_id in ADMIN_IDS:
        conn = sqlite3.connect("luxalpha.db")
        c = conn.cursor()
        c.execute("SELECT * FROM payments WHERE status='pending' LIMIT 10")
        rows = c.fetchall()
        conn.close()
        if not rows:
            await send_message(chat_id, "✅ پرداخت در انتظار وجود ندارد.")
            return
        text = "💳 *پرداخت‌های در انتظار:*\n\n"
        for r in rows:
            text += f"ID:{r[1]} | {r[2]} | {r[3]} | ${r[4]}\nHash: `{r[5]}`\n`/approve {r[1]} {r[2]}`\n\n"
        await send_message(chat_id, text)

async def handle_admin_command(chat_id, text):
    """دستورات ادمین"""
    if chat_id not in ADMIN_IDS:
        return

    # /approve <chat_id> <plan>
    if text.startswith("/approve "):
        parts = text.split()
        if len(parts) == 3:
            target_id = int(parts[1])
            plan_key = parts[2]
            expire = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            update_user_status(target_id, "active", plan_key, expire)
            # تأیید پرداخت
            conn = sqlite3.connect("luxalpha.db")
            c = conn.cursor()
            c.execute("UPDATE payments SET status='confirmed' WHERE chat_id=? AND plan=? AND status='pending'",
                      (target_id, plan_key))
            conn.commit()
            conn.close()
            plan = PLANS.get(plan_key, {})
            await send_message(target_id,
                f"🎉 *تبریک! اشتراک شما فعال شد!*\n\n"
                f"📦 پلن: {plan.get('name','')}\n"
                f"📅 انقضا: {expire}\n\n"
                f"برای دریافت اندیکاتورها به ادمین پیام دهید."
            )
            await send_message(chat_id, f"✅ اشتراک کاربر {target_id} فعال شد.")

    # /panel
    elif text == "/panel":
        await send_message(chat_id, "🛠 *پنل ادمین LUXalpha*", reply_markup=keyboard_admin())

    # /stats
    elif text == "/stats":
        conn = sqlite3.connect("luxalpha.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE status='active'")
        active = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")
        pending = c.fetchone()[0]
        conn.close()
        await send_message(chat_id,
            f"📊 *آمار ربات*\n\n"
            f"👥 کل کاربران: {total}\n"
            f"✅ اشتراک فعال: {active}\n"
            f"⏳ پرداخت انتظار: {pending}"
        )

# ===================== یادآوری خودکار =====================
async def reminder_loop():
    """هر ۱ ساعت یکبار اجرا می‌شه"""
    while True:
        await asyncio.sleep(3600)
        try:
            users = get_all_users()
            now = datetime.now()
            for u in users:
                chat_id = u["chat_id"]
                reg_time = datetime.fromisoformat(u["registered"]) if u.get("registered") else None
                if not reg_time:
                    continue

                days_since = (now - reg_time).days

                # پیگیری روز اول (کاربر خرید نکرده)
                if u["status"] == "registered" and days_since == 1 and u["last_follow"] < 1:
                    await send_message(chat_id, MSG_FOLLOW_DAY1.format(name=u["full_name"] or "دوست"))
                    conn = sqlite3.connect("luxalpha.db")
                    conn.execute("UPDATE users SET last_follow=1 WHERE chat_id=?", (chat_id,))
                    conn.commit(); conn.close()

                # پیگیری روز سوم
                elif u["status"] == "registered" and days_since >= 3 and u["last_follow"] < 2:
                    await send_message(chat_id, MSG_FOLLOW_DAY3.format(name=u["full_name"] or "دوست"))
                    conn = sqlite3.connect("luxalpha.db")
                    conn.execute("UPDATE users SET last_follow=2 WHERE chat_id=?", (chat_id,))
                    conn.commit(); conn.close()

                # هشدار انقضای اشتراک (۳ روز مانده)
                elif u["status"] == "active" and u.get("sub_expire"):
                    expire = datetime.strptime(u["sub_expire"], "%Y-%m-%d")
                    days_left = (expire - now).days
                    if days_left in [3, 1]:
                        await send_message(chat_id,
                            MSG_SUB_EXPIRY.format(name=u["full_name"] or "دوست", days=days_left))

        except Exception as e:
            logging.error(f"reminder_loop error: {e}")

# ===================== لوپ اصلی =====================
async def main():
    init_db()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("🚀 LUXalpha Bot Started!")

    asyncio.create_task(reminder_loop())

    offset = 0
    while True:
        updates = await get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            try:
                # پیام متنی
                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "")
                    user_db = get_user(chat_id)

                    if text == "/start":
                        await handle_start(chat_id, user_db)
                    elif text == "/plans":
                        await handle_plans(chat_id)
                    elif text in ["/approve", "/panel", "/stats"] or text.startswith("/approve "):
                        await handle_admin_command(chat_id, text)
                    else:
                        await handle_text(chat_id, text, user_db)

                # callback دکمه‌ها
                elif "callback_query" in update:
                    cq = update["callback_query"]
                    chat_id = cq["message"]["chat"]["id"]
                    await handle_callback(chat_id, cq["data"])

            except Exception as e:
                logging.error(f"Update error: {e}")

        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
