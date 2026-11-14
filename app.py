import os
import logging
import sqlite3
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = "@team_shadow_striker"
CHANNEL_URL = "https://t.me/team_shadow_striker"
DB = "shadow.db"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY,
            coins INTEGER DEFAULT 0,
            verified INTEGER DEFAULT 0,
            referrer INTEGER,
            daily TEXT
        )
    """)
    con.commit()
    return con

def get_user(uid):
    con = db()
    con.execute("INSERT OR IGNORE INTO users(uid) VALUES(?)", (uid,))
    row = con.execute(
        "SELECT coins, verified, referrer, daily FROM users WHERE uid=?",
        (uid,)
    ).fetchone()
    con.commit()
    con.close()
    return row

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)

    if context.args:
        try:
            ref = int(context.args[0])
            if ref != uid:
                con = db()
                con.execute(
                    "UPDATE users SET referrer=? WHERE uid=? AND referrer IS NULL",
                    (ref, uid)
                )
                con.commit()
                con.close()
        except ValueError:
            pass

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL)],
        [InlineKeyboardButton("✅ Verify Join", callback_data="verify")]
    ]
    await update.message.reply_text(
        "👑 Welcome to Shadow X Tracker!\n\n"
        "ব্যবহার করতে আগে আমাদের চ্যানেলে Join করো।",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    try:
        member = await context.bot.get_chat_member(CHANNEL, uid)
        if member.status not in ("member", "administrator", "creator"):
            raise ValueError("Not joined")
    except Exception:
        await query.message.reply_text(
            "❌ আগে চ্যানেলে Join করো, তারপর Verify করো।"
        )
        return

    con = db()
    row = con.execute(
        "SELECT coins, verified, referrer FROM users WHERE uid=?",
        (uid,)
    ).fetchone()

    if not row[1]:
        con.execute(
            "UPDATE users SET coins=coins+5, verified=1 WHERE uid=?",
            (uid,)
        )
        ref = row[2]
        if ref and ref != uid:
            refrow = con.execute(
                "SELECT verified FROM users WHERE uid=?", (ref,)
            ).fetchone()
            if refrow and refrow[0]:
                con.execute(
                    "UPDATE users SET coins=coins+5 WHERE uid=?", (ref,)
                )
                try:
                    await context.bot.send_message(
                        ref, "🎉 নতুন Referral সফল! +5 Coins পেয়েছো।"
                    )
                except Exception:
                    pass

    con.commit()
    con.close()

    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🔗 My Referral Link", callback_data="ref")]
    ]
    await query.message.reply_text(
        "✅ Verification Successful!\n🎉 Welcome!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "verify":
        await verify(update, context)
        return

    row = get_user(uid)
    if not row[1]:
        await q.message.reply_text("আগে /start দিয়ে Verify করো।")
        return

    con = db()

    if q.data == "balance":
        await q.message.reply_text(f"💰 তোমার Balance: {row[0]} Coins")

    elif q.data == "daily":
        today = date.today().isoformat()
        if row[3] == today:
            await q.message.reply_text("আজকের Bonus ইতিমধ্যে নিয়েছো।")
        else:
            con.execute(
                "UPDATE users SET coins=coins+2, daily=? WHERE uid=?",
                (today, uid)
            )
            con.commit()
            await q.message.reply_text("🎁 Daily Bonus +2 Coins!")

    elif q.data == "profile":
        user = q.from_user
        await q.message.reply_text(
            f"👤 Name: {user.full_name}\n"
            f"🆔 ID: {uid}\n"
            f"💰 Coins: {row[0]}"
        )

    elif q.data == "ref":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start={uid}"
        await q.message.reply_text(f"🔗 তোমার Referral Link:\n{link}")

    con.close()

async def post_init(app):
    base = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")
    await app.bot.set_webhook(
        url=f"{base}/telegram",
        allowed_updates=Update.ALL_TYPES
    )

def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu))
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        url_path="telegram",
        webhook_url=f"{os.environ['RENDER_EXTERNAL_URL'].rstrip('/')}/telegram"
    )

if __name__ == "__main__":
    main()
