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

# Поля, які треба залишити (без зайвих)
FIELDS = [
    "Реєстраційний номер ліцензії",       # field1
    "Адреса місця провадження",           # field2
    # --- Таблична частина пункту 8 ---
    "Перелік фіскальних номерів реєстраторів розрахункових операцій, програмних реєстраторів розрахункових операцій (рядок 1)",  # rro1
    "Дата початку використання (рядок 1)",                # rro2
    "Дата закінчення використання (рядок 1)",             # rro3
    "Перелік фіскальних номерів книг обліку (рядок 1)",   # rro4
    "Перелік фіскальних номерів розрахункових книжок (рядок 1)", # rro5
    # ... і ще два ряди (2 і 3), якщо потрібно
    "Перелік фіскальних номерів реєстраторів розрахункових операцій, програмних реєстраторів розрахункових операцій (рядок 2)",
    "Дата початку використання (рядок 2)",
    "Дата закінчення використання (рядок 2)",
    "Перелік фіскальних номерів книг обліку (рядок 2)",
    "Перелік фіскальних номерів розрахункових книжок (рядок 2)",
    "Перелік фіскальних номерів реєстраторів розрахункових операцій, програмних реєстраторів розрахункових операцій (рядок 3)",
    "Дата початку використання (рядок 3)",
    "Дата закінчення використання (рядок 3)",
    "Перелік фіскальних номерів книг обліку (рядок 3)",
    "Перелік фіскальних номерів розрахункових книжок (рядок 3)",
    # --- Пункт 9 ---
    "Відомості про розташування (п.9)",
    # --- Таблична частина пункту 10 ---
    "Код класифікації доходів бюджету (рядок 1)",        # pay1_1
    "Сума внесеного платежу (рядок 1)",                  # pay1_2
    "Номер платіжної інструкції (рядок 1)",              # pay1_3
    "Дата платіжної інструкції (рядок 1)",               # pay1_4
    "Код класифікації доходів бюджету (рядок 2)",        # pay2_1
    "Сума внесеного платежу (рядок 2)",                  # pay2_2
    "Номер платіжної інструкції (рядок 2)",              # pay2_3
    "Дата платіжної інструкції (рядок 2)",               # pay2_4
    "Код класифікації доходів бюджету (рядок 3)",        # pay3_1
    "Сума внесеного платежу (рядок 3)",                  # pay3_2
    "Номер платіжної інструкції (рядок 3)",              # pay3_3
    "Дата платіжної інструкції (рядок 3)"                # pay3_4
]

FIELD_KEYS = [
    "reg_number", "address",
    "rro1_1", "rro1_2", "rro1_3", "rro1_4", "rro1_5",
    "rro2_1", "rro2_2", "rro2_3", "rro2_4", "rro2_5",
    "rro3_1", "rro3_2", "rro3_3", "rro3_4", "rro3_5",
    "placement_info",
    "pay1_1", "pay1_2", "pay1_3", "pay1_4",
    "pay2_1", "pay2_2", "pay2_3", "pay2_4",
    "pay3_1", "pay3_2", "pay3_3", "pay3_4"
]
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
    # Відображення відповідей у docxtpl через ключі FIELD_KEYS
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
