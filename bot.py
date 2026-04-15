
import telebot
from pytgpt.auto import AUTO
import time
import json
import os
import threading

# ========== কনফিগারেশন ==========
TELEGRAM_TOKEN = "8761229801:AAFKsR67YPIYeu6X523FGAZU-XXpLWrV7qY"  # ⚠️ নতুন টোকেন দিন
ADMIN_PASSWORD = "Priyanshi4321"

# python-tgpt (কোনো API key লাগে না)
bot_ai = AUTO()

# স্টোরেজ
all_members = set()
admin_ids = set()
conversation_history = {}
all_messages = []
member_messages = {}
custom_responses = {}  # কাস্টম রেসপন্স স্টোর

# ফাইল স্টোরেজ
MESSAGES_FILE = "all_messages.json"
MEMBERS_FILE = "all_members.json"
CUSTOM_FILE = "custom_responses.json"

# অ্যাডমিন স্টেট ট্র্যাকিং
awaiting_password = {}
awaiting_user_message = {}
awaiting_bot_reply = {}
pending_custom_response = {}

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========== ডাটা লোড/সেভ ==========
def load_data():
    global all_members, all_messages, member_messages, custom_responses
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_messages = data.get('messages', [])
            member_messages = data.get('member_messages', {})
    if os.path.exists(MEMBERS_FILE):
        with open(MEMBERS_FILE, 'r', encoding='utf-8') as f:
            all_members = set(json.load(f))
    if os.path.exists(CUSTOM_FILE):
        with open(CUSTOM_FILE, 'r', encoding='utf-8') as f:
            custom_responses = json.load(f)

def save_data():
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'messages': all_messages,
            'member_messages': member_messages
        }, f, ensure_ascii=False, indent=2)
    with open(MEMBERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(all_members), f, ensure_ascii=False, indent=2)
    with open(CUSTOM_FILE, 'w', encoding='utf-8') as f:
        json.dump(custom_responses, f, ensure_ascii=False, indent=2)

# ========== মেসেজ সংরক্ষণ ==========
def save_message(user_id, user_name, user_message, bot_reply):
    msg_data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': user_id,
        'user_name': user_name,
        'message': user_message,
        'bot_reply': bot_reply
    }
    all_messages.append(msg_data)
    
    if str(user_id) not in member_messages:
        member_messages[str(user_id)] = []
    member_messages[str(user_id)].append(msg_data)
    
    if len(all_messages) > 500:
        all_messages.pop(0)
    
    save_data()

# ========== টাইপিং ইন্ডিকেটর + এআই রিপ্লাই ==========
def get_ai_reply_with_typing(user_id, message, chat_id):
    """টাইপিং ইন্ডিকেটর দেখিয়ে এআই রিপ্লাই দেয়"""
    try:
        # টাইপিং ইন্ডিকেটর শুরু (একটা থ্রেডে)
        def show_typing():
            for _ in range(3):  # 3 বার টাইপিং দেখাবে
                bot.send_chat_action(chat_id, "typing")
                time.sleep(1.5)
        
        typing_thread = threading.Thread(target=show_typing)
        typing_thread.start()
        
        # কনভার্সেশন মেমরি
        history = conversation_history.get(user_id, [])
        
        prompt = f"""You are a friendly helpful AI assistant. Reply naturally in the same language as the user. Keep replies short and clear.

Previous conversation:"""
        
        for msg in history[-10:]:
            prompt += f"\n{msg['role']}: {msg['content']}"
        
        prompt += f"\n\nUser: {message}\nAssistant:"

        reply = bot_ai.chat(prompt)
        
        if not reply or len(reply.strip()) == 0:
            reply = "😊"
        
        # মেমরিতে সেভ
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        conversation_history[user_id].append({"role": "user", "content": message})
        conversation_history[user_id].append({"role": "assistant", "content": reply})
        
        if len(conversation_history[user_id]) > 20:
            conversation_history[user_id] = conversation_history[user_id][-20:]
        
        return reply
        
    except Exception as e:
        print(f"Error: {e}")
        return "Sorry, having trouble. Please try again! 😊"

# ========== সব মেম্বারের মেসেজ দেখা ==========
def get_all_members_messages():
    if not all_messages:
        return "📭 No messages yet."
    
    user_messages = {}
    for msg in all_messages[-100:]:  # শেষ 100টি মেসেজ
        user_id = msg['user_id']
        user_name = msg['user_name']
        if user_id not in user_messages:
            user_messages[user_id] = {
                'name': user_name,
                'messages': []
            }
        user_messages[user_id]['messages'].append(msg)
    
    result = "📊 *ALL MEMBERS MESSAGES*\n\n"
    result += f"📝 Total messages: {len(all_messages)}\n"
    result += f"👥 Total members: {len(all_members)}\n"
    result += "─" * 30 + "\n\n"
    
    for user_id, data in user_messages.items():
        result += f"👤 *{data['name']}* (ID: `{user_id}`)\n"
        result += f"💬 Messages: {len(data['messages'])}\n"
        
        for msg in data['messages'][-3:]:
            result += f"   📨 `{msg['message'][:30]}`\n"
            result += f"   🤖 ➜ {msg['bot_reply'][:40]}...\n"
        result += "\n" + "─" * 20 + "\n\n"
    
    return result

