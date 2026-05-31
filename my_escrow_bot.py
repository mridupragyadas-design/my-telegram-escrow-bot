from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os
import asyncio
from datetime import datetime, timezone, timedelta
from flask import Flask
from threading import Thread

# ==================== FLASK WEB SERVER FOR RENDER ====================
flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

Thread(target=run_flask, daemon=True).start()
# ====================================================================

# === CONFIG ===
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8634076261:AAGRJOTyA_LCzwCNq37OjaghGwWFHo6DfZM')

OWNER_ID = 2096985880
ADMINS = [2096985880, 8737155576]   # Hardcoded admin IDs

STATS_FILE = "admin_stats.json"
USER_STATS_FILE = "user_escrow_stats.json"
NIGHT_SETTINGS_FILE = "night_settings.json"

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# Night mode state (in-memory)
night_mode = {}
auto_on_tasks = {}
auto_off_tasks = {}


# =========================
# LOAD / SAVE STATS
# =========================
def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def load_user_stats():
    if os.path.exists(USER_STATS_FILE):
        try:
            with open(USER_STATS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_stats(stats):
    with open(USER_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


admin_stats = load_stats()


# =========================
# NIGHT SETTINGS PERSISTENCE
# =========================
def load_night_settings():
    if os.path.exists(NIGHT_SETTINGS_FILE):
        try:
            with open(NIGHT_SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_night_settings(settings):
    with open(NIGHT_SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# =========================
# ADMIN CHECK (hardcoded)
# =========================
def is_admin(user_id):
    return user_id in ADMINS or user_id == OWNER_ID


# =========================
# GROUP ADMIN CHECK (for trade commands)
# =========================
async def is_group_admin(update: Update, user_id: int) -> bool:
    """Check if user is a Telegram group admin in the current chat."""
    chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        return False
    try:
        member = await chat.get_member(user_id)
        return member.status in ("administrator", "creator")
    except:
        return False


# =========================
# FORM HANDLER
# =========================
async def send_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    if text not in ["form", "/form", "/deal", "deal"]:
        return

    form_msg = (
        "𝙈𝙍𝙄𝙓𝘿𝙐 𝙀𝙎𝘾𝙍𝙊𝙒 𝙂𝙍𝙊𝙐𝙋🔐\n\n"
        "𝘿𝙚𝙖𝙡 𝘿𝙚𝙩𝙖𝙞𝙡𝙨\n"
        "• Deal Info:   \n"
        "• Buyer:   \n"
        "• Seller:  \n"
        "• Amount:  \n"
        "• Duration:  \n"
        "• Escrow Until:  \n"
        "• Releasee Condition: (Optional)\n\n"
        "𝙀𝙓𝙏𝙍𝘼\n"
        "CRYPTO ADDRESS : (Optional)\n\n"
        "⚠️ 𝙎𝙚𝙘𝙪𝙧𝙞𝙩𝙮 𝙉𝙤𝙩𝙞𝙘𝙚\n"
        "Admins will NEVER DM you for payment.Verify via /adminlist before proceeding."
    )
    await update.message.reply_text(form_msg)


# =========================
# ADD TRADE
# =========================
async def add_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not (is_admin(user_id) or await is_group_admin(update, user_id)):
        await update.message.reply_text("⚠️ Only admins can add trades!")
        return

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("⚠️ Reply to a form message.")
        return

    text = reply.text
    if "Deal Info" not in text:
        await update.message.reply_text("⚠️ Invalid form message.")
        return

    buyer = ""
    seller = ""
    amount = ""

    for line in text.splitlines():
        line = line.replace("•", "").strip()
        if line.startswith("Buyer:"):
            buyer = line.split("Buyer:")[1].strip()
        elif line.startswith("Seller:"):
            seller = line.split("Seller:")[1].strip()
        elif line.startswith("Amount:"):
            amount = line.split("Amount:")[1].strip()

    if "pending_trades" not in context.chat_data:
        context.chat_data["pending_trades"] = []

    context.chat_data["pending_trades"].append({
        "message_id": reply.message_id,
        "buyer": buyer,
        "seller": seller,
        "amount": amount
    })

    msg = (
        f"💰 𝗙𝘂𝗻𝗱𝘀 𝗔𝗱𝗱𝗲𝗱✅,𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗥𝗲𝗰𝗲𝗶𝘃𝗲𝗱,𝗖𝗼𝗻𝘁𝗶𝗻𝘂𝗲 𝗗𝗲𝗮𝗹!\n\n"
        f"🧑‍💼 Escrower: @{update.effective_user.username}\n"
        f"💰 Amount: ₹{amount}\n"
        f"👨🏻‍💼 Buyer: {buyer}\n"
        f"🙎🏻‍♂️ Seller: {seller}\n\n"
        f"🔐 𝗖𝗥𝗘𝗔𝗧𝗘𝗗 𝗕𝗬 @MRIXDUX"
    )
    await reply.reply_text(msg)


# =========================
# DONE TRADE
# =========================
async def done_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not (is_admin(user_id) or await is_group_admin(update, user_id)):
        await update.message.reply_text("⚠️ Only admins can release trades!")
        return

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("⚠️ Reply to trade message.")
        return

    trade_info = None
    if "pending_trades" in context.chat_data:
        for t in context.chat_data["pending_trades"]:
            if t["message_id"] == reply.message_id:
                trade_info = t
                context.chat_data["pending_trades"].remove(t)
                break

    if not trade_info:
        await update.message.reply_text("⚠️ Trade not found.")
        return

    # Admin stats
    user_id_str = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"
    stats = load_stats()
    if user_id_str not in stats:
        stats[user_id_str] = {"count": 0, "total": 0, "username": username}
    stats[user_id_str]["count"] += 1
    try:
        amt = float(trade_info["amount"].replace("₹", "").replace(",", ""))
    except:
        amt = 0
    stats[user_id_str]["total"] += amt
    save_stats(stats)

    # User escrow stats
    user_stats = load_user_stats()
    def update_user_escrow(uname, amount_val):
        if not uname or uname.strip() == "":
            return
        key = uname.lower().lstrip('@')
        if key not in user_stats:
            user_stats[key] = {"total_escrows": 0, "total_amount": 0, "username": uname}
        user_stats[key]["total_escrows"] += 1
        user_stats[key]["total_amount"] += amount_val

    buyer_name = trade_info["buyer"]
    seller_name = trade_info["seller"]
    amount_value = amt
    update_user_escrow(buyer_name, amount_value)
    update_user_escrow(seller_name, amount_value)
    save_user_stats(user_stats)

    msg = (
        "✅ 𝗙𝘂𝗻𝗱𝘀 𝗥𝗲𝗹𝗲𝗮𝘀𝗲𝗱/𝗧𝗿𝗮𝗱𝗲 𝗰𝗹𝗼𝘀𝗲𝗱!\n\n"
        f"🧑‍💼 Released By: @{update.effective_user.username}\n"
        f"💸 Amount: ₹{trade_info['amount']}\n"
        f"👨🏻‍💼 Buyer: {trade_info['buyer']}\n"
        f"🙎🏻‍♂️ Seller: {trade_info['seller']}\n\n"
        "🔐 𝗖𝗥𝗘𝗔𝗧𝗘𝗗 𝗕𝗬 @MRIXDUX"
    )
    await reply.reply_text(msg)


# =========================
# CANCEL TRADE
# =========================
async def cancel_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not (is_admin(user_id) or await is_group_admin(update, user_id)):
        await update.message.reply_text("⚠️ Only admins can cancel trades!")
        return

    reply = update.message.reply_to_message
    if not reply:
        await update.message.reply_text("⚠️ Reply to trade message.")
        return

    if "pending_trades" not in context.chat_data:
        await update.message.reply_text("⚠️ No trades found.")
        return

    trade_info = None
    for t in context.chat_data["pending_trades"]:
        if t["message_id"] == reply.message_id:
            trade_info = t
            context.chat_data["pending_trades"].remove(t)
            break

    if not trade_info:
        await update.message.reply_text("⚠️ Trade not found.")
        return

    await reply.reply_text(
        "🔴 𝗧𝗿𝗮𝗱𝗲/𝗗𝗲𝗮𝗹 𝗖𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱!!!!\n\n"
        f"👮🏻‍♂️ Cancelled By: @{update.effective_user.username}\n"
        f"👨🏻‍💼 Buyer: {trade_info['buyer']}\n"
        f"🙎🏻‍♂️ Seller: {trade_info['seller']}\n\n"
        "🔐 𝗖𝗥𝗘𝗔𝗧𝗘𝗗 𝗕𝗬 @MRIXDUX"
    )


# =========================
# MY DEALS
# =========================
async def mydeals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not (is_admin(user_id) or await is_group_admin(update, user_id)):
        await update.message.reply_text("⚠️ Admin only!")
        return

    stats = load_stats()
    user_id_str = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"

    if user_id_str in stats:
        count = stats[user_id_str]["count"]
        total = stats[user_id_str]["total"]
    else:
        count = 0
        total = 0

    msg = (
        f"📊 Your Escrow Stats @{username}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🧑‍💼 Total Escrows Closed: {count:03d}\n\n"
        f"💰 INR Deals: {count:03d} | ₹{total}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⚙️ Powered by @mrixdufr"
    )
    await update.message.reply_text(msg)


# =========================
# USER INFO (enhanced)
# =========================
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only hardcoded bot admins can use /info (optional)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Admin only!")
        return

    target_user = None
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        username = context.args[0].lstrip('@')
        try:
            # Try to get user from the chat by username
            member = await update.effective_chat.get_member(username)
            target_user = member.user
        except:
            pass

    if not target_user:
        await update.message.reply_text("Reply to a user's message or use /info @username.")
        return

    # Get member status (bot must be admin in group to get status)
    try:
        member = await update.effective_chat.get_member(target_user.id)
        status = member.status
        status_str = {
            "creator": "Creator",
            "administrator": "Administrator",
            "member": "Member",
            "restricted": "Restricted",
            "left": "Left",
            "banned": "Banned"
        }.get(str(status).lower(), str(status))
    except:
        status_str = "Unknown (bot may need admin rights)"

    # Load escrow stats
    user_stats = load_user_stats()
    key = (target_user.username or "").lower()
    escrow_info = user_stats.get(key, {"total_escrows": 0, "total_amount": 0})

    msg = (
        f"👤 **User Info**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{target_user.id}`\n"
        f"📛 First Name: {target_user.first_name or 'N/A'}\n"
        f"📛 Last Name: {target_user.last_name or 'N/A'}\n"
        f"👤 Username: @{target_user.username or 'N/A'}\n"
        f"🔗 [User link](tg://user?id={target_user.id})\n"
        f"📌 Status in group: {status_str}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ Total Escrows: {escrow_info['total_escrows']}\n"
        f"💰 Escrow Amount: ₹{escrow_info['total_amount']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⚙️ Powered by @MRIXDUX"
    )
    await update.message.reply_text(msg, parse_mode='Markdown', disable_web_page_preview=True)


# =========================
# NIGHT MODE (AUTO ON 1AM, OFF 7AM IST)
# =========================
def seconds_until_target_ist(target_hour: int, target_minute: int = 0) -> float:
    now = datetime.now(IST)
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return (target - now).total_seconds()

async def auto_enable_nightmode(chat_id, bot):
    await asyncio.sleep(seconds_until_target_ist(1, 0))
    settings = load_night_settings()
    if not settings.get(str(chat_id), {}).get("auto", False):
        return
    if not night_mode.get(chat_id, False):
        night_mode[chat_id] = True
        try:
            await bot.send_message(chat_id, "🌙 **Auto Night Mode Enabled**\n\nAll non‑admin messages will be deleted.\nAuto‑disable at 7:00 AM IST.", parse_mode="Markdown")
        except:
            pass
    if chat_id in auto_off_tasks:
        auto_off_tasks[chat_id].cancel()
    off_task = asyncio.create_task(auto_disable_nightmode(chat_id, bot))
    auto_off_tasks[chat_id] = off_task
    if chat_id in auto_on_tasks:
        auto_on_tasks[chat_id].cancel()
    next_on = asyncio.create_task(auto_enable_nightmode(chat_id, bot))
    auto_on_tasks[chat_id] = next_on

async def auto_disable_nightmode(chat_id, bot):
    await asyncio.sleep(seconds_until_target_ist(7, 0))
    settings = load_night_settings()
    if not settings.get(str(chat_id), {}).get("auto", False):
        return
    if night_mode.get(chat_id, False):
        night_mode[chat_id] = False
        try:
            await bot.send_message(chat_id, "☀️ **Auto Night Mode Disabled**\n\nIt's 7:00 AM IST. Message deletion turned off.", parse_mode="Markdown")
        except:
            pass
    if chat_id in auto_off_tasks:
        del auto_off_tasks[chat_id]

async def nighton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Works only in groups.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⚠️ Only bot admins can turn on night mode!")
        return
    bot_member = await chat.get_member(context.bot.id)
    if not bot_member.can_delete_messages:
        await update.message.reply_text("❌ I cannot delete messages! Please make me admin with 'Delete Messages' permission.", parse_mode="Markdown")
        return
    chat_id_str = str(chat.id)
    settings = load_night_settings()
    if chat_id_str not in settings:
        settings[chat_id_str] = {}
    settings[chat_id_str]["auto"] = True
    save_night_settings(settings)
    night_mode[chat.id] = True
    if chat.id in auto_on_tasks:
        auto_on_tasks[chat.id].cancel()
    if chat.id in auto_off_tasks:
        auto_off_tasks[chat.id].cancel()
    on_task = asyncio.create_task(auto_enable_nightmode(chat.id, context.bot))
    auto_on_tasks[chat.id] = on_task
    await update.message.reply_text("🌙 **Night Mode Enabled**\n\nAll non‑admin messages will be deleted.\nAuto‑disable at 7:00 AM IST.\nAuto‑enable every day at 1:00 AM IST.\nUse /nightoff to stop.", parse_mode="Markdown")

async def nightoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Works only in groups.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⚠️ Only bot admins can turn off night mode!")
        return
    chat_id_str = str(chat.id)
    settings = load_night_settings()
    if chat_id_str in settings:
        settings.pop(chat_id_str, None)
        save_night_settings(settings)
    night_mode[chat.id] = False
    if chat.id in auto_on_tasks:
        auto_on_tasks[chat.id].cancel()
        del auto_on_tasks[chat.id]
    if chat.id in auto_off_tasks:
        auto_off_tasks[chat.id].cancel()
        del auto_off_tasks[chat.id]
    await update.message.reply_text("☀️ **Night Mode Disabled**\n\nMessages will no longer be deleted.\nAuto schedule removed.", parse_mode="Markdown")

async def delete_non_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ["group", "supergroup"]:
        return
    if not night_mode.get(chat.id, False):
        return
    if is_admin(user.id):
        return
    # Also skip Telegram group admins
    try:
        member = await chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            return
    except:
        pass
    try:
        await update.message.delete()
    except:
        pass

async def check_perms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Run this in a group.")
        return
    bot_member = await chat.get_member(context.bot.id)
    msg = f"🔍 Bot Permissions\ncan_delete_messages: {bot_member.can_delete_messages}\ncan_restrict_members: {bot_member.can_restrict_members}"
    await update.message.reply_text(msg)


# =========================
# RESTORE NIGHT MODE ON STARTUP
# =========================
async def post_init(application):
    settings = load_night_settings()
    for chat_id_str, cfg in settings.items():
        if cfg.get("auto"):
            chat_id = int(chat_id_str)
            on_task = asyncio.create_task(auto_enable_nightmode(chat_id, application.bot))
            auto_on_tasks[chat_id] = on_task


# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.post_init = post_init

    # Form triggers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_form))
    app.add_handler(CommandHandler("form", send_form))
    app.add_handler(CommandHandler("deal", send_form))

    # Escrow commands (hardcoded admins OR group admins)
    app.add_handler(CommandHandler("add", add_trade))
    app.add_handler(CommandHandler("done", done_trade))
    app.add_handler(CommandHandler("cancel", cancel_trade))
    app.add_handler(CommandHandler("mydeals", mydeals))
    app.add_handler(CommandHandler("info", user_info))

    # Night mode commands (only hardcoded admins)
    app.add_handler(CommandHandler("nighton", nighton))
    app.add_handler(CommandHandler("nightoff", nightoff))
    app.add_handler(CommandHandler("checkperms", check_perms))

    # Message deleter (must be last)
    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, delete_non_admin_messages),
        group=1
    )

    print("🚀 Escrow Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
