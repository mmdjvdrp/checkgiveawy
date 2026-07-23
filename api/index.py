import os
import re
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get('BOT_TOKEN')
MY_ID = 1174871042

app = Flask(__name__)

def send_to_me(text):
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    if len(text) > 4000:
        text = text[:4000] + "\n\n...[متن طولانی بود و کوتاه شد]"
        
    payload = {
        "chat_id": MY_ID,
        "text": text
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Request Timeout or Error: {e}")

def process_raw_message(msg_dict):
    try:
        extracted_channels = set()
        allowed_countries_text = ""
        giveaway_date_text = ""
        
        giveaway = msg_dict.get('giveaway') or {}
        if giveaway:
            selection_date_ts = giveaway.get('winners_selection_date')
            if selection_date_ts:
                # ساخت تایم‌زون ایران (+03:30)
                iran_tz = timezone(timedelta(hours=3, minutes=30))
                
                # تبدیل تاریخ سرور به تاریخ و ساعت ایران
                dt = datetime.fromtimestamp(selection_date_ts, tz=timezone.utc).astimezone(iran_tz)
                date_str = dt.strftime('%Y/%m/%d ساعت %H:%M')
                
                # زمان الان به وقت ایران
                now = datetime.now(iran_tz)
                
                # مقایسه اینکه آیا تاریخ قرعه‌کشی گذشته است یا نه
                if dt < now:
                    giveaway_date_text = f"📅 تاریخ قرعه‌کشی: {date_str} (به وقت ایران)\n⚠️ **توجه: این قرعه‌کشی تمام شده است!** ❌"
                else:
                    giveaway_date_text = f"📅 تاریخ قرعه‌کشی: {date_str} (به وقت ایران) ⏳"

            chats = giveaway.get('chats') or []
            for chat in chats:
                if 'username' in chat:
                    extracted_channels.add('@' + chat['username'].lower())
                else:
                    extracted_channels.add(f"🔒 کانال خصوصی: {chat.get('title', 'نامشخص')} (ID: {chat.get('id', '')})")
            
            country_codes = giveaway.get('country_codes') or []
            if country_codes:
                flags = []
                for code in country_codes:
                    code_upper = code.upper()
                    flag_emoji = chr(ord(code_upper[0]) + 127397) + chr(ord(code_upper[1]) + 127397)
                    flags.append(f"{code_upper} {flag_emoji}")
                allowed_countries_text = "🌍 کشورهای مجاز: " + " | ".join(flags)
            else:
                allowed_countries_text = "🌍 کشورهای مجاز: همه کشورها (Global) 🌐"

        forward_origin = msg_dict.get('forward_origin') or {}
        chat = forward_origin.get('chat') or {}
        if chat.get('username'):
            extracted_channels.add('@' + chat['username'].lower())
        
        text = msg_dict.get('text') or msg_dict.get('caption') or ''
        if isinstance(text, str) and text:
            for u in re.findall(r'@\w+', text):
                extracted_channels.add(u.lower())
            for l in re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text):
                if len(l) < 32 and not l.startswith('+'):
                    extracted_channels.add('@' + l.lower())

        entities = (msg_dict.get('entities') or []) + (msg_dict.get('caption_entities') or [])
        for ent in entities:
            if isinstance(ent, dict) and ent.get('type') == 'text_link':
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', ent.get('url', ''))
                if match:
                    extracted_channels.add('@' + match.group(1).lower())

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

        if extracted_channels or allowed_countries_text or giveaway_date_text:
            response = "✅ اطلاعات استخراج شده:\n\n"
            if giveaway_date_text:
                response += giveaway_date_text + "\n"
            if allowed_countries_text:
                response += allowed_countries_text + "\n\n"
            if extracted_channels:
                response += "📢 چنل‌ها:\n" + "\n".join(extracted_channels)
                
            send_to_me(response.strip())
        else:
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            send_to_me(f"❌ اطلاعاتی پیدا نشد!\n\nدیتای خام بررسی شود:\n\n{raw_data[:3500]}")

    except Exception as e:
        send_to_me(f"⚠️ خطا در کد استخراج (مدیریت شد):\n{str(e)}")

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        try:
            update = request.get_json(silent=True) or {}
            msg_dict = update.get('message') or update.get('channel_post')
                
            if msg_dict and isinstance(msg_dict, dict):
                process_raw_message(msg_dict)
                
        except Exception as e:
            print("Critical Webhook Error:", e)
            
        return jsonify({"status": "ok"}), 200
    else:
        return "✅ Giveaway Checker Bot is running successfully!", 200
