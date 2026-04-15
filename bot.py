import telebot
import google.generativeai as genai
import time
import re

# ========== আপনার টোকেন এখানে দিন ==========
TELEGRAM_TOKEN = "8761229801:AAFKsR67YPIYeu6X523FGAZU-XXpLWrV7qY"
GEMINI_API_KEY = "AIzaSyBDuGZJ_aVFg1tIE9blMveMkAj7dlSbzdM"
ADMIN_PASSWORD = "Priyanshi4321"

# জেমিনি কনফিগার
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# স্টোরেজ
all_members = set()
admin_ids = set()
pending_broadcast = {}
awaiting_password = {}
conversation_history = {}  # প্রতি ইউজারের আলাদা মেমরি

# বট
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========== মেমরি ফাংশন ==========
def get_history(user_id):
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    return conversation_history[user_id]

def save_to_history(user_id, user_msg, bot_reply):
    history = get_history(user_id)
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": bot_reply})
    # শেষ ১০ বার্তা রাখি
    if len(history) > 20:
        conversation_history[user_id] = history[-20:]

def clear_history_for_user(user_id):
    if user_id in conversation_history:
        del conversation_history[user_id]

# ========== এআই রিপ্লাই (মেমরি সহ) ==========
def get_ai_reply(user_id, message):
    try:
        history = get_history(user_id)
        
        # প্রম্পট তৈরি
        prompt = """You are a friendly helpful AI assistant. Reply naturally in the same language as the user. Keep replies short, warm and clear.

Previous conversation:"""

        for msg in history[-10:]:  # শেষ ১০টি মেসেজ
            prompt += f"\n{msg['role']}: {msg['content']}"

        prompt += f"\n\nuser: {message}\nassistant:"

        response = model.generate_content(prompt)
        reply = response.text.strip()
        
        # খালি রিপ্লাই চেক
        if not reply:
            reply = "😊"
        
        # মেমরিতে সেভ
        save_to_history(user_id, message, reply)
        
        return reply
        
    except Exception as e:
        print(f"Gemini Error for user {user_id}: {e}")
        return "Sorry, I'm having trouble right now. Please try again in a moment. 😊"

# ========== /start কমান্ড ==========
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    all_members.add(user_id)
    clear_history_for_user(user_id)  # নতুন করে শুরু করলে মেমরি ক্লিয়ার
    
    bot.send_message(user_id, 
        "👋 Welcome! I'm your AI assistant.\n"
        "Feel free to ask me anything! 😊\n\n"
        "Commands:\n"
        "/start - Restart conversation\n"
        "/clear - Clear chat history\n"
        "/admin - Admin login\n"
        "/members - Show member count (admin only)"
    )

# ========== /clear কমান্ড ==========
@bot.message_handler(commands=["clear"])
def clear_history(message):
    user_id = message.chat.id
    clear_history_for_user(user_id)
    bot.send_message(user_id, "🧹 Your conversation history has been cleared!")

# ========== /admin কমান্ড ==========
@bot.message_handler(commands=["admin"])
def admin_login(message):
    user_id = message.chat.id
    awaiting_password[user_id] = "admin_login"
    bot.send_message(user_id, "🔐 Enter admin password:")

# ========== /members কমান্ড ==========
@bot.message_handler(commands=["members"])
def member_count(message):
    user_id = message.chat.id
    if user_id in admin_ids:
        bot.send_message(user_id, f"👥 Total members: {len(all_members)}")
    else:
        bot.send_message(user_id, "⛔ You are not authorized.")

# ========== মূল মেসেজ হ্যান্ডলার ==========
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    user_id = message.chat.id
    user_message = message.text.strip()
    
    # ইউজারকে মেম্বার লিস্টে যোগ করুন
    all_members.add(user_id)
    
    # ----- পাসওয়ার্ড ইনপুট চেক -----
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
                
                bot.send_message(user_id, "📢 Broadcasting message to all members...")
                
                success, failed = 0, 0
                for member_id in list(all_members):
                    if member_id == user_id:
                        continue
                    try:
                        bot.send_message(member_id, 
                            f"📢 Message from Admin:\n\n{broadcast_text}"
                        )
                        success += 1
                        time.sleep(0.1)  # রেট লিমিট এড়াতে
                    except Exception as e:
                        print(f"Failed to send to {member_id}: {e}")
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
    
    # ----- অ্যাডমিন ব্রডকাস্ট -----
    if user_id in admin_ids:
        pending_broadcast[user_id] = user_message
        awaiting_password[user_id] = "broadcast"
        bot.send_message(user_id, 
            f"📨 You want to send:\n\n{user_message}\n\n"
            f"🔐 Enter password to confirm broadcast:"
        )
        return
    
    # ----- সাধারণ ইউজার: এআই রিপ্লাই -----
    bot.send_chat_action(user_id, "typing")
    
    # ছোট মেসেজের জন্য একটু বিলম্ব (নরমাল টাইপিং ইফেক্ট)
    time.sleep(0.3)
    
    reply = get_ai_reply(user_id, user_message)
    bot.reply_to(message, reply)

# ========== বট চালু করুন ==========
print("🤖 Bot is running with conversation memory...")
print(f"Admin password: {ADMIN_PASSWORD}")
print("Press Ctrl+C to stop")

try:
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
except KeyboardInterrupt:
    print("\n🛑 Bot stopped.")
except Exception as e:
    print(f"Error: {e}")
