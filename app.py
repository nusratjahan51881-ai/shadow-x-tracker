import os
import sqlite3
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@team_shadow_striker"
DB = "shadow.db"

def db():
    return sqlite3.connect(DB)

def setup():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users(
            uid INTEGER PRIMARY KEY,
            coins INTEGER DEFAULT 0,
            joined INTEGER DEFAULT 0,
            referred_by INTEGER,
            bonus TEXT
        )
        """)

def get_user(uid):
    with db() as con:
        return con.execute(
            "SELECT coins, joined, referred_by, bonus FROM users WHERE uid=?",
            (uid,)
        ).fetchone()

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Generate Link", callback_data="link")],
        [
            InlineKeyboardButton("💰 My Balance", callback_data="balance"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="bonus")
        ],
        [
            InlineKeyboardButton("👥 Refer & Earn", callback_data="refer"),
            InlineKeyboardButton("👤 My Profile", callback_data="profile")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    setup()

    with db() as con:
        row = con.execute(
            "SELECT uid FROM users WHERE uid=?", (uid,)
        ).fetchone()

        if not row:
            ref = None
            if context.args:
                try:
                    candidate = int(context.args[0])
                    if candidate != uid:
                        ref = candidate
                except ValueError:
                    pass

            con.execute(
                "INSERT INTO users(uid, coins, joined, referred_by) VALUES(?,0,0,?)",
                (uid, ref)
            )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📢 Join Channel",
            url="https://t.me/team_shadow_striker"
        )],
        [InlineKeyboardButton(
            "✅ Verify Membership",
            callback_data="verify"
        )]
    ])

    await update.message.reply_text(
        "🌸 Welcome to Shadow X Tracker!\n\n"
        "বট ব্যবহার করতে প্রথমে আমাদের চ্যানেলে Join করুন।\n"
        "তারপর Verify চাপুন।",
        reply_markup=keyboard
    )

async def verified(update, context):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    try:
        member = await context.bot.get_chat_member(
            CHANNEL, user.id
        )
        if member.status not in ("member", "administrator", "creator"):
            await query.message.reply_text(
                "❌ আপনি এখনো চ্যানেলে Join করেননি।"
            )
            return
    except Exception:
        await query.message.reply_text(
            "⚠️ Membership যাচাই করা যাচ্ছে না। "
            "বটকে চ্যানেলের Admin করুন।"
        )
        return

    with db() as con:
        row = con.execute(
            "SELECT coins, joined, referred_by FROM users WHERE uid=?",
            (user.id,)
        ).fetchone()

        if row is None:
            con.execute(
                "INSERT INTO users(uid, coins, joined) VALUES(?,0,0)",
                (user.id,)
            )
            row = (0, 0, None)

        coins, joined, referrer = row

        if not joined:
            con.execute(
                "UPDATE users SET coins=coins+5, joined=1 WHERE uid=?",
                (user.id,)
            )

            if referrer:
                ref_row = con.execute(
                    "SELECT joined FROM users WHERE uid=?",
                    (referrer,)
                ).fetchone()

                if ref_row:
                    con.execute(
                        "UPDATE users SET coins=coins+5 WHERE uid=?",
                        (referrer,)
                    )
                    try:
                        await context.bot.send_message(
                            referrer,
                            "🎉 অভিনন্দন! আপনার Referral সম্পন্ন হয়েছে।\n"
                            "আপনি পেয়েছেন +৫ Coins 🌸"
                        )
                    except Exception:
                        pass

    name = user.full_name
    username = f"@{user.username}" if user.username else "নেই"

    caption = (
        f"🌸 Welcome to Shadow X Tracker!\n\n"
        f"👤 Name: {name}\n"
        f"📛 Username: {username}\n"
        f"🆔 ID: {user.id}\n"
        f"🪙 Balance: 5 Coins (প্রথমবার Verify করলে)\n\n"
        "আমাদের বটে স্বাগতম! ❤️"
    )

    photos = await context.bot.get_user_profile_photos(
        user.id, limit=1
    )

    if photos.total_count:
        photo = photos.photos[0][-1].file_id
        await query.message.reply_photo(
            photo=photo,
            caption=caption,
            reply_markup=menu()
        )
    else:
        await query.message.reply_text(
            caption, reply_markup=menu()
        )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    user = get_user(uid)
    if not user or not user[1]:
        await query.message.reply_text(
            "আগে /start দিয়ে Channel Verify করুন।"
        )
        return

    coins, joined, referrer, bonus = user

    if data == "balance":
        await query.message.reply_text(
            f"💰 আপনার Balance: {coins} Coins"
        )

    elif data == "bonus":
        today = datetime.utcnow().date().isoformat()

        if bonus == today:
            await query.message.reply_text(
                "⏳ আজকের Daily Bonus ইতিমধ্যে নিয়েছেন।"
            )
        else:
            with db() as con:
                con.execute(
                    "UPDATE users SET coins=coins+2, bonus=? WHERE uid=?",
                    (today, uid)
                )
            await query.message.reply_text(
                "🎁 Daily Bonus সফল!\n🪙 +২ Coins"
            )

    elif data == "refer":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={uid}"
        await query.message.reply_text(
            "👥 Refer & Earn\n\n"
            "আপনার Referral Link:\n"
            f"{link}\n\n"
            "প্রতিটি নতুন Verified Referral-এ +৫ Coins 🌸"
        )

    elif data == "profile":
        await query.message.reply_text(
            f"👤 Name: {query.from_user.full_name}\n"
            f"📛 Username: @{query.from_user.username or 'None'}\n"
            f"🆔 ID: {uid}\n"
            f"🪙 Coins: {coins}"
        )

    elif data == "link":
        await query.message.reply_text(
            "🔗 Link Generation\n\n"
            "এই ফিচারের সম্মতিভিত্তিক ওয়েবপেজ "
            "পরবর্তী সেটআপ ধাপে যুক্ত হবে।\n"
            "এখন কোনো কয়েন কাটা হবে না।"
        )

async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable missing")

    setup()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(
        verified, pattern="^verify$"
    ))
    app.add_handler(CallbackQueryHandler(buttons))

    print("Shadow X Tracker Bot Started")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    import asyncio
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
