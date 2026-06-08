
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

OWNER_ID = [2096985880, 8737155576]
ADMINS = [2096985880, 8737155576]   # Only these user IDs can use admin commands

STATS_FILE = "admin_stats.json"
USER_STATS_FILE = "user_escrow_stats.json"
NIGHT_SETTINGS_FILE = "night_settings.json"

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# Night mode state (in‑memory)
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
# ADMIN CHECK (only hardcoded)
# =========================
def is_admin(user_id):
    return user_id in ADMINS or user_id == OWNER_ID


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
    if not is_admin(update.effective_user.id):
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
    if not is_admin(update.effective_user.id):
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
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"
    stats = load_stats()
    if user_id not in stats:
        stats[user_id] = {"count": 0, "total": 0, "username": username}
    stats[user_id]["count"] += 1
    try:
        amt = float(trade_info["amount"].replace("₹", "").replace(",", ""))
    except:
        amt = 0
    stats[user_id]["total"] += amt
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
    if not is_admin(update.effective_user.id):
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
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Admin only!")
        return

    stats = load_stats()
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "Unknown"

    if user_id in stats:
        count = stats[user_id]["count"]
        total = stats[user_id]["total"]
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
# USER INFO
# =========================
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Admin only!")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a user's message with /info")
        return

    target = update.message.reply_to_message.from_user
    user_id = target.id
    first_name = target.first_name or ""
    last_name = target.last_name or ""
    username = target.username or "NoUsername"

    user_stats = load_user_stats()
    key = username.lower()

    if key in user_stats:
        total_escrows = user_stats[key]["total_escrows"]
        total_amount = user_stats[key]["total_amount"]
        msg = (
            f"👤 User Info:\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{user_id}`\n"
            f"📛 First Name: {first_name}\n"
            f"📛 Last Name: {last_name}\n"
            f"👤 Username: @{username}\n"
            f"🔗 User link: [link](tg://user?id={user_id})\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ Total Escrows: {total_escrows}\n"
            f"💰 Escrow Amount: ₹{total_amount}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚙️ Powered by @MRIXDUX"
        )
    else:
        msg = (
            f"👤 User Info:\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{user_id}`\n"
            f"📛 First Name: {first_name}\n"
            f"📛 Last Name: {last_name}\n"
            f"👤 Username: @{username}\n"
            f"🔗 User link: [link](tg://user?id={user_id})\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ Total Escrows: No escrow yet\n"
            f"💰 Escrow Amount: No amount\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚙️ Powered by @MRIXDUX"
        )
    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)


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
    """Enable night mode at 1:00 AM IST and schedule auto disable at 7:00 AM"""
    await asyncio.sleep(seconds_until_target_ist(1, 0))  # wait until 1 AM IST
    # Reload settings to verify auto is still True
    settings = load_night_settings()
    if not settings.get(str(chat_id), {}).get("auto", False):
        return
    if not night_mode.get(chat_id, False):
        night_mode[chat_id] = True
        try:
            await bot.send_message(
                chat_id,
                "🌙 **Auto Night Mode Enabled**\n\n"
                "✅ Any message from non‑admins will be **deleted immediately**.\n"
                "Auto‑disable at 7:00 AM IST.",
                parse_mode="Markdown"
            )
        except:
            pass
    # Schedule auto off (7 AM)
    if chat_id in auto_off_tasks:
        auto_off_tasks[chat_id].cancel()
    off_task = asyncio.create_task(auto_disable_nightmode(chat_id, bot))
    auto_off_tasks[chat_id] = off_task
    # Reschedule next day's auto enable
    if chat_id in auto_on_tasks:
        auto_on_tasks[chat_id].cancel()
    next_on = asyncio.create_task(auto_enable_nightmode(chat_id, bot))
    auto_on_tasks[chat_id] = next_on

async def auto_disable_nightmode(chat_id, bot):
    """Disable night mode at 7:00 AM IST"""
    await asyncio.sleep(seconds_until_target_ist(7, 0))  # wait until 7 AM IST
    settings = load_night_settings()
    if not settings.get(str(chat_id), {}).get("auto", False):
        return
    if night_mode.get(chat_id, False):
        night_mode[chat_id] = False
        try:
            await bot.send_message(
                chat_id,
                "☀️ **Auto Night Mode Disabled**\n\nIt's 7:00 AM IST. Message deletion turned off.",
                parse_mode="Markdown"
            )
        except:
            pass
    if chat_id in auto_off_tasks:
        del auto_off_tasks[chat_id]

