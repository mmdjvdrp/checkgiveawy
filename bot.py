import telebot
import re
import os
from flask import Flask
import threading
import traceback
import time

# دریافت توکن
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ ارور: توکن ربات (BOT_TOKEN) در تنظیمات رندر پیدا نشد!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'giveaway'])
def extract_channel_ids(message):
    try:
        extracted_channels = set()

        # بررسی پیام‌های Giveaway رسمی تلگرام
        if message.content_type == 'giveaway' and message.giveaway and message.giveaway.chats:
            for chat in message.giveaway.chats:
                if chat.username:
                    extracted_channels.add('@' + chat.username.lower())
                else:
                    extracted_channels.add(f"🔒 کانال خصوصی: {chat.title} (ID: {chat.id})")

        text = message.text or message.caption or ""
        
        # استخراج از متن
        usernames = re.findall(r'@\w+', text)
        for u in usernames:
            extracted_channels.add(u.lower())

        links = re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text)
        for l in links:
            if len(l) < 32 and not l.startswith('+'):
                extracted_channels.add('@' + l.lower())

        # استخراج از دکمه‌های شیشه‌ای
        if message.reply_markup and hasattr(message.reply_markup, 'keyboard'):
            for row in message.reply_markup.keyboard:
                for button in row:
                    if hasattr(button, 'url') and button.url:
                        if 't.me/' in button.url or 'telegram.me/' in button.url:
                            match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', button.url)
                            if match:
                                channel_id = match.group(1)
                                if len(channel_id) < 32 and not channel_id.startswith('+'):
                                    extracted_channels.add('@' + channel_id.lower())

        # ارسال جواب
        if extracted_channels:
            response = "✅ **آیدی‌های پیدا شده:**\n\n" + "\n".join(extracted_channels)
        else:
            response = "❌ هیچ آیدی یا لینک کانالی در این پیام پیدا نشد."

        bot.reply_to(message, response, parse_mode='Markdown')

    except Exception as e:
        error_msg = f"⚠️ ربات نتوانست این پیام را پردازش کند.\n\n`{str(e)}`"
        bot.reply_to(message, error_msg, parse_mode='Markdown')
        print("Error details:\n", traceback.format_exc())

@app.route('/')
def index():
    return "✅ Bot is running successfully on Render!"

def run_bot():
    print("⏳ در حال پاک کردن تنظیمات قبلی تلگرام...")
    try:
        bot.remove_webhook()
        time.sleep(1)
        print("✅ تنظیمات پاک شد. ربات در حال روشن شدن است...")
        # مشکل ارور در اینجا برطرف شد
        bot.infinity_polling(timeout=60)
    except Exception as e:
        print("❌ خطای شدید در روشن شدن ربات:\n", traceback.format_exc())

if __name__ == "__main__":
    print("🚀 در حال استارت کردن سرور...")
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
