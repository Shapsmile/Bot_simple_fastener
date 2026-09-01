"""Управление пользователями (только для админов)."""

import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.common import check_access, clear_input_state
from bot_app.config import pending_users
from bot_app.screens import show_global_settings


async def show_user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Меню управления пользователями (только для админов)
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # Проверяем права администратора
    if bot_simple_bd_func.get_user_role(user_id) != 'admin':
        await query.answer("🚫 Недостаточно прав!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("👥 Список пользователей", callback_data="users_list")],
        [InlineKeyboardButton("➕ Добавить пользователя", callback_data="users_add")],
        [InlineKeyboardButton("🗑️ Удалить пользователя", callback_data="users_remove")],
        [InlineKeyboardButton("◀️ Назад в настройки", callback_data="back_to_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "👨‍💼 Управление пользователями",
        reply_markup=reply_markup
    )


async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает список всех авторизованных пользователей
    """
    users = bot_simple_bd_func.get_authorized_users()

    if not users:
        text = "📭 Нет авторизованных пользователей"
    else:
        text = "👥 Авторизованные пользователи:\n\n"

        for user_id, username, full_name, role, added_date in users:
            role_icon = "👑" if role == 'admin' else "👤"
            text += f"{role_icon} {full_name or username}\n"
            text += f"   📱 @{username}\n" if username else f"   🆔 ID: {user_id}\n"
            text += f"   🎯 Роль: {role}\n"
            text += f"   📅 Добавлен: {added_date}\n\n"

    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_user_management")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


async def ask_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает данные нового пользователя
    """
    clear_input_state(context)  # Сбрасываем любые предыдущие состояния ввода
    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="back_to_user_management")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    message = await query.edit_message_text(
        "➕ Добавление пользователя\n\n"
        "Отправьте сообщение в формате:\n"
        "`@username Фамилия Имя роль`\n\n"
        "Пример:\n"
        "`@ivanov Иван Петров operator`\n"
        "`@petrov Петр Сидоров admin`\n\n"
        "Роли: operator (оператор), admin (администратор)",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    context.user_data['user_add_message_id'] = message.message_id


async def process_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает добавление нового пользователя по username
    """
    try:
        text = update.message.text.strip()
        parts = text.split()

        print(f"🔍 Обрабатываем данные пользователя: '{text}'")

        if len(parts) < 3:
            raise ValueError("Недостаточно данных")

        # Парсим данные
        username = parts[0].replace('@', '').lower()  # Убираем @ и приводим к нижнему регистру
        full_name = ' '.join(parts[1:-1])
        role = parts[-1].lower()

        print(f"🔍 Распарсенные данные: username=@{username}, full_name={full_name}, role={role}")

        # Проверяем роль
        if role not in ['operator', 'admin']:
            raise ValueError("Неверная роль. Используйте: operator или admin")

        # Удаляем сообщение администратора
        await update.message.delete()

        # СОХРАНЯЕМ В ГЛОБАЛЬНОЕ ХРАНИЛИЩЕ
        pending_users[username] = {
            'username': username,
            'full_name': full_name,
            'role': role,
            'added_by': update.effective_user.id,
            'added_by_name': update.effective_user.full_name,
            'timestamp': time.time()  # Для очистки старых записей
        }

        print(f"✅ Данные сохранены в глобальное хранилище. Все ожидаемые: {list(pending_users.keys())}")

        success_text = (
            f"✅ Пользователь подготовлен к добавлению!\n\n"
            f"👤 Username: @{username}\n"
            f"📛 ФИО: {full_name}\n"
            f"🎯 Роль: {role}\n\n"
            f"Теперь попросите пользователя написать ЛЮБОЕ сообщение в этого бота.\n"
            f"Как только он это сделает - он будет автоматически добавлен в систему."
        )

        if 'user_add_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['user_add_message_id'],
                text=success_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад в управление пользователями",
                                         callback_data="back_to_user_management")
                ]])
            )

    except Exception as e:
        print(f"❌ Ошибка при обработке нового пользователя: {e}")
        await update.message.delete()

        error_text = f"❌ Ошибка формата: {str(e)}"

        if 'user_add_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['user_add_message_id'],
                text=error_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="back_to_user_management")
                ]])
            )

    finally:
        # Всегда очищаем ключ, чтобы он не перехватывал последующий ввод
        context.user_data.pop('user_add_message_id', None)


async def show_users_for_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает список пользователей для удаления с кнопками
    """
    users = bot_simple_bd_func.get_authorized_users()

    # Фильтруем - нельзя удалить себя
    current_user_id = update.effective_user.id
    users = [user for user in users if user[0] != current_user_id]

    if not users:
        text = "📭 Нет пользователей для удаления (кроме вас самих)"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_user_management")]]
    else:
        text = "🗑️ Выберите пользователя для удаления:\n\n"

        keyboard = []
        for user_id, username, full_name, role, added_date in users:
            role_icon = "👑" if role == 'admin' else "👤"
            button_text = f"{role_icon} {full_name or username} (@{username})" if username else f"{role_icon} {full_name} (ID: {user_id})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"remove_user_{user_id}")])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_user_management")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


async def show_remove_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """
    Показывает подтверждение удаления пользователя
    """
    # Получаем информацию о пользователе
    user_info = bot_simple_bd_func.get_user_info(user_id)
    if not user_info:
        await update.callback_query.answer("❌ Пользователь не найден!", show_alert=True)
        return

    user_id, username, full_name, role, added_date = user_info

    # Сохраняем данные пользователя в контексте
    context.user_data['user_to_remove'] = {
        'user_id': user_id,
        'username': username,
        'full_name': full_name,
        'role': role
    }

    text = (
        f"🗑️ Подтверждение удаления\n\n"
        f"👤 Пользователь: {full_name or 'Без имени'}\n"
        f"📱 Username: @{username}\n" if username else f"🆔 ID: {user_id}\n"
                                                      f"🎯 Роль: {role}\n"
                                                      f"📅 Добавлен: {added_date}\n\n"
                                                      f"⚠️ Вы уверены что хотите удалить этого пользователя?\n"
                                                      f"Он потеряет доступ к боту!"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_remove")],
        [InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_remove")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


async def process_user_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает удаление пользователя
    """
    user_to_remove = context.user_data.get('user_to_remove')

    if not user_to_remove:
        await update.callback_query.answer("❌ Ошибка: данные пользователя не найдены!", show_alert=True)
        return

    user_id = user_to_remove['user_id']
    username = user_to_remove['username']
    full_name = user_to_remove['full_name']

    # Удаляем пользователя из базы
    bot_simple_bd_func.remove_authorized_user(user_id)

    # Очищаем контекст
    context.user_data.pop('user_to_remove', None)

    # Показываем сообщение об успехе
    success_text = (
        f"✅ Пользователь успешно удален!\n\n"
        f"👤 {full_name or 'Пользователь'}\n"
        f"📱 @{username}\n" if username else f"🆔 ID: {user_id}\n"
                                            f"🗑️ Доступ к боту отозван"
    )

    keyboard = [[InlineKeyboardButton("◀️ В управление пользователями", callback_data="back_to_user_management")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(success_text, reply_markup=reply_markup)

    # Логируем действие
    admin_id = update.effective_user.id
    admin_name = update.effective_user.full_name
    print(f"👮 Администратор {admin_name} (ID: {admin_id}) удалил пользователя {full_name} (ID: {user_id})")


async def user_management_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для управления пользователями
    """
    # Проверяем доступ
    if not await check_access(update, context):
        return

    await show_global_settings(update, context)
