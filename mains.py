from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3
import os
import re
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)

# =============== CONFIG ================
# NAYA BOT TOKEN (jo tune abhi diya)
BOT_TOKEN = "8742243511:AAEu6AJyuzqUhFXcQK8yxEKY2vm7nZr-JPA"

REQUIRED_CHANNELS = [
    "@LynxInfo_Official",
    "@Lynx_api", 
    "@TeamNobitaOfficial",
    "@NobitaOsintTeamm",
    "@NobitaOsintBackup",
    "@TeamNobitaChat"
]
ADMIN_ID = 8202721675

# Premium Emoji IDs
JOIN_BTN_EMOJI = "6269103435413459285"
CLAIM_BTN_EMOJI = "6271652704662065458"
ACCESS_EMOJI = "6269115585875939943"
MUST_JOIN_EMOJI = "6282567341842633593"
# =========================================

# Database
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, verified INTEGER DEFAULT 0)')
cursor.execute('CREATE TABLE IF NOT EXISTS content (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, data TEXT, caption TEXT)')
conn.commit()

def convert_premium_emojis(text):
    if not text:
        return text
    pattern1 = r'\{premiumemojiid(\d+)\}'
    def replace1(match):
        return f'<tg-emoji emoji-id="{match.group(1)}">⭐</tg-emoji>'
    text = re.sub(pattern1, replace1, text)
    
    pattern2 = r'<emoji>(\d+)</emoji>'
    def replace2(match):
        return f'<tg-emoji emoji-id="{match.group(1)}">⭐</tg-emoji>'
    text = re.sub(pattern2, replace2, text)
    
    return text

async def is_subscribed_all(user_id, context):
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                print(f"❌ User {user_id} not in {channel}")
                return False
        except Exception as e:
            print(f"⚠️ Error checking {channel}: {e}")
            # Agar bot admin nahi hai channel mein toh assume karo user joined hai
            # Isko change kar sakte ho
            continue
    return True

