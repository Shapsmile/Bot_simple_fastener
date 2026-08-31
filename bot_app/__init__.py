"""Пакет бота: разбиение bot.py на модули по функциональным областям."""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot_app.config import TOKEN
from bot_app.router import handle_all_text_input, handle_button_click, handle_new_user_message
from bot_app.screens import start
from bot_app.users import user_management_command


def main():
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", user_management_command))

    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Обработчики текстовых сообщений - ВАЖНО: СНАЧАЛА проверка новых пользователей
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_new_user_message  # Этот должен быть ПЕРВЫМ
    ))

    # Дополнительный обработчик для авторизованных пользователей
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_all_text_input  # Этот должен быть ВТОРЫМ
    ))

    print("🤖 Бот запущен с системой контроля доступа!")
    application.run_polling()