# ========== কমান্ডসমূহ ==========
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id
    chat_id = message.chat.id
    all_members.add(user_id)
    save_data()
    
    # টাইপিং ইন্ডিকেটর
    bot.send_chat_action(chat_id, "typing")
    time.sleep(0.5)
    
    bot.send_message(user_id, 
        "👋 *Welcome to AI Assistant Bot!*\n\n"
        "I can reply to your messages naturally.\n\n"
        "*Commands:*\n"
        "├ /start - Restart conversation\n"
        "├ /clear - Clear chat history\n"
        "├ /admin - Admin login\n"
        "├ /members - View all messages (admin)\n"
        "├ /myid - Show your user ID\n"
        "├ /stats - Show statistics\n"
        "└ /setresponse - Add custom response (admin)\n\n"
        "💡 *Features:*\n"
        "• Shows typing indicator when replying\n"
        "• Remembers conversation context\n"
        "• No API key required\n\n"
        "Ask me anything! 😊",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["myid"])
def show_my_id(message):
    user_id = message.chat.id
    bot.send_chat_action(user_id, "typing")
    time.sleep(0.3)
    bot.send_message(user_id, f"🆔 Your user ID: `{user_id}`", parse_mode="Markdown")

@bot.message_handler(commands=["stats"])
def show_stats(message):
    user_id = message.chat.id
    bot.send_chat_action(user_id, "typing")
    time.sleep(0.5)
    
    stats = f"📊 *Bot Statistics*\n\n"
    stats += f"👥 Total members: {len(all_members)}\n"
    stats += f"💬 Total messages: {len(all_messages)}\n"
    stats += f"🎨 Custom responses: {len(custom_responses)}\n"
    stats += f"👤 Active users: {len(member_messages)}\n"
    
    if user_id in admin_ids:
        stats += f"\n📝 *Messages per user:*\n"
        for uid, msgs in list(member_messages.items())[:10]:
            stats += f"   • User `{uid}`: {len(msgs)} messages\n"
    
    bot.send_message(user_id, stats, parse_mode="Markdown")

@bot.message_handler(commands=["clear"])
def clear_history(message):
    user_id = message.chat.id
    bot.send_chat_action(user_id, "typing")
    time.sleep(0.3)
    
    if user_id in conversation_history:
        del conversation_history[user_id]
    bot.send_message(user_id, "🧹 Your conversation history has been cleared!")

@bot.message_handler(commands=["admin"])
def admin_login(message):
    user_id = message.chat.id
    bot.send_chat_action(user_id, "typing")
    time.sleep(0.3)
    awaiting_password[user_id] = "admin_login"
    bot.send_message(user_id, "🔐 Enter admin password:")

@bot.message_handler(commands=["members"])
def show_all_messages(message):
    user_id = message.chat.id
    
    if user_id not in admin_ids:
        bot.send_chat_action(user_id, "typing")
        time.sleep(0.3)
        bot.send_message(user_id, "⛔ Only admin can view all messages.")
        return
    
    bot.send_chat_action(user_id, "typing")
    time.sleep(0.5)
    bot.send_message(user_id, "📊 Fetching all member messages...")
    
    all_msgs = get_all_members_messages()
    
    if len(all_msgs) > 4000:
        parts = [all_msgs[i:i+4000] for i in range(0, len(all_msgs), 4000)]
        for part in parts:
            bot.send_message(user_id, part, parse_mode="Markdown")
            time.sleep(0.5)
    else:
        bot.send_message(user_id, all_msgs, parse_mode="Markdown")

@bot.message_handler(commands=["setresponse"])
def set_response(message):
    user_id = message.chat.id
    
    if user_id not in admin_ids:
        bot.send_chat_action(user_id, "typing")
        time.sleep(0.3)
        bot.send_message(user_id, "⛔ Only admin can use this command.")
        return
    
    bot.send_chat_action(user_id, "typing")
    time.sleep(0.3)
    bot.send_message(user_id, 
        "📝 *Custom Response Setup*\n\n"
        "Step 1: Send me the message that users will type.\n"
        "Example: `hello` or `hi`\n\n"
        "Type /cancel to cancel.",
        parse_mode="Markdown"
    )
    awaiting_user_message[user_id] = "custom_response_user"

@bot.message_handler(commands=["cancel"])
def cancel(message):
    user_id = message.chat.id
    bot.send_chat_action(user_id, "typing")
    time.sleep(0.3)
    awaiting_user_message.pop(user_id, None)
    awaiting_bot_reply.pop(user_id, None)
    awaiting_password.pop(user_id, None)
    pending_custom_response.pop(user_id, None)
    bot.send_message(user_id, "❌ Operation cancelled.")

