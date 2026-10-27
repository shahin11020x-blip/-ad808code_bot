import os
import re
import time
import urllib.request
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

TELEGRAM_TOKEN = "8831739954:AAG8w-rh9KK1zbDZBQzqLHqlvONmZAQH-sM"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/shahin11020x-blip/-ad808code_bot/main/channel_bot.py"
PURCHASE_LINK = "https://t.me/ad_808code"
TARGET_CHANNEL_ID = -1004302808319

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def time_to_ms(time_str: str) -> int:
    time_str = time_str.strip()
    parts = time_str.split(':')
    if len(parts) == 2:
        return (int(parts[0]) * 60 + int(parts[1])) * 1000
    elif len(parts) == 1:
        return int(parts[0]) * 1000
    return 0

def extract_track_info(text: str, fallback_title: str) -> str:
    """استخراج هوشمند عنوان و کد بیت از متن کپشن کاربر"""
    code_match = re.search(r'#808_\d+', text)
    beat_code = code_match.group(0) if code_match else ""

    title_match = re.search(r'Title:\s*([^\n\r]+)', text, re.IGNORECASE)
    if title_match:
        song_title = title_match.group(1).strip()
    else:
        song_title = fallback_title

    if song_title and beat_code:
        return f"{song_title} ({beat_code})"
    elif beat_code:
        return f"808CODE ({beat_code})"
    elif song_title:
        return song_title
    else:
        return "808CODE"

def extract_youtube_url(text: str) -> str:
    """استخراج لینک یوتیوب از متن ارسال شده"""
    yt_regex = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+)'
    match = re.search(yt_regex, text)
    if match:
        return match.group(0)
    return ""

def extract_soundcloud_url(text: str) -> str:
    """استخراج لینک ساندکلاد از متن ارسال شده"""
    sc_regex = r'(https?://(?:www\.)?(?:soundcloud\.com|on\.soundcloud\.com)/[^\s]+)'
    match = re.search(sc_regex, text)
    if match:
        return match.group(0)
    return ""

def clean_caption_text(text: str) -> str:
    """پاکسازی زمان‌های برش و لینک‌های یوتیوب و ساندکلاد از متن کپشن نهایی"""
    cleaned = re.sub(r'\b\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\b', '', text)
    cleaned = re.sub(r'\b\d{1,2}:\d{2}\b', '', cleaned)
    cleaned = re.sub(r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+)', '', cleaned)
    cleaned = re.sub(r'(https?://(?:www\.)?(?:soundcloud\.com|on\.soundcloud\.com)/[^\s]+)', '', cleaned)
    cleaned_lines = [line for line in cleaned.splitlines() if line.strip() != '']
    return '\n'.join(cleaned_lines).strip()

async def post_init(application):
    commands = [
        BotCommand("start", "شروع ساخت پست جدید و ریست ربات"),
        BotCommand("update", "به‌روزرسانی ربات از گیت‌هاب")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🔄 به‌روزرسانی ربات", callback_data="btn_update")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "سلام! 👋 به ربات مدیریت کانال موزیک خوش آمدید.\n\n"
        "✨ **مراحل ساخت پست جدید:**\n"
        "۱. **عکس کاور بیت** را بفرستید.\n"
        "۲. **فایل صوتی / بیت** خود را بفرستید.\n"
        "۳. **متن دلخواه خودتان** را بفرستید.\n\n"
        "⏱️ *نکته زمان‌بندی:* اگر زمانی قید کنید (مثلاً `0:10`) ۱۵ ثانیه از آن ثانیه برش داده می‌شود. اگر زمانی قید نشود، به صورت خودکار **۱۵ ثانیه اول (0:00 - 0:15)** برش داده می‌شود.\n\n"
        "👇 از دکمه زیر یا منوی دستورات هم می‌توانید استفاده کنید:",
        reply_markup=reply_markup
    )

