import os
import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
)
from docxtpl import DocxTemplate
import pypandoc

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
TEMPLATE_PATH = "zayava_template.docx"

FIELDS = [
    "Заява подається до",
    "Вид заяви",
    "Реквізити заявника/ліцензіата",
    "Вид ліцензії",
    "Спосіб отримання ліцензії",
    "Реєстраційний номер ліцензії",
    "Адреса місця провадження",
    "Перелік фіскальних номерів",
    "Відомості про розташування",
    "Інформація про внесення платежу",
    "Ознайомлений з вимогами законодавства",
    "Підтверджую достовірність",
    "Підписант"
]

FIELD_KEYS = [f"field{i+1}" for i in range(len(FIELDS))]
SKIP, DONE = "Пропустити", "Завершити"

def start(update: Update, context: CallbackContext):
    context.user_data["step"] = 0
    context.user_data["form"] = {}
    update.message.reply_text(
        "✍️ Бот для створення заяви на ліцензію. Натисніть /zayava щоб почати заповнення."
    )

def zayava(update: Update, context: CallbackContext):
    context.user_data["step"] = 0
    context.user_data["form"] = {}
    return ask_field(update, context)

def ask_field(update, context):
    i = context.user_data["step"]
    if i >= len(FIELDS):
        return finish(update, context)
    keyboard = [[SKIP, DONE]]
    update.message.reply_text(
        f"{FIELDS[i]}:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return 1

def handle_response(update, context):
    i = context.user_data["step"]
    text = update.message.text.strip()
    if text == DONE:
        return finish(update, context)
    if text != SKIP:
        context.user_data["form"][FIELD_KEYS[i]] = text
    else:
        context.user_data["form"][FIELD_KEYS[i]] = ""
    context.user_data["step"] += 1
    return ask_field(update, context)

def finish(update, context):
    data = context.user_data["form"]
    # Map fields to context for docxtpl (можна по ключах field1, field2... field13)
    doc = DocxTemplate(TEMPLATE_PATH)
    doc.render(data)
    docx_path = f"/tmp/zayava_{update.effective_user.id}.docx"
    pdf_path = f"/tmp/zayava_{update.effective_user.id}.pdf"
    doc.save(docx_path)

    try:
        # Convert docx to pdf
        pypandoc.convert_file(docx_path, 'pdf', outputfile=pdf_path)
        with open(pdf_path, "rb") as pdf:
            update.message.reply_document(pdf, filename="zayava.pdf")
    except Exception as e:
        # Якщо PDF не вдалось, шлемо docx
        with open(docx_path, "rb") as docx:
            update.message.reply_document(docx, filename="zayava.docx")
    update.message.reply_text("✅ Заява готова!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def cancel(update, context):
    update.message.reply_text("❌ Операцію скасовано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('zayava', zayava)],
        states={
            1: [MessageHandler(Filters.text & ~Filters.command, handle_response)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler('cancel', cancel))

    print("✅ Бот для заяви запущено")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
