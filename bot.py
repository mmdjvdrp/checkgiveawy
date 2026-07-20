import telebot
import re
import os
import json
from flask import Flask
import threading
import time

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def process_message(message):
    try:
        extracted_channels = set()
        
        # گرفتن دیتای خام
        msg_dict = message.json
        
        # ۱. بررسی دیتای قرعه‌کشی
        if 'giveaway' in msg_dict and 'chats' in msg_dict['giveaway']:
            for chat in msg_dict['giveaway']['chats']:
                if 'username' in chat:
                    extracted_channels.add('@' + chat['username'].lower())
                else:
                    extracted_channels.add(f"🔒 کانال خصوصی: {chat.get('title')} (ID: {chat.get('id')})")

        # ۲. بررسی فوروارد
        if 'forward_origin' in msg_dict:
            chat = msg_dict['forward_origin'].get('chat', {})
            if chat.get('username'):
                extracted_channels.add('@' + chat['username'].lower())
        
        # ۳. بررسی متن
        text = msg_dict.get('text', '') or msg_dict.get('caption', '')
        for u in re.findall(r'@\w+', text):
            extracted_channels.add(u.lower())
        for l in re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text):
            if len(l) < 32 and not l.startswith('+'):
                extracted_channels.add('@' + l.lower())

        # ۴. بررسی لینک‌های مخفی
        entities = msg_dict.get('entities', []) + msg_dict.get('caption_entities', [])
        for ent in entities:
            if ent.get('type') == 'text_link':
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', ent.get('url', ''))
                if match:
                    extracted_channels.add('@' + match.group(1).lower())

        # ۵. بررسی دکمه‌ها
        reply_markup = msg_dict.get('reply_markup', {})
        inline_keyboard = reply_markup.get('inline_keyboard', [])
        for row in inline_keyboard:
            for button in row:
                url = button.get('url', '')
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', url)
                if match:
                    extracted_channels.add('@' + match.group(1).lower())

        # --- تغییرات اینجاست: حذف کامل Markdown برای جلوگیری از ارور تلگرام ---
        if extracted_channels:
            response = "✅ ایدی های استخراج شده:\n\n" + "\n".join(extracted_channels)
            # ارسال به صورت متن کاملا ساده
            bot.reply_to(message, response)
        else:
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            # ارسال متن کاملا ساده و بدون هیچ فرمتی
            bot.reply_to(message, f"❌ ایدی پیدا نشد!\nلطفا کد زیر را برای من کپی کن:\n\n{raw_data[:3500]}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ خطا در سیستم:\n{str(e)}")

# رادار پیام‌ها
def update_listener(messages):
    for message in messages:
        process_message(message)

bot.set_update_listener(update_listener)

@app.route('/')
def index():
    return "✅ Bot is running!"

def run_bot():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=60)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
