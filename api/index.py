import os
import re
import json
import requests
from flask import Flask, request, jsonify

TOKEN = os.environ.get('BOT_TOKEN')
MY_ID = 1174871042

app = Flask(__name__)

# تابع ارسال پیام به پیوی (با محدودیت زمانی برای جلوگیری از خاموش شدن ورسل)
def send_to_me(text):
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # تلگرام پیام‌های طولانی‌تر از 4096 کاراکتر را مسدود می‌کند، پس آن را برش می‌زنیم
    if len(text) > 4000:
        text = text[:4000] + "\n\n...[متن طولانی بود و کوتاه شد]"
        
    payload = {
        "chat_id": MY_ID,
        "text": text
    }
    try:
        # timeout=5 باعث می‌شود ورسل روی این درخواست گیر نکند و کرش ندهد
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Request Timeout or Error: {e}")

# تابع پردازش کاملاً محافظت‌شده
def process_raw_message(msg_dict):
    try:
        extracted_channels = set()
        
        # ۱. بررسی دیتای قرعه‌کشی (Giveaway)
        giveaway = msg_dict.get('giveaway') or {}
        chats = giveaway.get('chats') or []
        for chat in chats:
            if 'username' in chat:
                extracted_channels.add('@' + chat['username'].lower())
            else:
                extracted_channels.add(f"🔒 کانال خصوصی: {chat.get('title', 'نامشخص')} (ID: {chat.get('id', '')})")

        # ۲. بررسی فوروارد
        forward_origin = msg_dict.get('forward_origin') or {}
        chat = forward_origin.get('chat') or {}
        if chat.get('username'):
            extracted_channels.add('@' + chat['username'].lower())
        
        # ۳. بررسی متن اصلی و کپشن‌ها
        text = msg_dict.get('text') or msg_dict.get('caption') or ''
        if isinstance(text, str) and text:
            for u in re.findall(r'@\w+', text):
                extracted_channels.add(u.lower())
            for l in re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text):
                if len(l) < 32 and not l.startswith('+'):
                    extracted_channels.add('@' + l.lower())

        # ۴. بررسی لینک‌های مخفی (دکمه‌های اینلاین و هایپرلینک‌ها)
        entities = (msg_dict.get('entities') or []) + (msg_dict.get('caption_entities') or [])
        for ent in entities:
            if isinstance(ent, dict) and ent.get('type') == 'text_link':
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', ent.get('url', ''))
                if match:
                    extracted_channels.add('@' + match.group(1).lower())

        # ۵. بررسی دکمه‌های شیشه‌ای پایین پیام
        reply_markup = msg_dict.get('reply_markup') or {}
        inline_keyboard = reply_markup.get('inline_keyboard') or []
        for row in inline_keyboard:
            if isinstance(row, list):
                for button in row:
                    if isinstance(button, dict):
                        url = button.get('url', '')
                        match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', url)
                        if match:
                            extracted_channels.add('@' + match.group(1).lower())

        # --- ارسال خروجی ---
        if extracted_channels:
            response = "✅ آیدی‌های استخراج شده:\n\n" + "\n".join(extracted_channels)
            send_to_me(response)
        else:
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            send_to_me(f"❌ آیدی پیدا نشد!\n\nدیتای خام بررسی شود:\n\n{raw_data}")

    except Exception as e:
        send_to_me(f"⚠️ خطا در کد استخراج (مدیریت شد):\n{str(e)}")

# مسیر اصلی ورسل
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        try:
            # silent=True باعث می‌شود اگر پیام نامعتبر بود ورسل کرش نکند
            update = request.get_json(silent=True) or {}
            
            # پیدا کردن بدنه اصلی پیام تلگرام
            msg_dict = update.get('message') or update.get('channel_post')
                
            if msg_dict and isinstance(msg_dict, dict):
                process_raw_message(msg_dict)
                
        except Exception as e:
            print("Critical Webhook Error:", e)
            
        # بلافاصله به تلگرام میگوییم پیام را گرفتیم تا ورسل پردازش را ببندد
        return jsonify({"status": "ok"}), 200
    else:
        return "✅ Giveaway Checker Bot is running bulletproof on Vercel!", 200
