import telebot
import re
import os
import json
from flask import Flask
import threading
import time
import traceback

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ توکن یافت نشد!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# این تابع پردازشگر اصلی ماست
def process_message(message):
    try:
        extracted_channels = set()
        
        # گرفتن دیتای خام و بدون سانسور از تلگرام
        msg_dict = message.json
        
        # ۱. بررسی دیتای قرعه‌کشی (Giveaway)
        if 'giveaway' in msg_dict and 'chats' in msg_dict['giveaway']:
            for chat in msg_dict['giveaway']['chats']:
                if 'username' in chat:
                    extracted_channels.add('@' + chat['username'].lower())
                else:
                    extracted_channels.add(f"🔒 کانال خصوصی: {chat.get('title')} (ID: {chat.get('id')})")

        # ۲. بررسی فوروارد از سمت کانال (گاهی آیدی اسپانسر اینجاست)
        if 'forward_origin' in msg_dict:
            chat = msg_dict['forward_origin'].get('chat', {})
            if chat.get('username'):
                extracted_channels.add('@' + chat['username'].lower())
        
        # ۳. بررسی متن پیام
        text = msg_dict.get('text', '') or msg_dict.get('caption', '')
        for u in re.findall(r'@\w+', text):
            extracted_channels.add(u.lower())
        for l in re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text):
            if len(l) < 32 and not l.startswith('+'):
                extracted_channels.add('@' + l.lower())

        # ۴. بررسی لینک‌های مخفی (Hyperlinks)
        entities = msg_dict.get('entities', []) + msg_dict.get('caption_entities', [])
        for ent in entities:
            if ent.get('type') == 'text_link':
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', ent.get('url', ''))
                if match:
                    extracted_channels.add('@' + match.group(1).lower())

        # ۵. بررسی دکمه‌های شیشه‌ای
        reply_markup = msg_dict.get('reply_markup', {})
        inline_keyboard = reply_markup.get('inline_keyboard', [])
        for row in inline_keyboard:
            for button in row:
                url = button.get('url', '')
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', url)
                if match:
                    extracted_channels.add('@' + match.group(1).lower())

        # --- ارسال نتیجه نهایی ---
        if extracted_channels:
            response = "✅ **آیدی‌های استخراج شده:**\n\n" + "\n".join(extracted_channels)
            bot.reply_to(message, response, parse_mode='Markdown')
        else:
            # اگر هیچ آیدی پیدا نکرد، دیتای خام را برای شما می‌فرستد
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            bot.reply_to(message, f"❌ آیدی مستقیم پیدا نشد!\nلطفاً کد زیر رو کپی کن و برای من (هوش مصنوعی) بفرست تا ببینم تلگرام دقیقاً ساختارش رو چطوری چیده:\n\n```json\n{raw_data[:3500]}\n```", parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ خطا:\n`{str(e)}`", parse_mode='Markdown')

# 🎯 رادار قدرتمند: دور زدن فیلترهای کتابخانه و گرفتن مستقیم تمام پیام‌ها
def update_listener(messages):
    for message in messages:
        process_message(message)

# متصل کردن رادار به ربات
bot.set_update_listener(update_listener)


# ---------------- کدهای اجرای سرور ----------------
@app.route('/')
def index():
    return "✅ Bot is running properly!"

def run_bot():
    try:
        bot.remove_webhook()
        time.sleep(1)
        # روشن نگه داشتن ربات
        bot.infinity_polling(timeout=60)
    except Exception as e:
        print(f"Server Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
