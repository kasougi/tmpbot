import logging
import asyncio
import pytz
from datetime import datetime, time
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
from telethon.sync import TelegramClient


client = TelegramClient("session_name", API_ID, API_HASH)

# 🔹 Хранилище постов и бронирований
user_posts = {}
user_reservations = {}  # {user_id: (post_id, message_id)}
active_users = set()

# pending_payments = {}  # {user_id: message_id подтверждения оплаты}

START_MESSAGE = """
Дорогие клиенты, мы рады всех приветствовать в нашем чат-боте! 👀

Команда «Реклама в тгк» представляет инновацию в сфере оказания рекламных услуг! Теперь, с помощью нашего бота, вы сможете покупать совместную рекламу еще удобнее и безопаснее. Больше не будет сообщений от назойливых мошенников и вечного спама напоминаниями в канале 🤍🙏

В нашем чат-боте все предельно просто и понятно! 
Инструкция для покупки рекламы: 
1. Нажимаете «Посмотреть наборы»
2. Выбираете понравившийся набор и нажимаете «забронировать место»
3. Оплачиваете и отправляете боту одним сообщением чек и ссылку на канал 

Основные правила:
- мы не несем ответственность за приход 
- работаем только по полной предоплате 
- оплата возвращается только в случае отмены рекламы 
Задать любой вопрос: @manageraddv
"""

PAYMENTS_MESSAGE = """
Для бронирования необходимо перевести нужную сумму по реквизитам:
2202208318731503
Мария З. Сбербанк. 

После перевода обязательно пришлите скриншот и ссылку на канал одним сообщением!

Задать любой вопрос: @manageraddv
"""

CLOSE_MESSAGE = """
На настоящий момент это все доступные наборы, надеемся  вы найдете подходящий для себя🤍

Если вы хотите предложить конкретного блогера, то всегда можете обращаться  - @manageraddv
"""

NOTIFICATIONS = """
Добрый вечер!🤍
Количество актуальных наборов: {num}
Заглядывайте в бот! Уверены, вы найдете что-то для себя 🙏
"""

