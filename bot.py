import telebot
import google.generativeai as genai
import time

# ✅ Put your tokens here
TELEGRAM_TOKEN = "8761229801:AAFKsR67YPIYeu6X523FGAZU-XXpLWrV7qY"
GEMINI_API_KEY = "AIzaSyBG-W-5tyVZzlq5vf5nlfMCB8xGEK_xrWk"

# Admin password
ADMIN_PASSWORD = "Priyanshi4321"

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Storage
all_members = set()
admin_ids = set()
pending_broadcast = {}
awaiting_password = {}

# Bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========== GET AI REPLY ==========
def get_ai_reply(message):
    try:
        response = model.generate_content(
            "You are a friendly helpful AI assistant. "
            "Reply naturally in the same language as the user. "
            "Keep replies short and clear.\n\nUser: " + message
        )
        return response.text
    except Exception as e:
        return "Sorry, try again! 😊"

# ========== /start ==========
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    all_members.add(user_id)
    bot.send_message(user_id,
        "👋 Welcome! I'm your AI assistant.\n"
        "Feel free to ask me anything! 😊"
    )

# ========== /admin ==========
@bot.message_handler(commands=["admin"])
def admin_login(message):
    user_id = message.chat.id
    awaiting_password[user_id] = "admin_login"
    bot.send_message(user_id, "🔐 Enter admin password:")

# ========== /members ==========
@bot.message_handler(commands=["members"])
def member_count(message):
    user_id = message.chat.id
    if user_id in admin_ids:
        bot.send_message(user_id, f"👥 Total members: {len(all_members)}")
    else:
        bot.send_message(user_id, "⛔ You are not authorized.")

# ========== MAIN MESSAGE HANDLER ==========
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    user_id = message.chat.id
    user_message = message.text.strip()

    all_members.add(user_id)

    # ---- Password input ----
    if user_id in awaiting_password:
        intent = awaiting_password[user_id]

        if intent == "admin_login":
            if user_message == ADMIN_PASSWORD:
                admin_ids.add(user_id)
                del awaiting_password[user_id]
                bot.send_message(user_id,
                    "✅ Admin login successful!\n\n"
                    "Now send any message to broadcast to all members.\n"
                    "Use /members to see member count."
                )
            else:
                del awaiting_password[user_id]
                bot.send_message(user_id, "❌ Wrong password! Access denied.")
            return

        if intent == "broadcast":
            if user_message == ADMIN_PASSWORD:
                broadcast_text = pending_broadcast.pop(user_id, None)
                del awaiting_password[user_id]

                if not broadcast_text:
                    bot.send_message(user_id, "⚠️ No message found.")
                    return

                success, failed = 0, 0
                for member_id in list(all_members):
                    if member_id == user_id:
                        continue
                    try:
                        bot.send_message(member_id,
                            f"📢 Message from Admin:\n\n{broadcast_text}"
                        )
                        success += 1
                        time.sleep(0.3)
                    except Exception:
                        failed += 1

                bot.send_message(user_id,
                    f"✅ Broadcast complete!\n"
                    f"📤 Sent: {success} | ❌ Failed: {failed}"
                )
            else:
                pending_broadcast.pop(user_id, None)
                del awaiting_password[user_id]
                bot.send_message(user_id, "❌ Wrong password! Broadcast cancelled.")
            return

    # ---- Admin broadcast ----
    if user_id in admin_ids:
        pending_broadcast[user_id] = user_message
        awaiting_password[user_id] = "broadcast"
        bot.send_message(user_id,
            f"📨 You want to send:\n\n{user_message}\n\n"
            f"🔐 Enter password to confirm:"
        )
        return

    # ---- Member: AI reply ----
    bot.send_chat_action(user_id, "typing")
    reply = get_ai_reply(user_message)
    bot.reply_to(message, reply)


print("🤖 Bot is running...")
bot.infinity_polling()