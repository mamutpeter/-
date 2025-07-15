import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
)
from docx import Document
from docx2pdf import convert

FIELDS = [
    "Заява подається до:",                # 1
    "Вид заяви",                          # 2
    "Реквізити заявника/ліцензіата",      # 3
    "Вид ліцензії",                       # 4
    "Спосіб отримання ліцензії",          # 5
    "Реєстраційний номер ліцензії",       # 6
    "Адреса місця провадження діяльності",# 7
    "Перелік фіскальних номерів",         # 8
    "Відомості про місця роздрібної торгівлі", # 9
    "Інформація про внесення платежу",    # 10
    "Ознайомлений з вимогами законодавства", # 11
    "Підтверджую достовірність",          # 12
    "Підписант",                          # 13
]
TEMPLATE_FILE = "zayava_template.docx"    # Шлях до шаблону
STATE_ASK_FIELD = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['answers'] = {}
    context.user_data['field_idx'] = 0
    await ask_field(update, context)
    return STATE_ASK_FIELD

async def ask_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get('field_idx', 0)
    if idx >= len(FIELDS):
        await generate_and_send(update, context)
        return ConversationHandler.END

    field = FIELDS[idx]
    reply_markup = ReplyKeyboardMarkup(
        [["Ввести відповідь", "Залишити пустим"], ["Завершити та отримати заяву"]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(f"{idx+1}. {field}", reply_markup=reply_markup)
    return STATE_ASK_FIELD

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    idx = context.user_data['field_idx']
    if text == "Ввести відповідь":
        await update.message.reply_text("Введіть відповідь:", reply_markup=ReplyKeyboardRemove())
        return idx + 1000  # особливий стан, очікування відповіді
    elif text == "Залишити пустим":
        context.user_data['answers'][f'field{idx+1}'] = ""
        context.user_data['field_idx'] += 1
        return await ask_field(update, context)
    elif text == "Завершити та отримати заяву":
        return await generate_and_send(update, context)
    else:
        await update.message.reply_text("Обери дію через кнопки.")
        return STATE_ASK_FIELD

async def handle_field_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data['field_idx']
    context.user_data['answers'][f'field{idx+1}'] = update.message.text
    context.user_data['field_idx'] += 1
    return await ask_field(update, context)

async def generate_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Генеруємо docx на основі шаблону
    doc = Document(TEMPLATE_FILE)
    for para in doc.paragraphs:
        for key, val in context.user_data['answers'].items():
            para.text = para.text.replace(f"{{{{{key}}}}}", val or "")
    # Зберігаємо тимчасово
    user_id = update.effective_user.id
    docx_path = f"output_{user_id}.docx"
    pdf_path = f"output_{user_id}.pdf"
    doc.save(docx_path)
    # Конвертуємо в PDF (docx2pdf потрібен Windows/MS Office, якщо Linux – можу замінити на pypandoc)
    convert(docx_path, pdf_path)
    with open(pdf_path, "rb") as f:
        await update.message.reply_document(f, filename="Заява.pdf")
    os.remove(docx_path)
    os.remove(pdf_path)
    await update.message.reply_text("✅ Заява готова.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def build_conv_handler():
    states = {
        STATE_ASK_FIELD: [
            MessageHandler(filters.Regex("^(Ввести відповідь|Залишити пустим|Завершити та отримати заяву)$"), handle_response),
        ]
    }
    # Додаємо динамічні хендлери для кожного поля
    for i in range(len(FIELDS)):
        states[i + 1000] = [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_input)]
    return ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states=states,
        fallbacks=[],
        allow_reentry=True
    )

if __name__ == "__main__":
    from telegram.ext import Application
    # Стартуй з апі-токеном нового бота
    app = Application.builder().token("YOUR_NEW_BOT_TOKEN").build()
    app.add_handler(build_conv_handler())
    print("✅ Бот для заяв запущено!")
    app.run_polling()
