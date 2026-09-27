import os
import re
import json
import base64
import urllib.request
import sys
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
# (بعد از اینکه فایل channel_bot.py را در گیت‌هاب ساختید، روی دکمه Raw بزنید و لینک آن را اینجا جایگزین کنید تا دستور /update کار کند)
GITHUB_RAW_URL = "https://raw.githubusercontent.com/shahin11020x-blip/YOUR_REPO_NAME/main/channel_bot.py"
# -----------------------------------------------------

def call_gemini_api(prompt: str, image_path: str = None) -> str:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': GEMINI_API_KEY
    }
    parts = [{"text": prompt}]
    
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode('utf-8')
        mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        parts.append({"inlineData": {"mimeType": mime_type, "data": img_data}})
        
    payload = {"contents": [{"parts": parts}]}
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
        "۱. فایل صوتی / بیت خود را بفرستید.\n"
        "۲. **عکس کاور پست** را بفرستید.\n"
        "۳. **اسکرین‌شات بیت‌استارز** یا اطلاعات را بفرستید!\n\n"
        "🔄 دستور آپدیت خودکار: `/update`"
    )

async def update_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور آپدیت خودکار ربات از طریق گیت‌هاب"""
    msg = await update.message.reply_text("⏳ در حال بررسی و دریافت آخرین نسخه کد از گیت‌هاب...")
    try:
        req = urllib.request.Request(GITHUB_RAW_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            new_code = response.read().decode('utf-8')
            
        if "def process_and_send_post" not in new_code:
            await msg.edit_text("❌ خطا: فایل دانلود شده معتبر به نظر نمی‌رسد.")
            return

        with open("channel_bot.py", "w", encoding="utf-8") as f:
            f.write(new_code)
            
        await msg.edit_text("✅ ربات با موفقیت به‌روزرسانی شد! 🚀")
        
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        await msg.edit_text(f"❌ خطا در آپدیت خودکار: {str(e)}")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio = update.message.audio or update.message.voice or update.message.document
    if not audio:
        return
    
    context.user_data.clear()
    context.user_data['audio_file_id'] = audio.file_id
    await update.message.reply_text("✅ موزیک دریافت شد!\nلطفاً **عکس کاور پست** را ارسال کنید.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if not user_data.get('audio_file_id'):
        await update.message.reply_text("❌ لطفاً ابتدا فایل صوتی را بفرستید.")
        return

    if not user_data.get('post_cover_id'):
        photo = update.message.photo[-1]
        user_data['post_cover_id'] = photo.file_id
        await update.message.reply_text(
            "✅ عکس کاور پست دریافت شد!\n\n"
            "📸 حالا **اسکرین‌شات بیت‌استارز** را بفرستید (می‌توانید زمان برش مثلاً `0:30 - 1:00` را زیر عکس بنویسید)."
        )
        return

    status_msg = await update.message.reply_text("🔎 در حال خواندن اطلاعات از روی اسکرین‌شات...")
    
    screenshot = update.message.photo[-1]
    screenshot_file = await context.bot.get_file(screenshot.file_id)
    screenshot_path = "temp_screenshot.jpg"
    await screenshot_file.download_to_drive(screenshot_path)

    caption_text = update.message.caption or ""
    time_match = re.findall(r'\b\d{1,2}:\d{2}\b', caption_text)
    if len(time_match) >= 2:
        start_ms = time_to_ms(time_match[0])
        end_ms = time_to_ms(time_match[1])
    elif len(time_match) == 1:
        start_ms = time_to_ms(time_match[0])
        end_ms = start_ms + 30000
    else:
        start_ms = 0
        end_ms = 30000

    await process_and_send_post(update, context, status_msg, screenshot_path=screenshot_path, start_ms=start_ms, end_ms=end_ms)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if not user_data.get('audio_file_id') or not user_data.get('post_cover_id'):
        await update.message.reply_text("لطفاً ابتدا فایل صوتی و عکس کاور پست را ارسال کنید.")
        return

    user_text = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ در حال پردازش اطلاعات و آماده‌سازی پست...")

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

async def process_and_send_post(update, context, status_msg, screenshot_path=None, text_info=None, start_ms=0, end_ms=30000):
    user_data = context.user_data
    cover_path = "temp_post_cover.jpg"
    file_path = "temp_audio.mp3"
    cut_path = "cut_audio.mp3"

    try:
        cover_file = await context.bot.get_file(user_data['post_cover_id'])
        await cover_file.download_to_drive(cover_path)

        await status_msg.edit_text("✍️ در حال تحلیل و ساخت کپشن با هوش مصنوعی...")

        prompt = (
            "You are the admin of a music channel.\n"
            "Extract details (Title, BPM, Key, Genre, Tags) from the screenshot or text and output EXACTLY in this format:\n\n"
            "🧪 808CODE | #808_5\n"
            "— 30s Preview —\n"
            "♩ Title — [Title from image, e.g. Rolex]\n"
            "♩ Specs — [BPM number] BPM | Key: #[Key from image or #Fm if not found]\n"
            "♩ Vibe — #[Genre from image, e.g. #Hiphop]\n"
            "♩ Style — #[Tag1] #[Tag2] #[Tag3]\n\n"
            "​📥 Full File (MP3 / WAV / Stems): \n"
            "@ad_808code"
        )

        if text_info:
            prompt += f"\n\nاطلاعات متنی:\n{text_info}"

        caption = call_gemini_api(prompt, image_path=screenshot_path)
        
        if not caption:
            caption = (
                "🧪 808CODE | #808_5\n"
                "— 30s Preview —\n"
                "♩ Title — Unknown\n"
                "♩ Specs — 140 BPM | Key: #Fm\n"
                "♩ Vibe — #Hiphop\n"
                "♩ Style — #Trap\n\n"
                "​📥 Full File (MP3 / WAV / Stems): \n"
                "@ad_808code"
            )

        await status_msg.edit_text("✂️ در حال برش فایل صوتی...")
        audio_file = await context.bot.get_file(user_data['audio_file_id'])
        await audio_file.download_to_drive(file_path)

        song = AudioSegment.from_file(file_path)
        cut_song = song[start_ms:min(end_ms, len(song))]
        cut_song.fade_out(1000).export(cut_path, format="mp3")

        if os.path.exists(cover_path) and os.path.exists(cut_path):
            with open(cut_path, 'rb') as audio, open(cover_path, 'rb') as thumb:
                await context.bot.send_audio(
                    chat_id=update.message.chat_id,
                    audio=audio,
                    thumbnail=thumb,
                    caption=caption
                )

        await status_msg.edit_text("🚀 **پست با موفقیت آماده و ارسال شد!**", parse_mode="Markdown")
        user_data.clear()

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در پردازش: {str(e)}")

    finally:
        for f in [file_path, cut_path, cover_path, screenshot_path]:
            if f and os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update", update_bot))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 ربات با قابلیت آپدیت خودکار فعال شد...")
    app.run_polling()
