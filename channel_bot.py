import os
import re
import json
import urllib.request
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pydub import AudioSegment
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)

# ------------------- تنظیمات کلیدی -------------------
TELEGRAM_TOKEN = "8831739954:AAG8w-rh9KK1zbDZBQzqLHqlvONmZAQH-sM"
GEMINI_API_KEY = "AQ.Ab8RN6ICtQ7xI8bqxNcQPrY1Z06v6H698rpJdh00H1Z6_FbXmQ"

# آدرس لینک خام فایل channel_bot.py در گیت‌هاب شما
GITHUB_RAW_URL = "https://raw.githubusercontent.com/shahin11020x-blip/-ad808code_bot/main/channel_bot.py"
# -----------------------------------------------------

# وب‌سرور سبک برای راضی کردن رندر و باز نگه داشتن پورت
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def call_gemini_api(prompt: str) -> str:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            return res['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"خطا در Gemini API: {e}")
        return None

def time_to_ms(time_str: str) -> int:
    time_str = time_str.strip()
    parts = time_str.split(':')
    if len(parts) == 2:
        return (int(parts[0]) * 60 + int(parts[1])) * 1000
    elif len(parts) == 1:
        return int(parts[0]) * 1000
    return 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "سلام! 👋 به ربات هوشمند مدیریت کانال موزیک خوش آمدید.\n\n"
        "✨ **مراحل ساخت پست جدید:**\n"
        "۱. **عکس ثابت بیت** (کاور داخل فایل صوتی) را بفرستید.\n"
        "۲. فایل صوتی / بیت خود را بفرستید.\n"
        "۳. **عکس کاور پست چنل** را بفرستید.\n"
        "۴. **متن مشخصات** آهنگ را بفرستید!\n\n"
        "🔄 دستور آپدیت خودکار: `/update`"
    )