# ========== ব্রডকাস্ট ==========
def broadcast_to_members(admin_id, user_message, bot_reply):
    success, failed = 0, 0
    
    for member_id in list(all_members):
        if member_id == admin_id:
            continue
        try:
            message_text = f"📨 *New Custom Response Added!*\n\n"
            message_text += f"👤 *User said:* `{user_message}`\n"
            message_text += f"🤖 *Bot replies:* {bot_reply}\n\n"
            message_text += f"💡 Try sending `{user_message}` to see the response!"
            
            bot.send_message(member_id, message_text, parse_mode="Markdown")
            success += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"Failed: {e}")
            failed += 1
    
    return success, failed

# ========== মূল মেসেজ হ্যান্ডলার ==========
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    user_id = message.chat.id
    chat_id = message.chat.id
    user_message = message.text.strip()
    user_name = message.from_user.first_name or "User"
    
    all_members.add(user_id)
    save_data()
    
    # ----- 1. পাসওয়ার্ড চেক -----
    if user_id in awaiting_password:
        intent = awaiting_password[user_id]
        
        if intent == "admin_login":
            if user_message == ADMIN_PASSWORD:
                admin_ids.add(user_id)
                del awaiting_password[user_id]
                bot.send_chat_action(chat_id, "typing")
                time.sleep(0.5)
                bot.send_message(user_id, 
                    "✅ *Admin login successful!*\n\n"
                    "You can now use:\n"
                    "├ /setresponse - Add custom responses\n"
                    "├ /members - View all messages\n"
                    "└ /stats - View statistics",
                    parse_mode="Markdown"
                )
            else:
                del awaiting_password[user_id]
                bot.send_chat_action(chat_id, "typing")
                time.sleep(0.3)
                bot.send_message(user_id, "❌ Wrong password! Access denied.")
            return
    
    # ----- 2. কাস্টম রেসপন্স: ইউজার মেসেজ -----
    if user_id in awaiting_user_message and awaiting_user_message[user_id] == "custom_response_user":
        if user_message.startswith("/"):
            cancel(message)
            return
        
        pending_custom_response[user_id] = user_message
        del awaiting_user_message[user_id]
        awaiting_bot_reply[user_id] = True
        
        bot.send_chat_action(chat_id, "typing")
        time.sleep(0.3)
        bot.send_message(user_id, 
            f"✅ Got it!\n\n"
            f"📝 User message: `{user_message}`\n\n"
            f"Step 2: Now send me the reply that the bot should give.\n"
            f"Type /cancel to cancel.",
            parse_mode="Markdown"
        )
        return
    
    # ----- 3. কাস্টম রেসপন্স: বটের উত্তর -----
    if user_id in awaiting_bot_reply:
        if user_message.startswith("/"):
            cancel(message)
            return
        
        user_msg = pending_custom_response.get(user_id, "")
        bot_reply_text = user_message
        
        if user_msg and bot_reply_text:
            custom_responses[user_msg.lower()] = bot_reply_text
            save_data()
            
            bot.send_chat_action(chat_id, "typing")
            time.sleep(0.5)
            bot.send_message(user_id, "📢 Broadcasting to all members...")
            
            success, failed = broadcast_to_members(user_id, user_msg, bot_reply_text)
            
            bot.send_message(user_id, 
                f"✅ *Custom response added!*\n\n"
                f"📝 `{user_msg}` ➜ {bot_reply_text}\n\n"
                f"📊 Broadcast: Sent {success} | Failed {failed}",
                parse_mode="Markdown"
            )
        
        del awaiting_bot_reply[user_id]
        del pending_custom_response[user_id]
        return
    
    # ----- 4. কাস্টম রেসপন্স চেক -----
    if user_message.lower() in custom_responses:
        bot.send_chat_action(chat_id, "typing")
        time.sleep(0.5)
        reply = custom_responses[user_message.lower()]
        bot.reply_to(message, reply)
        
        # মেসেজ সেভ
        save_message(user_id, user_name, user_message, reply)
        return
    
    # ----- 5. সাধারণ এআই রিপ্লাই (টাইপিং ইন্ডিকেটর সহ) -----
    reply = get_ai_reply_with_typing(user_id, user_message, chat_id)
    bot.reply_to(message, reply)
    
    # মেসেজ সেভ
    save_message(user_id, user_name, user_message, reply)

# ========== বট চালু ==========
load_data()

print("=" * 50)
print("🤖 BOT IS RUNNING WITH ALL FEATURES")
print("=" * 50)
print(f"Admin password: {ADMIN_PASSWORD}")
print("\n✅ Features enabled:")
print("   • Typing indicator (users see bot typing)")
print("   • Online status (bot shows online)")
print("   • Custom responses")
print("   • Message history for all members")
print("   • Conversation memory")
print("   • No API key required")
print("\n📌 Commands for users:")
print("   /start - Start bot")
print("   /myid - Show your ID")
print("   /stats - Show statistics")
print("   /clear - Clear history")
print("\n🔐 Admin commands (after /admin):")
print("   /members - View all messages")
print("   /setresponse - Add custom response")
print("   /stats - Full statistics")
print("\n" + "=" * 50)
print("Press Ctrl+C to stop")
print("=" * 50)

try:
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
except KeyboardInterrupt:
    print("\n🛑 Bot stopped.")
except Exception as e:
    print(f"Error: {e}")def member_count(message):
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
