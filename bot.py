import telebot
import re
import os
from flask import Flask
import threading

# دریافت توکن از تنظیمات سرور (برای امنیت، توکن را مستقیم در کد نمی‌نویسیم)
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ----------------- کدهای ربات -----------------
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def extract_channel_ids(message):
    text = message.text or message.caption or ""
    extracted_channels = set()

    usernames = re.findall(r'@\w+', text)
    for u in usernames:
        extracted_channels.add(u.lower())

    links = re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text)
    for l in links:
        if len(l) < 32 and not l.startswith('+'):
            extracted_channels.add('@' + l.lower())

    if message.reply_markup and message.reply_markup.keyboard:
        keyboard = message.reply_markup.keyboard
        for row in keyboard:
            for button in row:
                if 'url' in button and ('t.me/' in button['url'] or 'telegram.me/' in button['url']):
                    match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', button['url'])
                    if match:
                        channel_id = match.group(1)
                        if len(channel_id) < 32 and not channel_id.startswith('+'):
                            extracted_channels.add('@' + channel_id.lower())

    if extracted_channels:
        response = "✅ **آیدی‌های پیدا شده:**\n\n" + "\n".join(extracted_channels)
    else:
        response = "❌ هیچ آیدی یا لینک کانالی در این پیام/دکمه‌ها پیدا نشد."

    bot.reply_to(message, response, parse_mode='Markdown')


# ----------------- کدهای سرور وب (برای Render) -----------------
@app.route('/')
def index():
    return "✅ Bot is running successfully on Render!"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # اجرای ربات در پس‌زمینه
    threading.Thread(target=run_bot).start()
    
    # اجرای سرور وب برای Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