async def send_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT type, data, caption FROM content ORDER BY id DESC LIMIT 1")
    content = cursor.fetchone()
    
    if content:
        t, d, c = content
        if t == "text":
            parsed = convert_premium_emojis(d)
            await update.message.reply_text(parsed, parse_mode='HTML')
        elif t == "photo":
            caption = convert_premium_emojis(c) if c else ""
            await update.message.reply_photo(photo=d, caption=caption, parse_mode='HTML')
        elif t == "video":
            caption = convert_premium_emojis(c) if c else ""
            await update.message.reply_video(video=d, caption=caption, parse_mode='HTML')
        elif t == "file":
            caption = convert_premium_emojis(c) if c else ""
            await update.message.reply_document(document=d, caption=caption, parse_mode='HTML')
    else:
        await update.message.reply_text("No content set. Use /admin to add.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("Unauthorized!")
        return
    
    keyboard = [
        [InlineKeyboardButton("ADD TEXT", callback_data="add_text")],
        [InlineKeyboardButton("ADD PHOTO", callback_data="add_photo")],
        [InlineKeyboardButton("ADD VIDEO", callback_data="add_video")],
        [InlineKeyboardButton("ADD FILE", callback_data="add_file")],
        [InlineKeyboardButton("BROADCAST", callback_data="broadcast")],
        [InlineKeyboardButton("STATS", callback_data="stats")],
        [InlineKeyboardButton("CLOSE", callback_data="close")]
    ]
    
    await update.message.reply_text(
        "ADMIN PANEL\n\nChoose option:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"📥 Start from user: {user_id}")
    
    cursor.execute("SELECT verified FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    
    if result and result[0] == 1:
        print(f"✅ User {user_id} already verified")
        await send_content(update, context)
        return
    
    print(f"🔍 Checking subscription for user {user_id}")
    if await is_subscribed_all(user_id, context):
        print(f"✅ User {user_id} verified!")
        cursor.execute("INSERT OR REPLACE INTO users (user_id, verified) VALUES (?, 1)", (user_id,))
        conn.commit()
        await send_content(update, context)
    else:
        print(f"❌ User {user_id} not subscribed - showing join page")
        keyboard = []
        row = []
        for i, channel in enumerate(REQUIRED_CHANNELS):
            row.append(InlineKeyboardButton(
                text="JOIN CHANNEL",
                url=f"https://t.me/{channel[1:]}",
                icon_custom_emoji_id=JOIN_BTN_EMOJI
            ))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton(
            text="CLAIM",
            callback_data="verify",
            icon_custom_emoji_id=CLAIM_BTN_EMOJI
        )])
        
        msg_text = f"""<tg-emoji emoji-id="{ACCESS_EMOJI}">⚠️</tg-emoji> Access Restricted <tg-emoji emoji-id="{ACCESS_EMOJI}">⚠️</tg-emoji>

<tg-emoji emoji-id="{MUST_JOIN_EMOJI}">⭐</tg-emoji> Must Join All Channels To Use This Bot <tg-emoji emoji-id="{MUST_JOIN_EMOJI}">⭐</tg-emoji>"""
        
        await update.message.reply_text(
            msg_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data
    
    if data == "verify":
        print(f"🔘 Claim clicked by user: {user_id}")
        if await is_subscribed_all(user_id, context):
            print(f"✅ User {user_id} claim successful!")
            cursor.execute("INSERT OR REPLACE INTO users (user_id, verified) VALUES (?, 1)", (user_id,))
            conn.commit()
            await query.message.delete()
            new_update = Update(update.update_id, message=query.message, effective_user=update.effective_user)
            await send_content(new_update, context)
        else:
            print(f"❌ User {user_id} claim failed - not in all channels")
            await query.answer("Join all channels first!", show_alert=True)
        return
    
    if data == "back":
        keyboard = [
            [InlineKeyboardButton("ADD TEXT", callback_data="add_text")],
            [InlineKeyboardButton("ADD PHOTO", callback_data="add_photo")],
            [InlineKeyboardButton("ADD VIDEO", callback_data="add_video")],
            [InlineKeyboardButton("ADD FILE", callback_data="add_file")],
            [InlineKeyboardButton("BROADCAST", callback_data="broadcast")],
            [InlineKeyboardButton("STATS", callback_data="stats")],
            [InlineKeyboardButton("CLOSE", callback_data="close")]
        ]
        await query.edit_message_text("ADMIN PANEL\n\nChoose option:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if data == "add_text":
        context.user_data['action'] = "text"
        await query.edit_message_text(
            "Send TEXT content\n\nUse <emoji>ID</emoji> for premium emojis\n\nExample:\nHello World <emoji>6271627012167701001</emoji>\n\nSend /cancel to abort",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]])
        )
        return
    
    if data == "add_photo":
        context.user_data['action'] = "photo"
        await query.edit_message_text(
            "Send PHOTO\n\nCaption can have <emoji>ID</emoji>\n\nSend /cancel to abort",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]])
        )
        return
    
    if data == "add_video":
        context.user_data['action'] = "video"
        await query.edit_message_text(
            "Send VIDEO\n\nCaption can have <emoji>ID</emoji>\n\nSend /cancel to abort",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]])
        )
        return
    
    if data == "add_file":
        context.user_data['action'] = "file"
        await query.edit_message_text(
            "Send FILE\n\nCaption can have <emoji>ID</emoji>\n\nSend /cancel to abort",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]])
        )
        return
    
    if data == "broadcast":
        context.user_data['action'] = "broadcast"
        await query.edit_message_text(
            "Send BROADCAST message\n\nUse <emoji>ID</emoji> for premium emojis\n\nSend /cancel to abort",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]])
        )
        return
    
    if data == "stats":
        cursor.execute("SELECT COUNT(*) FROM users WHERE verified=1")
        users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM content")
        contents = cursor.fetchone()[0]
        await query.edit_message_text(
            f"STATISTICS\n\nVerified Users: {users}\nContent Items: {contents}\nChannels: {len(REQUIRED_CHANNELS)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]])
        )
        return
    
    if data == "close":
        await query.delete_message()
        return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if 'action' not in context.user_data:
        return
    
    action = context.user_data['action']
    msg = update.message
    
    if action == "text":
        if msg.text and msg.text != "/cancel":
            cursor.execute("DELETE FROM content")
            cursor.execute("INSERT INTO content (type, data, caption) VALUES (?, ?, ?)", ("text", msg.text, ""))
            conn.commit()
            await msg.reply_text("TEXT SAVED!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]]))
            del context.user_data['action']
        elif msg.text == "/cancel":
            del context.user_data['action']
            await msg.reply_text("Cancelled")
    
    elif action == "photo":
        if msg.photo:
            cursor.execute("DELETE FROM content")
            cursor.execute("INSERT INTO content (type, data, caption) VALUES (?, ?, ?)", ("photo", msg.photo[-1].file_id, msg.caption or ""))
            conn.commit()
            await msg.reply_text("PHOTO SAVED!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]]))
            del context.user_data['action']
    
    elif action == "video":
        if msg.video:
            cursor.execute("DELETE FROM content")
            cursor.execute("INSERT INTO content (type, data, caption) VALUES (?, ?, ?)", ("video", msg.video.file_id, msg.caption or ""))
            conn.commit()
            await msg.reply_text("VIDEO SAVED!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]]))
            del context.user_data['action']
    
    elif action == "file":
        if msg.document:
            cursor.execute("DELETE FROM content")
            cursor.execute("INSERT INTO content (type, data, caption) VALUES (?, ?, ?)", ("file", msg.document.file_id, msg.caption or ""))
            conn.commit()
            await msg.reply_text("FILE SAVED!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]]))
            del context.user_data['action']
    
    elif action == "broadcast":
        if msg.text and msg.text != "/cancel":
            parsed = convert_premium_emojis(msg.text)
            cursor.execute("SELECT user_id FROM users WHERE verified=1")
            users = cursor.fetchall()
            success = 0
            for user in users:
                try:
                    await context.bot.send_message(user[0], parsed, parse_mode='HTML')
                    success += 1
                except:
                    pass
            await msg.reply_text(f"BROADCAST SENT TO {success} USERS!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("BACK", callback_data="back")]]))
            del context.user_data['action']
        elif msg.text == "/cancel":
            del context.user_data['action']
            await msg.reply_text("Cancelled")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"""PREMIUM EMOJI GUIDE

JOIN BUTTON EMOJI: {JOIN_BTN_EMOJI}
CLAIM BUTTON EMOJI: {CLAIM_BTN_EMOJI}
ACCESS EMOJI: {ACCESS_EMOJI}
MUST JOIN EMOJI: {MUST_JOIN_EMOJI}

Use <emoji>ID</emoji> format in messages"""
    
    await update.message.reply_text(help_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'action' in context.user_data:
        del context.user_data['action']
        await update.message.reply_text("Cancelled")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.VIDEO, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    
    print("="*50)
    print("🤖 BOT IS RUNNING!")
    print(f"✅ Bot Token: {BOT_TOKEN[:20]}...")
    print(f"✅ Admin ID: {ADMIN_ID}")
    print(f"✅ Channels: {len(REQUIRED_CHANNELS)}")
    print("="*50)
    
    # Always use polling mode for Termux and simple deployments
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
