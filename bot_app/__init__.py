"""Пакет бота: разбиение bot.py на модули по функциональным областям."""

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import bot_simple_bd_func
from bot_app.config import TOKEN
from bot_app.router import handle_button_click, handle_text_message
from bot_app.screens import start
from bot_app.users import user_management_command


async def error_handler(update, context):
    """Логирует ошибки, чтобы они не терялись молча"""
    logging.error(
        "Ошибка при обработке %s: %s",
        update, context.error,
        exc_info=context.error
    )


def main():
    # Инициализируем базу данных (на Railway файла нет - создаём схему при старте)
    bot_simple_bd_func.init_database()
    bot_simple_bd_func.user_system_database()

    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", user_management_command))

    # Обработчики кнопок
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # ЕДИНСТВЕННЫЙ обработчик текста: сам перенаправляет авторизованных пользователей
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))

    # Логируем ошибки вместо молчаливого падения
    application.add_error_handler(error_handler)

    print("🤖 Бот запущен с системой контроля доступа!")
    application.run_polling()
