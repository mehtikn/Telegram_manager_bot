import os
import sqlite3
from datetime import timedelta

from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = 8817054298:AAFKxIwtFg2Rek-_lCh-l7705UOasaorE2c

# Database
db = sqlite3.connect("group_stats.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    chat_id INTEGER,
    user_id INTEGER,
    username TEXT,
    first_name TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, user_id)
)
""")
db.commit()


async def is_admin(update: Update, user_id: int) -> bool:
    member = await update.effective_chat.get_member(user_id)
    return member.status in ("administrator", "creator")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = update.effective_message

    if not message or not message.from_user:
        return

    user = message.from_user
    chat = update.effective_chat

    # Count messages
    if chat.type in ("group", "supergroup"):

        cursor.execute("""
        INSERT INTO messages
        (chat_id, user_id, username, first_name, count)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(chat_id, user_id)
        DO UPDATE SET
            count = count + 1,
            username = excluded.username,
            first_name = excluded.first_name
        """, (
            chat.id,
            user.id,
            user.username or "",
            user.first_name or ""
        ))

        db.commit()

    # Only commands with a reply
    if not message.text:
        return

    text = message.text.strip().lower()

    target_message = message.reply_to_message

    # Commands that need a replied user
    if text in ("بن", "ban", "میوت", "mute", "وارن", "warn", "حذف", "del", "delete"):

        if not target_message or not target_message.from_user:
            await message.reply_text("⚠️ باید روی پیام کاربر ریپلای کنی.")
            return

        target = target_message.from_user

        # Only admins can use moderation commands
        if not await is_admin(update, user.id):
            return

        # Don't moderate admins
        if await is_admin(update, target.id):
            await message.reply_text("⚠️ نمی‌تونی روی ادمین این کار رو انجام بدی.")
            return

        # BAN
        if text in ("بن", "ban"):
            await context.bot.ban_chat_member(
                chat.id,
                target.id
            )
            await message.reply_text(
                f"🚫 {target.first_name} بن شد."
            )

        # MUTE
        elif text in ("میوت", "mute"):
            permissions = ChatPermissions(
                can_send_messages=False
            )

            await context.bot.restrict_chat_member(
                chat.id,
                target.id,
                permissions=permissions
            )

            await message.reply_text(
                f"🔇 {target.first_name} میوت شد."
            )

        # WARN
        elif text in ("وارن", "warn"):
            await message.reply_text(
                f"⚠️ به {target.first_name} اخطار داده شد."
            )

        # DELETE
        elif text in ("حذف", "del", "delete"):
            await context.bot.delete_message(
                chat.id,
                target_message.message_id
            )

    # GROUP STATS
    elif text in ("آمار", "stats"):

        if not await is_admin(update, user.id):
            return

        if target_message and target_message.from_user:

            target = target_message.from_user

            cursor.execute("""
            SELECT count FROM messages
            WHERE chat_id = ? AND user_id = ?
            """, (chat.id, target.id))

            result = cursor.fetchone()

            count = result[0] if result else 0

            await message.reply_text(
                f"📊 آمار {target.first_name}\n\n"
                f"💬 تعداد پیام‌ها: {count}"
            )

        else:

            cursor.execute("""
            SELECT first_name, username, count
            FROM messages
            WHERE chat_id = ?
            ORDER BY count DESC
            LIMIT 10
            """, (chat.id,))

            results = cursor.fetchall()

            if not results:
                await message.reply_text("هنوز آماری ثبت نشده.")
                return

            text_result = "🏆 فعال‌ترین اعضای گپ:\n\n"

            for i, row in enumerate(results, 1):
                name, username, count = row

                text_result += (
                    f"{i}. {name} — 💬 {count}\n"
                )

            await message.reply_text(text_result)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 ربات مدیریت گپ فعال شد."
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(filters.COMMAND, start)
    )

    app.add_handler(
        MessageHandler(filters.ALL, handle_message)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