async def update_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ در حال بررسی و دریافت آخرین نسخه کد از گیت‌هاب...")
    try:
        req = urllib.request.Request(GITHUB_RAW_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            new_code = response.read().decode('utf-8')
            
        if "def process_and_send_post" not in new_code:
            await msg.edit_text("❌ خطا: فایل دانلود شده معتبر به نظر نمی‌‌رسد.")
            return

        with open("channel_bot.py", "w", encoding="utf-8") as f:
            f.write(new_code)
            
        await msg.edit_text("✅ ربات با موفقیت به‌روزرسانی شد! 🚀")
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        await msg.edit_text(f"❌ خطا در آپدیت خودکار: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    photo = update.message.photo[-1]

    if not user_data.get('default_track_cover_id'):
        user_data['default_track_cover_id'] = photo.file_id
        await update.message.reply_text("✅ عکس ثابت بیت دریافت شد!\n\nحالا **فایل صوتی / بیت** خود را ارسال کنید.")
        return

    if user_data.get('audio_file_id') and not user_data.get('post_cover_id'):
        user_data['post_cover_id'] = photo.file_id
        await update.message.reply_text(
            "✅ عکس کاور پست چنل دریافت شد!\n\n"
            "📝 حالا **مشخصات آهنگ** (نام، تمپو، گام، سبک و زمان برش مثل `0:30 - 1:00`) را به صورت متن بفرستید تا پست نهایی ساخته شود."
        )
        return
    
    await update.message.reply_text("ℹ️️ لطفا طبق مرحله پیش بروید.")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio = update.message.audio or update.message.voice or update.message.document
    if not audio:
        return
    
    user_data = context.user_data
    if not user_data.get('default_track_cover_id'):
        await update.message.reply_text("❌ لطفاً ابتدا عکس ثابت بیت را ارسال کنید.")
        return

    user_data['audio_file_id'] = audio.file_id
    await update.message.reply_text("✅ فایل صوتی دریافت شد!\n\nحالا **عکس کاور پست چنل** را ارسال کنید.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if not user_data.get('default_track_cover_id') or not user_data.get('audio_file_id') or not user_data.get('post_cover_id'):
        await update.message.reply_text("❌ لطفاً مراحل قبلی (عکس ثابت بیت، فایل صوتی، عکس کاور پست) را کامل ارسال کنید.")
        return

    user_text = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ در حال پردازش اطلاعات و ساخت کپشن با هوش مصنوعی...")

    time_match = re.findall(r'\b\d{1,2}:\d{2}\b', user_text)
    if len(time_match) >= 2:
        start_ms = time_to_ms(time_match[0])
        end_ms = time_to_ms(time_match[1])
    elif len(time_match) == 1:
        start_ms = time_to_ms(time_match[0])
        end_ms = start_ms + 30000
    else:
        start_ms = 0
        end_ms = 30000

    await process_and_send_post(update, context, status_msg, text_info=user_text, start_ms=start_ms, end_ms=end_ms)

async def process_and_send_post(update, context, status_msg, text_info=None, start_ms=0, end_ms=30000):
    user_data = context.user_data
    track_cover_path = "temp_track_cover.jpg"
    post_cover_path = "temp_post_cover.jpg"
    file_path = "temp_audio.mp3"
    cut_path = "cut_audio.mp3"

    try:
        # دانلود عکس ثابت بیت برای داخل فایل صوتی
        track_cover_file = await context.bot.get_file(user_data['default_track_cover_id'])
        await track_cover_file.download_to_drive(track_cover_path)

        # دانلود عکس کاور پست برای تلگرام
        post_cover_file = await context.bot.get_file(user_data['post_cover_id'])
        await post_cover_file.download_to_drive(post_cover_path)

        await status_msg.edit_text("✍️ در حال ساخت کپشن حرفه‌ای با هوش مصنوعی...")

        prompt = (
            "You are an expert music channel admin. Based on the user's provided info, generate a Telegram caption in this EXACT format:\n\n"
            "🧪 808CODE | #808_5\n"
            "— 30s Preview —\n"
            "♩ Title — [Track Title]\n"
            "♩ Specs — [BPM] BPM | Key: [Key]\n"
            "♩ Vibe — [Genre]\n"
            "♩ Style — [Tags]\n\n"
            "📥 Full File (MP3 / WAV / Stems): \n"
            "@ad_808code\n\n"
            f"User Provided Info:\n{text_info}"
        )

        caption = call_gemini_api(prompt)
        
        if not caption:
            caption = (
                "🧪 808CODE | #808_5\n"
                "— 30s Preview —\n"
                "♩ Title — Track\n"
                "♩ Specs — 140 BPM | Key: #Fm\n"
                "♩ Vibe — #HipHop\n"
                "♩ Style — #Trap\n\n"
                "📥 Full File (MP3 / WAV / Stems): \n"
                "@ad_808code"
            )

        await status_msg.edit_text("✂️ در حال برش فایل صوتی...")
        audio_file = await context.bot.get_file(user_data['audio_file_id'])
        await audio_file.download_to_drive(file_path)

        song = AudioSegment.from_file(file_path)
        cut_song = song[start_ms:min(end_ms, len(song))]
        cut_song.fade_out(1000).export(cut_path, format="mp3")

        if os.path.exists(post_cover_path) and os.path.exists(cut_path) and os.path.exists(track_cover_path):
            with open(post_cover_path, 'rb') as photo_file, open(cut_path, 'rb') as audio_file_obj, open(track_cover_path, 'rb') as thumb_file:
                # ارسال عکس کاور پست به عنوان پیام اصلی همراه با کپشن، و فایل صوتی با کاور ثابت بیت به عنوان تامبنیل
                sent_msg = await context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=photo_file,
                    caption=caption
                )
                await context.bot.send_audio(
                    chat_id=update.message.chat_id,
                    audio=audio_file_obj,
                    thumbnail=thumb_file
                )

        await status_msg.edit_text("🚀 **پست با موفقیت آماده و ارسال شد!**", parse_mode="Markdown")
        user_data.clear()

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در پردازش: {str(e)}")

    finally:
        for f in [file_path, cut_path, track_cover_path, post_cover_path]:
            if f and os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update", update_bot))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 ربات با قابلیت کاور ثابت و کاور پست فعال شد...")
    app.run_polling()
```gui:channel_bot.py:channel_bot.py
