import telebot
import re
import os
import json
from flask import Flask, request

TOKEN = os.environ.get('BOT_TOKEN')
# آیدی عددی اکانت اصلی شما (@lovepotion)
MY_ID = 1174871042

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# این هندلر تمام پیام‌های دریافتی ربات را پردازش می‌کند
@bot.message_handler(func=lambda message: True)
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

        # --- ارسال نتایج مستقیماً به پیوی شما (MY_ID) ---
        if extracted_channels:
            response = "✅ آیدی‌های استخراج شده:\n\n" + "\n".join(extracted_channels)
            bot.send_message(MY_ID, response)
        else:
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            bot.send_message(MY_ID, f"❌ آیدی پیدا نشد!\nلطفاً کد زیر را بررسی کن:\n\n{raw_data[:3500]}")

    except Exception as e:
        bot.send_message(MY_ID, f"⚠️ خطا در سیستم استخراج:\n{str(e)}")

# مسیر اصلی ورسل برای دریافت آپدیت‌های تلگرام
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        # دریافت پیام از تلگرام و دادن آن به هندلر بالا
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "✅ Giveaway Checker Bot is successfully running on Vercel!", 200