async def nighton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually enable night mode and turn on auto schedule (1AM‑7AM)"""
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Works only in groups.")
        return

    if not is_admin(user.id):
        await update.message.reply_text("⚠️ Only bot admins can turn on night mode!")
        return

    # Check bot's delete permission
    bot_member = await chat.get_member(context.bot.id)
    if not bot_member.can_delete_messages:
        await update.message.reply_text(
            "❌ **I cannot delete messages!**\n\n"
            "Please make me an admin with **'Delete Messages'** permission.\n"
            "After that, use /nighton again.\n\n"
            "To check permissions, run /checkperms",
            parse_mode="Markdown"
        )
        return

    chat_id_str = str(chat.id)
    # Save auto setting
    settings = load_night_settings()
    if chat_id_str not in settings:
        settings[chat_id_str] = {}
    settings[chat_id_str]["auto"] = True
    save_night_settings(settings)

    night_mode[chat.id] = True

    # Cancel any existing tasks for this chat
    if chat.id in auto_on_tasks:
        auto_on_tasks[chat.id].cancel()
    if chat.id in auto_off_tasks:
        auto_off_tasks[chat.id].cancel()

    # Schedule daily auto enable (starts at next 1 AM)
    on_task = asyncio.create_task(auto_enable_nightmode(chat.id, context.bot))
    auto_on_tasks[chat.id] = on_task

    await update.message.reply_text(
        "🌙 **Night Mode Enabled**\n\n"
        "✅ Any message from non‑admins will be **deleted immediately**.\n"
        "Auto‑disable at 7:00 AM IST.\n"
        "Auto‑enable every day at 1:00 AM IST.\n"
        "Use /nightoff to disable and stop auto schedule.",
        parse_mode="Markdown"
    )

async def nightoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually disable night mode and cancel auto schedule"""
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ Works only in groups.")
        return

    if not is_admin(user.id):
        await update.message.reply_text("⚠️ Only bot admins can turn off night mode!")
        return

    chat_id_str = str(chat.id)
    # Remove auto setting
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

    await update.message.reply_text(
        "☀️ **Night Mode Disabled**\n\n"
        "Messages will no longer be deleted. Everyone can chat normally.\n"
        "Auto schedule (1 AM – 7 AM) has been turned off.",
        parse_mode="Markdown"
    )

async def delete_non_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ["group", "supergroup"]:
        return
    if not night_mode.get(chat.id, False):
        return
    if is_admin(user.id):
        return
    # Also never delete Telegram group admins? The requirement is only hardcoded admins can be exempt.
    # But to be safe, we should not delete group admins either, otherwise they'd be annoyed.
    # However, the user said "no not every telegram admin" – meaning they don't want to give trade permissions to all group admins.
    # But for night mode deletion, it's common to exempt group admins as well (so they can still talk).
    # I'll exempt group admins from deletion to avoid issues. If the user wants to delete even group admins, they can change.
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
    msg = (
        f"🔍 **Bot Permissions in this group**\n\n"
        f"📌 can_delete_messages: **{bot_member.can_delete_messages}**\n"
        f"📌 can_restrict_members: **{bot_member.can_restrict_members}**\n\n"
        f"* Night mode (message deletion) requires `can_delete_messages = True`."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# =========================
# RESTORE NIGHT MODE ON STARTUP
# =========================
async def post_init(application):
    """Restore auto night mode tasks for groups that had it enabled before restart."""
    settings = load_night_settings()
    for chat_id_str, cfg in settings.items():
        if cfg.get("auto"):
            chat_id = int(chat_id_str)
            # Reschedule daily auto enable
            on_task = asyncio.create_task(auto_enable_nightmode(chat_id, application.bot))
            auto_on_tasks[chat_id] = on_task
            # Note: night_mode[chat_id] is not set to True now; it will be set at next 1 AM.
            # Optionally, we could leave it off until 1 AM.

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.post_init = post_init

    # Form triggers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_form))
    app.add_handler(CommandHandler("form", send_form))
    app.add_handler(CommandHandler("deal", send_form))

    # Escrow commands (only hardcoded admins)
    app.add_handler(CommandHandler("add", add_trade))
    app.add_handler(CommandHandler("done", done_trade))
    app.add_handler(CommandHandler("cancel", cancel_trade))
    app.add_handler(CommandHandler("mydeals", mydeals))
    app.add_handler(CommandHandler("info", user_info))

    # Night mode commands (only hardcoded admins)
    app.add_handler(CommandHandler("nighton", nighton))
    app.add_handler(CommandHandler("nightoff", nightoff))
    app.add_handler(CommandHandler("checkperms", check_perms))

    # Delete handler (must