# 🔹 Функция отправки напоминаний
async def send_evening_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(pytz.timezone("Europe/Moscow")).time()
    target_time = time(18, 00)  # 18:00 по Москве

    if now.hour == target_time.hour and now.minute == target_time.minute:
        for user_id in active_users:
            if user_id != MANAGER_ID:
                num = await fetch_filtered_posts()
                if len(num):
                    try:
                        keyboard = [[InlineKeyboardButton("📦 Посмотреть наборы", callback_data="view_sets")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await context.bot.send_message(user_id, NOTIFICATIONS.format(num=len(num)), reply_markup=reply_markup)
                    except Exception as e:
                        logging.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")

# async def send_evening_reminders(context: ContextTypes.DEFAULT_TYPE):
#     num_posts = await fetch_filtered_posts()
#     if num_posts:
#         for user_id in context.bot_data.get("active_users", set()):
#             if user_id != MANAGER_ID:
#                 try:
#                     keyboard = [[InlineKeyboardButton("📦 Посмотреть наборы", callback_data="view_sets")]]
#                     reply_markup = InlineKeyboardMarkup(keyboard)
#                     await context.bot.send_message(user_id, NOTIFICATIONS.format(num=len(num_posts)), reply_markup=reply_markup)
#                 except Exception as e:
#                     logging.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")

# # Запуск напоминаний в 18:00 по Москве
# def setup_jobs(application: Application):
#     job_queue = application.job_queue
#     job_queue.run_daily(send_evening_reminders, time(hour=18, minute=49, tzinfo=pytz.timezone("Europe/Moscow")))

# 🔹 Функция планировщика напоминаний
async def schedule_reminders(application: Application):
    while True:
        await send_evening_reminders(application)  # Отправляем напоминания
        await asyncio.sleep(60)  # Проверяем раз в минуту

# 🔹 Функция старта
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != MANAGER_ID:
        active_users.add(user_id)  # Запоминаем пользователя
        keyboard = [[InlineKeyboardButton("📦 Посмотреть наборы", callback_data="view_sets")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            START_MESSAGE,
            reply_markup=reply_markup)
    
# 🔹 Получение отфильтрованных постов
async def fetch_filtered_posts():
    async with client:
        messages = await client.get_messages(CHANNEL_ID, limit=50)
        return [msg for msg in messages if msg.text and "#набор" in msg.text]


# 🔹 Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data == "view_sets":
        if user_id not in user_posts:
            user_posts[user_id] = await fetch_filtered_posts()

        if user_posts[user_id]:
            post = user_posts[user_id].pop(0)

            sent_message = await context.bot.forward_message(
                chat_id=user_id,
                from_chat_id=CHANNEL_ID,
                message_id=post.id
            )

            keyboard = [
                [InlineKeyboardButton("📦 Посмотреть другие наборы", callback_data="view_sets")],
                [InlineKeyboardButton("🛒 Забронировать место", callback_data=f"reserve_{sent_message.message_id}_{post.id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text="Выберите действие",
                reply_markup=reply_markup,
                reply_to_message_id=sent_message.message_id
            )
            
        else:
            keyboard = [[InlineKeyboardButton("📦 Проверить наличие новых наборов", callback_data="view_sets")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(CLOSE_MESSAGE, reply_markup=reply_markup)

    elif data.startswith("reserve_"):
        _, msg_id, post_id = data.split("_")
        user_reservations[user_id] = (int(post_id), int(msg_id))

        confirmation_message = await query.message.reply_text(
            PAYMENTS_MESSAGE
        )

        # pending_payments[user_id] = confirmation_message.message_id

    elif data.startswith("confirm_payment_"):
        await manager_confirm_payment(update, context, data)


# 🔹 Обработка оплаты (фото и текст)
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in user_reservations:
        post_id, msg_id = user_reservations[user_id]
        media_message = update.message

        # ✅ Пересылаем оригинальный пост менеджеру
        sent_post = await context.bot.forward_message(
            chat_id=MANAGER_ID,
            from_chat_id=CHANNEL_ID,
            message_id=post_id
        )

        # ✅ Пересылаем полное сообщение с оплатой
        forwarded_payment = await media_message.forward(MANAGER_ID)

        keyboard = [[InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"confirm_payment_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # ✅ Отправляем менеджеру сообщение с кнопкой подтверждения
        confirmation_message = await context.bot.send_message(
            chat_id=MANAGER_ID,
            text="🔔 Новый запрос на бронирование!",
            reply_markup=reply_markup,
            reply_to_message_id=forwarded_payment.message_id
        )

        new_confirmation = await update.message.reply_text("✅ Ваш платеж отправлен менеджеру на проверку!")

    else:
        await update.message.reply_text("Сначала нажмите забронируйте место.🤍")

# 🔹 Подтверждение оплаты менеджером
async def manager_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    user_id = int(data.split("_")[-1])

    if user_id in user_reservations:
        _, user_message_id = user_reservations[user_id]

        # ✅ Удаляем сообщение "✅ Ваш платеж отправлен менеджеру на проверку!"
        if user_message_id:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=user_message_id)
            except Exception as e:
                print(e)

        keyboard = [[InlineKeyboardButton("📦 Вернуться к наборам", callback_data="view_sets")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # ✅ Отправляем пользователю "✅ Бронирование прошло успешно!"
        await context.bot.send_message(user_id, "✅ Бронирование прошло успешно!", reply_markup=reply_markup)

        keyboard = [[InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"confirm_payment_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # ✅ Обновляем сообщение у менеджера
        await query.message.edit_text("✅ Ваша оплата принята, благодарим за сотрудничество!", reply_markup=reply_markup)

        # ✅ Удаляем запись о бронировании
        del user_reservations[user_id]

    else:
        await query.answer("Платеж уже обработан или не найден.", show_alert=True)

# 🔹 Обработчик произвольного текста
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, следуйте инструкциям")

# 🔹 Основная функция
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # ✅ Запускаем напоминания в фоне
    loop = asyncio.get_event_loop()
    loop.create_task(schedule_reminders(app))
    # setup_jobs(app)

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()