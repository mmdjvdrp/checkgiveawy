import telebot
import re
import os
import json
from flask import Flask
import threading
import time

TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# لیست تمام انواع پیام‌ها (حتی پیام‌های ناشناخته و آپدیت‌های جدید تلگرام)
ALL_TYPES = [
    'text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker',
    'giveaway', 'giveaway_winners', 'giveaway_completed', 'unknown'
]

@bot.message_handler(func=lambda message: True, content_types=ALL_TYPES)
def extract_channels(message):
    try:
        extracted_channels = set()
        
        # گرفتن دیتای کاملاً خام از قلب تلگرام (بدون واسطه)
        msg_dict = message.json
        
        # ۱. شکار کانال‌ها از باکس اختصاصی Giveaway (همون وسط پیام که گفتی)
        if 'giveaway' in msg_dict and 'chats' in msg_dict['giveaway']:
            for chat in msg_dict['giveaway']['chats']:
                if 'username' in chat:
                    extracted_channels.add('@' + chat['username'].lower())
                else:
                    extracted_channels.add(f"🔒 کانال خصوصی: {chat.get('title')} (ID: {chat.get('id')})")

        # ۲. شکار کانال اسپانسر از طریق دیتای "فوروارد" (بالای پیام)
        if 'forward_origin' in msg_dict:
            chat = msg_dict['forward_origin'].get('chat', {})
            if chat.get('username'):
                extracted_channels.add('@' + chat['username'].lower())
        elif 'forward_from_chat' in msg_dict:
            chat = msg_dict['forward_from_chat']
            if chat.get('username'):
                extracted_channels.add('@' + chat['username'].lower())

        # ۳. بررسی متن پیام، لینک‌های مخفی و دکمه‌های شیشه‌ای (برای پیام‌های ترکیبی)
        text = msg_dict.get('text', '') or msg_dict.get('caption', '')
        for u in re.findall(r'@\w+', text):
            extracted_channels.add(u.lower())
        
        for l in re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text):
            if len(l) < 32 and not l.startswith('+'):
                extracted_channels.add('@' + l.lower())

        entities = msg_dict.get('entities', []) + msg_dict.get('caption_entities', [])
        for ent in entities:
            if ent.get('type') == 'text_link':
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', ent.get('url', ''))
                if match:
                    extracted_channels.add('@' + match.group(1).lower())

        reply_markup = msg_dict.get('reply_markup', {})
        inline_keyboard = reply_markup.get('inline_keyboard', [])
        for row in inline_keyboard:
            for button in row:
                url = button.get('url', '')
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', url)
                if match:
                    extracted_channels.add('@' + match.group(1).lower())

        # --- ارسال نتیجه نهایی به کاربر ---
        if extracted_channels:
            response = "✅ **آیدی‌های استخراج شده:**\n\n" + "\n".join(extracted_channels)
            bot.reply_to(message, response, parse_mode='Markdown')
        else:
            # 🔴 سیستم هوشمند: اگر نتوانست پیدا کند، کد خام تلگرام را برای شما می‌فرستد!
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            bot.reply_to(message, f"❌ آیدی مستقیم پیدا نشد!\nلطفا کد زیر رو کپی کن و برای من (هوش مصنوعی) بفرست تا ببینم تلگرام کجا قایمش کرده:\n\n```json\n{raw_data[:3500]}\n```", parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ خطا در پردازش:\n`{str(e)}`", parse_mode='Markdown')

@app.route('/')
def index():
    return "✅ Bot is running on Render!"

def run_bot():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=60)
    except:
        pass

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
