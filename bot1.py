from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# دستور شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"سلام {update.effective_user.first_name}! من یه ربات ساده‌ام.")

# توکن رباتت رو اینجا بذار
TOKEN = "8146746925:AAGPfDWIN5BV0EXSth0gjAqCclsO65ot79M"

app = ApplicationBuilder().token(TOKEN).build()

# اضافه کردن دستور start
app.add_handler(CommandHandler("start", start))

print("ربات روشن شد...")
app.run_polling()