async def update_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ در حال بررسی و دریافت آخرین نسخه کد از گیت‌هاب...")
    try:
        req = urllib.request.Request(GITHUB_RAW_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            new_code = response.read().decode('utf-8')
            
        if "def process_and_send_preview" not in new_code:
            await msg.edit_text("❌ خطا: فایل دانلود شده معتبر به نظر نمی‌رسد.")
            return

        with open("channel_bot.py", "w", encoding="utf-8") as f:
            f.write(new_code)
            
        await msg.edit_text("✅ ربات با موفقیت به‌روزرسانی شد! 🚀")
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        await msg.edit_text(f"❌ خطا در آپدیت خودکار: {str(e)}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_update":
        await update_bot(query, context)
    elif query.data == "send_to_channel":
        await send_preview_to_channel(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    photo = update.message.photo[-1]

    user_data['default_track_cover_id'] = photo.file_id
    await update.message.reply_text("✅ عکس کاور بیت دریافت شد!\n\nحالا **فایل صوتی / بیت** خود را ارسال کنید.")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    audio = update.message.audio or update.message.voice or update.message.document
    if not audio:
        return
    
    user_data = context.user_data
    if not user_data.get('default_track_cover_id'):
        await update.message.reply_text("❌ لطفاً ابتدا عکس کاور بیت را ارسال کنید.")
        return

    user_data['audio_file_id'] = audio.file_id
    
    file_name = getattr(audio, 'file_name', '') or ''
    fallback_title = os.path.splitext(file_name)[0] if file_name else ""
    user_data['fallback_title'] = fallback_title

    await update.message.reply_text(
        "✅ فایل صوتی دریافت شد!\n\n"
        "📝 حالا **متن دلخواه خودتان** را بفرستید.\n"
        "⏱️ اگر زمانی قید کنید (مثلاً `0:14`) ۱۵ ثانیه از آن ثانیه برش می‌خورد. اگر زمانی نفرستید به صورت خودکار ۱۵ ثانیه اول (`0:00 - 0:15`) برش داده می‌شود.\n"
        "🔗 *نکته:* می‌توانید لینک‌های YouTube و SoundCloud را هم در متن بگذارید تا روی دکمه‌های شیشه‌ای تنظیم شوند."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data

    if not user_data.get('default_track_cover_id') or not user_data.get('audio_file_id'):
        await update.message.reply_text("❌ لطفاً ابتدا عکس کاور بیت و فایل صوتی را ارسال کنید.")
        return

    raw_user_text = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ در حال پردازش صوت و برش ۱۵ ثانیه‌ای...")

    # بررسی وجود زمان برش در متن
    time_match = re.findall(r'\b\d{1,2}:\d{2}\b', raw_user_text)
    
    if len(time_match) >= 2:
        start_ms = time_to_ms(time_match[0])
        end_ms = time_to_ms(time_match[1])
    elif len(time_match) == 1:
        start_ms = time_to_ms(time_match[0])
        end_ms = start_ms + 15000  # ۱۵ ثانیه بعد از زمان داده شده
    else:
        start_ms = 0
        end_ms = 15000  # پیش‌فرض: ۰ تا ۱۵ ثانیه

    youtube_url = extract_youtube_url(raw_user_text)
    soundcloud_url = extract_soundcloud_url(raw_user_text)
    final_caption = clean_caption_text(raw_user_text)

    user_data['caption_text'] = final_caption
    user_data['raw_text_for_info'] = raw_user_text
    user_data['youtube_url'] = youtube_url
    user_data['soundcloud_url'] = soundcloud_url
    user_data['start_ms'] = start_ms
    user_data['end_ms'] = end_ms

    await process_and_send_preview(update, context, status_msg)

async def process_and_send_preview(update, context, status_msg):
    user_data = context.user_data
    timestamp = int(time.time())
    track_cover_path = f"cover_{timestamp}.jpg"
    file_path = f"raw_{timestamp}.mp3"
    cut_path = f"track_{timestamp}.mp3"

    try:
        # دانلود فایل‌ها
        track_cover_file = await context.bot.get_file(user_data['default_track_cover_id'])
        await track_cover_file.download_to_drive(track_cover_path)

        audio_file = await context.bot.get_file(user_data['audio_file_id'])
        await audio_file.download_to_drive(file_path)

        # استخراج اطلاعات
        fallback_title = user_data.get('fallback_title', '')
        raw_text_for_info = user_data.get('raw_text_for_info', '')
        custom_title = extract_track_info(raw_text_for_info, fallback_title)

        # پردازش صوت
        start_ms = user_data.get('start_ms', 0)
        end_ms = user_data.get('end_ms', 15000)
        
        song = AudioSegment.from_file(file_path)
        cut_song = song[start_ms:min(end_ms, len(song))]
        cut_song.fade_out(1000).export(cut_path, format="mp3")

        # تزریق کاور و متادیتا (ID3 Tags)
        try:
            try:
                audio_tags = ID3(cut_path)
                audio_tags.delete()
            except error:
                pass

            audio_tags = ID3()
            with open(track_cover_path, 'rb') as img:
                audio_tags.add(
                    APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc=u'Cover',
                        data=img.read()
                    )
                )
            audio_tags.add(TIT2(encoding=3, text=custom_title))
            audio_tags.add(TPE1(encoding=3, text="808CODE"))
            audio_tags.save(cut_path)
        except Exception as tag_err:
            print(f"Tag error: {tag_err}")

        # دکمه‌های شیشه‌ای جدید
        youtube_url = user_data.get('youtube_url', '')
        yt_link = youtube_url if youtube_url else "https://youtube.com"

        soundcloud_url = user_data.get('soundcloud_url', '')
        sc_link = soundcloud_url if soundcloud_url else "https://soundcloud.com"
        
        post_keyboard = [
            [InlineKeyboardButton("YouTube", url=yt_link)],
            [InlineKeyboardButton("SoundCloud", url=sc_link)],
            [InlineKeyboardButton("MP3 / WAV / Stems", url=PURCHASE_LINK)]
        ]
        post_markup = InlineKeyboardMarkup(post_keyboard)

        # ارسال پیش‌نمایش به خود کاربر در چت شخصی
        if os.path.exists(cut_path) and os.path.exists(track_cover_path):
            with open(cut_path, 'rb') as audio_file_obj, open(track_cover_path, 'rb') as thumb_file:
                sent_audio = await context.bot.send_audio(
                    chat_id=update.message.chat_id,
                    audio=audio_file_obj,
                    thumbnail=thumb_file,
                    caption=user_data.get('caption_text', ''),
                    title=custom_title,
                    performer="808CODE",
                    reply_markup=post_markup
                )
                
                # ذخیره شناسه فایل پردازش شده برای ارسال مجدد به کانال
                user_data['processed_audio_file_id'] = sent_audio.audio.file_id
                user_data['processed_custom_title'] = custom_title

        await status_msg.delete()

        # ارسال پیام همراه دکمه «ارسال به کانال»
        channel_keyboard = [
            [InlineKeyboardButton("📢 ارسال به کانال", callback_data="send_to_channel")]
        ]
        channel_markup = InlineKeyboardMarkup(channel_keyboard)

        await update.message.reply_text(
            "👆 **پیش‌نمایش پست شما آماده شد!**\n\n"
            "می‌توانید پست بالا را بررسی کنید. در صورت تأیید، روی دکمه زیر بزنید تا مستقیماً به کانال ارسال شود:",
            reply_markup=channel_markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در پردازش: {str(e)}")

    finally:
        # پاکسازی فایل‌های موقت
        for f in [file_path, cut_path, track_cover_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

async def send_preview_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_data = context.user_data

    if not user_data.get('processed_audio_file_id'):
        await query.message.edit_text("❌ متأسفانه اطلاعات پست پیدا نشد. لطفاً مراحل را دوباره طی کنید.")
        return

    try:
        await query.message.edit_text("⏳ در حال ارسال پست به کانال...")

        youtube_url = user_data.get('youtube_url', '')
        yt_link = youtube_url if youtube_url else "https://youtube.com"

        soundcloud_url = user_data.get('soundcloud_url', '')
        sc_link = soundcloud_url if soundcloud_url else "https://soundcloud.com"
        
        post_keyboard = [
            [InlineKeyboardButton("YouTube", url=yt_link)],
            [InlineKeyboardButton("SoundCloud", url=sc_link)],
            [InlineKeyboardButton("MP3 / WAV / Stems", url=PURCHASE_LINK)]
        ]
        post_markup = InlineKeyboardMarkup(post_keyboard)

        # ارسال به کانال هدف
        await context.bot.send_audio(
            chat_id=TARGET_CHANNEL_ID,
            audio=user_data['processed_audio_file_id'],
            caption=user_data.get('caption_text', ''),
            title=user_data.get('processed_custom_title', '808CODE'),
            performer="808CODE",
            reply_markup=post_markup
        )

        await query.message.edit_text("🚀 **پست با موفقیت در کانال منتشر شد!**", parse_mode="Markdown")
        user_data.clear()

    except Exception as e:
        await query.message.edit_text(f"❌ خطا در ارسال به کانال: {str(e)}")

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update", update_bot))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 ربات با موفقیت فعال شد...")
    app.run_polling()
