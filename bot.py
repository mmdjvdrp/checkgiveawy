import telebot
import re
import os
import json
from flask import Flask
import threading
import traceback
import time

# دریافت توکن
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ ارور: توکن ربات (BOT_TOKEN) پیدا نشد!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# گرفتن انواع پیام‌ها
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'giveaway', 'giveaway_winners'])
def extract_channel_ids(message):
    try:
        extracted_channels = set()
        
        # دریافت دیتای کاملاً خام پیام به شکل دیکشنری (بدون واسطه)
        msg_dict = message.json
        
        # 1. بررسی دیتای قرعه‌کشی (Giveaway)
        if 'giveaway' in msg_dict:
            giveaway_data = msg_dict['giveaway']
            if 'chats' in giveaway_data:
                for chat in giveaway_data['chats']:
                    if 'username' in chat:
                        extracted_channels.add('@' + chat['username'].lower())
                    else:
                        extracted_channels.add(f"🔒 کانال خصوصی: {chat.get('title')} (ID: {chat.get('id')})")

        # 2. بررسی متن پیام یا کپشن
        text = msg_dict.get('text', '') or msg_dict.get('caption', '')
        
        usernames = re.findall(r'@\w+', text)
        for u in usernames:
            extracted_channels.add(u.lower())

        links = re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text)
        for l in links:
            if len(l) < 32 and not l.startswith('+'):
                extracted_channels.add('@' + l.lower())

        # 3. بررسی لینک‌های مخفی شده در متن (Text Entities / Hyperlinks)
        entities = msg_dict.get('entities', []) + msg_dict.get('caption_entities', [])
        for ent in entities:
            if ent.get('type') == 'text_link':
                url = ent.get('url', '')
                match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', url)
                if match:
                    channel_id = match.group(1)
                    if len(channel_id) < 32 and not channel_id.startswith('+'):
                        extracted_channels.add('@' + channel_id.lower())

        # 4. بررسی دکمه‌های شیشه‌ای (Inline Keyboard)
        reply_markup = msg_dict.get('reply_markup', {})
        inline_keyboard = reply_markup.get('inline_keyboard', [])
        for row in inline_keyboard:
            for button in row:
                url = button.get('url', '')
                if 't.me/' in url or 'telegram.me/' in url:
                    match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', url)
                    if match:
                        channel_id = match.group(1)
                        if len(channel_id) < 32 and not channel_id.startswith('+'):
                            extracted_channels.add('@' + channel_id.lower())

        # --- ارسال نتیجه به کاربر ---
        if extracted_channels:
            response = "✅ **آیدی‌های پیدا شده:**\n\n" + "\n".join(extracted_channels)
            bot.reply_to(message, response, parse_mode='Markdown')
        else:
            # ویژگی دیباگ هوشمند: اگر نتوانست پیدا کند، اطلاعات خام تلگرام را برایتان می‌فرستد!
            raw_data = json.dumps(msg_dict, indent=2, ensure_ascii=False)
            debug_msg = (
                "❌ **آیدی پیدا نشد!**\n\n"
                "احتمالاً تلگرام ساختار این پیام را عوض کرده.\n"
                "لطفاً متن زیر (کد خام پیام) را کپی کن و برای من (هوش مصنوعی) بفرست تا ببینم کانال‌ها کجا پنهان شده‌اند:\n\n"
                f"```json\n{raw_data[:3500]}\n```"
            )
            bot.reply_to(message, debug_msg, parse_mode='Markdown')

    except Exception as e:
        error_msg = f"⚠️ ربات با خطا مواجه شد.\n\n`{str(e)}`"
        bot.reply_to(message, error_msg, parse_mode='Markdown')
        print("Error details:\n", traceback.format_exc())

@app.route('/')
def index():
    return "✅ Bot is running successfully on Render!"

def run_bot():
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=60)
    except Exception as e:
        print("❌ خطای شدید:\n", traceback.format_exc())

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
