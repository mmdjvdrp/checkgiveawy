import telebot
import re
import os
from flask import Flask
import threading
import traceback

# دریافت توکن از تنظیمات سرور
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ----------------- کدهای ربات -----------------
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'giveaway'])
def extract_channel_ids(message):
    try:
        extracted_channels = set()

        # 1. استخراج از پیام‌های قرعه‌کشی (Native Giveaways)
        if message.content_type == 'giveaway' and message.giveaway and message.giveaway.chats:
            for chat in message.giveaway.chats:
                if chat.username:
                    extracted_channels.add('@' + chat.username.lower())
                else:
                    extracted_channels.add(f"🔒 کانال خصوصی: {chat.title} (ID: {chat.id})")

        # 2. استخراج از متن و کپشن
        text = message.text or message.caption or ""
        
        usernames = re.findall(r'@\w+', text)
        for u in usernames:
            extracted_channels.add(u.lower())

        links = re.findall(r'(?:t\.me|telegram\.me)/(\w+)', text)
        for l in links:
            if len(l) < 32 and not l.startswith('+'):
                extracted_channels.add('@' + l.lower())

        # 3. استخراج از دکمه‌های شیشه‌ای (باگ این بخش برطرف شد)
        if message.reply_markup and hasattr(message.reply_markup, 'keyboard'):
            for row in message.reply_markup.keyboard:
                for button in row:
                    # بررسی می‌کنیم که آیا دکمه لینک دارد یا خیر
                    if hasattr(button, 'url') and button.url:
                        if 't.me/' in button.url or 'telegram.me/' in button.url:
                            match = re.search(r'(?:t\.me|telegram\.me)/(\w+)', button.url)
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

    except Exception as e:
        # اگر هر خطایی در کد رخ دهد، ربات خاموش نمیشود و فقط ارور را میفرستد
        error_msg = f"⚠️ ربات نتوانست این پیام را پردازش کند.\n\n`{str(e)}`"
        bot.reply_to(message, error_msg, parse_mode='Markdown')
        print("Error details:\n", traceback.format_exc())


# ----------------- کدهای سرور وب (برای Render) -----------------
@app.route('/')
def index():
    return "✅ Bot is running successfully on Render!"

def run_bot():
    # روشن نگه داشتن ربات
    bot.infinity_polling(non_stop=True, timeout=60)

if __name__ == "__main__":
    # اجرای ربات در پس‌زمینه
    threading.Thread(target=run_bot, daemon=True).start()
    
    # اجرای سرور وب برای Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
