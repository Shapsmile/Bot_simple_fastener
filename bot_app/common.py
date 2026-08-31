"""Общие хелперы: обработка ошибок ввода, очистка ожидаемых пользователей, проверка доступа."""

import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import bot_simple_bd_func
from bot_app.config import pending_users


async def show_input_error(update, context, message_id_key, error_text, cancel_label, cancel_callback):
    """Удаляет сообщение пользователя и показывает ошибку в сообщении бота"""
    await update.message.delete()
    if message_id_key in context.user_data:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=context.user_data[message_id_key],
            text=error_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(cancel_label, callback_data=cancel_callback)
            ]])
        )


def cleanup_pending_users():
    """Очищает старые записи (старше 1 часа)"""
    current_time = time.time()
    expired = []

    for username, data in pending_users.items():
        if current_time - data['timestamp'] > 3600:  # 1 час
            expired.append(username)

    for username in expired:
        del pending_users[username]

    if expired:
        print(f"🧹 Очищены устаревшие ожидаемые пользователи: {expired}")


async def check_access(update, context):
    """
    Промежуточная функция для проверки доступа пользователя.
    Вызывается перед обработкой любого сообщения
    """
    user_id = update.effective_user.id

    # Проверяем авторизацию
    if not bot_simple_bd_func.is_user_authorized(user_id):
        # Если пользователь не авторизован - блокируем доступ
        if update.message:
            await update.message.reply_text(
                "🚫 Доступ запрещен!\n\n"
                "Вы не авторизованы для использования этого бота.\n"
                "Обратитесь к администратору для получения доступа."
            )
        elif update.callback_query:
            await update.callback_query.answer("🚫 Доступ запрещен!", show_alert=True)

        # Прерываем дальнейшую обработку
        return False

    return True
