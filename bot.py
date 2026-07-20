import telebot
import re
import os
from flask import Flask
import threading

# دریافت توکن از تنظیمات سرور
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ----------------- کدهای ربات -----------------
# توجه: کلمه 'giveaway' به لیست انواع پیام‌ها اضافه شد
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'giveaway'])
def extract_channel_ids(message):
    extracted_channels = set()

    # --- بخش جدید: تشخیص قرعه‌کشی‌های رسمی (Native Giveaways) تلگرام ---
    if message.giveaway and message.giveaway.chats:
        for chat in message.giveaway.chats:
            if chat.username:
                # اگر کانال عمومی باشد و آیدی داشته باشد
                extracted_channels.add('@' + chat.username.lower())
            else:
                # اگر کانال پرایوت (خصوصی) باشد، آیدی عمومی ندارد، پس اسم و آیدی عددی‌اش را می‌دهیم
                extracted_channels.add(f"🔒 کانال خصوصی: {chat.title} (ID: {chat.id})")


    # --- بخش قبلی ۱: استخراج از متن و کپشن ---
    text = message.text or message.caption or ""
    
    usernames = re.findall(r'@\w+', text)
    for u in usernames:
        extracted_channels.add(u.lower())

    links = re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text)
    for l in links:
        if len(l) < 32 and not l.startswith('+'):
            extracted_channels.add('@' + l.lower())


    # --- بخش قبلی ۲: استخراج از دکمه‌های شیشه‌ای ---
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


    # --- ارسال نتیجه به کاربر ---
    if extracted_channels:
        response = "✅ **آیدی‌های پیدا شده:**\n\n" + "\n".join(extracted_channels)
    else:
        response = "❌ هیچ آیدی یا لینک کانالی در این پیام پیدا نشد."

    bot.reply_to(message, response, parse_mode='Markdown')


# ----------------- کدهای سرور وب (برای Render) -----------------
@app.route('/')
def index():
    return "✅ Bot is running successfully on Render!"

def run_bot():
    # استفاده از non_stop برای جلوگیری از قطع شدن‌های ناگهانی
    bot.infinity_polling(non_stop=True, timeout=60)

if __name__ == "__main__":
    # اجرای ربات در پس‌زمینه
    threading.Thread(target=run_bot, daemon=True).start()
    
    # اجرای سرور وب برای Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
