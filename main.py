from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from database import *
import datetime
import re
import asyncio

TOKEN = "7891910607:AAE4pWVgIQv4So0gmvEiUX2WEUmQFx1VQYA"

create_tables()



async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ошибка: Эта команда не поддерживается. Используйте /help, чтобы посмотреть список доступных команд.")

async def random_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ошибка: Я не понимаю это сообщение. Используйте /help, чтобы узнать список доступных команд."
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я помогу вам управлять финансами. Используйте /help для списка команд.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
/add сумма категория "комментарий" [дата формата: год-месяц-день]- Добавить транзакцию (в случае, если дата не указана, транзакция будет записана на текущую дату)
/stats [дата формата: год-месяц-день]- Показать статистику на конкретный день (в случае, если дата не указана, будет показана статистика на текущую дату)
/help - Показать список команд
/monthstats (год месяц) - покажет все траты за указанный месяц
/setlimit сумма [год месяц] - установить лимит на месяц ( нельзя установить лимит на уже прошедший месяц)
/reminder число время(00:00) сообщение напоминания - Установить ежемесячное напоминание
    """)


async def add_transaction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Используйте: /add <сумма> <категория> <описание> [дата]")
            return

        # Если дата указана, берем последний аргумент как дату
        if len(args) > 3:
            amount = float(args[0])
            category = args[1]
            description = " ".join(args[2:-1])
            date = args[-1]
        else:
            # Если дата не указана, берем текущую дату
            amount = float(args[0])
            category = args[1]
            description = " ".join(args[2:])
            date = datetime.datetime.now().strftime("%Y-%m-%d")

        amount = abs(amount)
        # Валидация формата даты
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text("Неправильный формат даты. Используйте YYYY-MM-DD.")
            return

        # Добавление транзакции
        add_transaction(user_id, amount, category, description, date)

        # Проверка лимита
        year, month = int(date.split("-")[0]), int(date.split("-")[1])
        limit = get_monthly_limit(user_id, year, month)
        if limit is not None:
            # Получаем сумму расходов за месяц
            _, total_spent = get_monthly_summary(user_id, year, month)
            if total_spent > limit:
                exceeded = total_spent - limit  # Превышение лимита
                await update.message.reply_text(
                    f"Транзакция на {date} добавлена! Вы превысили лимит на месяц на {exceeded:.2f} руб!!!"
                )
            else:
                remaining = limit - total_spent  # Остаток до лимита
                await update.message.reply_text(
                    f"Транзакция на {date} добавлена! Остаток до лимита: {remaining:.2f} руб."
                )
        else:
            await update.message.reply_text(f"Транзакция на {date} добавлена! Лимит на этот месяц не установлен.")
    except ValueError:
        await update.message.reply_text("Неправильный формат. Используйте: /add <сумма> <категория> <описание> [дата]")


async def set_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if len(args) < 1:
        await update.message.reply_text("Используйте: /setlimit <сумма> [год] [месяц]")
        return

    # Парсим лимит, год и месяц
    limit = float(args[0])
    now = datetime.datetime.now()
    year = int(args[1]) if len(args) > 1 else now.year
    month = int(args[2]) if len(args) > 2 else now.month

    current_year = now.year
    current_month = now.month
    if year < current_year or (year == current_year and month < current_month):
        await update.message.reply_text(f"Невозможно установить лимит на прошедший месяц ({year}-{month:02d}).")
        return

    # Устанавливаем лимит
    set_monthly_limit(user_id, year, month, limit)
    await update.message.reply_text(f"Лимит на {year}-{month:02d} установлен: {limit:.2f} руб.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    # Если дата не указана, берем текущую дату
    date = args[0] if args else datetime.datetime.now().strftime("%Y-%m-%d")
    summary = get_summary(user_id, date)
    if not summary:
        await update.message.reply_text(f"Нет данных для {date}.")
        return
    message = f"Статистика расходов за {date}:\n"
    for category, total in summary:
        message += f"{category}: {total} руб\n"
    await update.message.reply_text(message)


async def month_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    # Если год и месяц не указаны, используем текущие
    now = datetime.datetime.now()
    year = int(args[0]) if len(args) > 0 else now.year
    month = int(args[1]) if len(args) > 1 else now.month

    # Получаем данные за месяц
    category_summary, total_amount = get_monthly_summary(user_id, year, month)

    # Получаем лимит на месяц
    limit = get_monthly_limit(user_id, year, month)

    if not category_summary and limit is None:
        await update.message.reply_text(f"Нет данных за {year}-{month:02d}. Лимит на этот месяц не установлен.")
        return

    # Формируем сообщение
    message = f"Статистика расходов за {year}-{month:02d}:\n"
    for category, total in category_summary:
        message += f"{category}: {total:.2f} руб\n"
    message += f"\nОбщая сумма трат за месяц: {total_amount:.2f} руб"

    # Добавляем информацию о лимите
    if limit is not None:
        message += f"\nУстановленный лимит: {limit:.2f} руб"
        if total_amount > limit:
            exceeded = total_amount - limit
            message += f"\nЛимит превышен на: {exceeded:.2f} руб"
        else:
            remaining = limit - total_amount
            message += f"\nОстаток до лимита: {remaining:.2f} руб"
    else:
        message += "\nЛимит на этот месяц не установлен."

    # Формируем кнопки с категориями
    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"category_{category}_{year}_{month}")]
        for category, _ in category_summary
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, reply_markup=reply_markup)


async def category_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем запрос кнопки

    # Извлекаем данные из callback_data
    _, category, year, month = query.data.split("_")
    year, month = int(year), int(month)
    user_id = query.from_user.id

    # Получаем траты внутри выбранной категории
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT amount, description, date FROM transactions
        WHERE user_id = ? AND category = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
    ''', (user_id, category, str(year), f"{month:02d}"))
    transactions = cursor.fetchall()
    conn.close()

    # Формируем сообщение
    if not transactions:
        message = f"Нет данных по категории '{category}' за {year}-{month:02d}."
    else:
        message = f"Траты по категории '{category}' за {year}-{month:02d}:\n"
        for amount, description, date in transactions:
            message += f"- {date}: {amount:.2f} руб ({description})\n"

    # Отправляем сообщение
    await query.message.reply_text(message)


async def set_monthly_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    args = context.args

    # Проверка количества аргументов
    if len(args) < 3:
        await update.message.reply_text("Ошибка: Используйте /reminder <день> <время в формате HH:MM> <сообщение>")
        return

    try:
        # Проверяем день
        day = int(args[0])
        if day < 1 or day > 31:
            await update.message.reply_text("Ошибка: День должен быть от 1 до 31.")
            return

        # Проверяем время
        time = args[1]
        if not re.match(r"^\d{2}:\d{2}$", time):
            await update.message.reply_text("Ошибка: Время должно быть в формате HH:MM.")
            return

        # Сообщение
        message = " ".join(args[2:])
        if not message.strip():
            await update.message.reply_text("Ошибка: Сообщение не может быть пустым.")
            return

        # Сохраняем напоминание
        add_monthly_reminder(user_id, chat_id, day, time, message)
        await update.message.reply_text(f"Ежемесячное напоминание установлено на {day}-е число в {time}. Сообщение: \"{message}\".")
    except ValueError:
        await update.message.reply_text("Ошибка: Проверьте правильность введенных данных.")


async def send_monthly_reminders(application):
    while True:
        now = datetime.datetime.now()
        current_day = now.day
        current_time = now.strftime("%H:%M")

        reminders = get_all_monthly_reminders()
        for user_id, chat_id, day, time, message in reminders:
            if day == current_day and time == current_time:
                await application.bot.send_message(chat_id=chat_id, text=f"Напоминание: {message}")
        await asyncio.sleep(60)  # Проверяем каждую минуту


def main():
    application = Application.builder().token(TOKEN).build()

    create_monthly_reminders_table()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_transaction_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("monthstats", month_stats_command))
    application.add_handler(CommandHandler("setlimit", set_limit_command))
    application.add_handler(CommandHandler("reminder", set_monthly_reminder_command))
    application.add_handler(CallbackQueryHandler(category_details_callback))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, random_text_handler))

    application.job_queue.run_repeating(
        lambda context: asyncio.create_task(send_monthly_reminders(application)),
        interval=60,
        first=0
    )

    application.run_polling()



if __name__ == "__main__":
    main()