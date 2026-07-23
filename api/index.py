import os
import re
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get('BOT_TOKEN')
MY_ID = 1174871042

# دیتابیس رایگان ابری برای ذخیره گیفت‌ها
DB_URL = f"https://kvdb.io/giveaways_{MY_ID}/active"

app = Flask(__name__)

def send_to_me(text):
    if not TOKEN:
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    if len(text) > 4000:
        text = text[:4000] + "\n\n...[متن طولانی بود و کوتاه شد]"
    payload = {"chat_id": MY_ID, "text": text}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def save_giveaway_to_db(expire_timestamp, channels, countries):
    try:
        resp = requests.get(DB_URL)
        db_data = resp.json() if resp.status_code == 200 else {"giveaways": []}
        db_data["giveaways"].append({
            "expire_at": expire_timestamp,
            "channels": list(channels),
            "countries": countries
        })
        requests.post(DB_URL, json=db_data)
    except Exception as e:
        print("DB Save Error:", e)

def process_raw_message(msg_dict):
    try:
        extracted_channels = set()
        allowed_countries_text = ""
        giveaway_date_text = ""
        is_active = False
        expire_timestamp = 0
        
        giveaway = msg_dict.get('giveaway') or {}
        if giveaway:
            selection_date_ts = giveaway.get('winners_selection_date')
            if selection_date_ts:
                iran_tz = timezone(timedelta(hours=3, minutes=30))
                dt = datetime.fromtimestamp(selection_date_ts, tz=timezone.utc).astimezone(iran_tz)
                date_str = dt.strftime('%Y/%m/%d ساعت %H:%M')
                now = datetime.now(iran_tz)
                
                if dt < now:
                    giveaway_date_text = f"📅 تاریخ قرعه‌کشی: {date_str} (به وقت ایران)\n⚠️ **توجه: این قرعه‌کشی تمام شده است!** ❌"
                else:
                    giveaway_date_text = f"📅 تاریخ قرعه‌کشی: {date_str} (به وقت ایران) ⏳\n*(در سیستم ثبت شد تا پس از اتمام گزارش داده شود)*"
                    is_active = True
                    expire_timestamp = selection_date_ts

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
            
            if is_active:
                save_giveaway_to_db(expire_timestamp, extracted_channels, allowed_countries_text)
                
        else:
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            send_to_me(f"❌ اطلاعاتی پیدا نشد!\n\nدیتای خام بررسی شود:\n\n{raw_data[:3500]}")

    except Exception as e:
        send_to_me(f"⚠️ خطا در کد استخراج (مدیریت شد):\n{str(e)}")

# --- مسیر گزارش‌گیری دوره‌ای (با شرط گذشت حداقل ۲ ساعت از پایان) ---
@app.route('/check-timers', methods=['GET'])
def check_timers():
    try:
        resp = requests.get(DB_URL)
        if resp.status_code != 200:
            return jsonify({"status": "no active giveaways"}), 200
            
        db_data = resp.json()
        active_giveaways = db_data.get("giveaways", [])
        if not active_giveaways:
            return jsonify({"status": "empty list"}), 200
            
        now_ts = datetime.now(timezone.utc).timestamp()
        # محاسبه زمانی که 2 ساعت پیش بوده است (2 * 3600 = 7200 ثانیه)
        two_hours_ago_ts = now_ts - 7200
        
        still_waiting = []
        ready_to_report = []
        
        for g in active_giveaways:
            # اگر زمان پایان آن از 2 ساعت پیش هم عقب‌تر بود (یعنی 2 ساعت از پایانش گذشته)
            if g["expire_at"] <= two_hours_ago_ts:
                ready_to_report.append(g)
            else:
                # هنوز تمام نشده، یا تمام شده ولی کمتر از 2 ساعت گذشته است
                still_waiting.append(g)
                
        if ready_to_report:
            # ابتدا موارد باقی‌مانده را ذخیره می‌کنیم تا موارد گزارش‌شده حذف شوند
            requests.post(DB_URL, json={"giveaways": still_waiting})
            
            msg = "🔔 **گزارش: این قرعه‌کشی‌ها به پایان رسیده‌اند (بیش از ۲ ساعت قبل):**\n\n"
            for i, ex in enumerate(ready_to_report, 1):
                msg += f"🎁 **مورد {i}:**\n"
                if ex["countries"]:
                    msg += f"{ex['countries']}\n"
                msg += "📢 چنل‌ها:\n" + "\n".join(ex["channels"]) + "\n\n"
                
            send_to_me(msg.strip())
            return jsonify({"status": f"{len(ready_to_report)} alarms sent!"}), 200
            
        return jsonify({"status": "checked, nothing ready to report yet"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        try:
            update = request.get_json(silent=True) or {}
            msg_dict = update.get('message') or update.get('channel_post')
            if msg_dict and isinstance(msg_dict, dict):
                process_raw_message(msg_dict)
        except Exception as e:
            pass
        return jsonify({"status": "ok"}), 200
    else:
        return "✅ Giveaway Checker Bot is running successfully!", 200
