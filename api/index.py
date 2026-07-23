import os
import re
import json
import requests
from flask import Flask, request

TOKEN = os.environ.get('BOT_TOKEN')
MY_ID = 1174871042

app = Flask(__name__)

# تابع ساده برای ارسال پیام به پیوی شما بدون نیاز به کتابخانه‌های دردسرساز
def send_to_me(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": MY_ID,
        "text": text
    }
    requests.post(url, json=payload)

# تابع پردازش پیام (دقیقاً کدهای خودتان که روی JSON خام اجرا می‌شود)
def process_raw_message(msg_dict):
    try:
        extracted_channels = set()
        
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

        # --- خروجی ---
        if extracted_channels:
            response = "✅ آیدی‌های استخراج شده:\n\n" + "\n".join(extracted_channels)
            send_to_me(response)
        else:
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            send_to_me(f"❌ آیدی پیدا نشد!\nلطفاً کد زیر را بررسی کن:\n\n{raw_data[:3500]}")

    except Exception as e:
        send_to_me(f"⚠️ خطا در سیستم استخراج:\n{str(e)}")

# مسیر اصلی ورسل
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        try:
            update = request.get_json()
            
            # استخراج دقیق پیام از دیتای خام تلگرام
            msg_dict = None
            if 'message' in update:
                msg_dict = update['message']
            elif 'channel_post' in update:
                msg_dict = update['channel_post']
                
            if msg_dict:
                process_raw_message(msg_dict)
                
        except Exception as e:
            print("Error processing webhook:", e)
            
        return "OK", 200
    else:
        return "✅ Giveaway Checker Bot is running bulletproof on Vercel!", 200
