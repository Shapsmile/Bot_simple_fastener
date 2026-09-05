"""Главные экраны: выбор выработки, настройки, профиль, меню склада/проходки."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.common import check_access, fmt_qty
from bot_app.keyboards import advance_menu_keyboard, excavation_selection_keyboard, stock_menu_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Первый экран - выбор выработки.
    Показывает все доступные выработки из базы данных
    """
    # Проверяем доступ
    if not await check_access(update, context):
        return

    # Очищаем данные предыдущей сессии
    context.user_data.clear()

    reply_markup = InlineKeyboardMarkup(excavation_selection_keyboard())

    # Отправляем сообщение с кнопками выбора выработки
    await update.message.reply_text(
        "🏗️ Выберите забой, с которым хотите работать:",
        reply_markup=reply_markup
    )


async def start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запуск из кнопки (когда пользователь нажимает "Назад к выбору забоя")
    Показывает экран выбора выработки без команды /start
    """
    # Проверяем доступ
    if not await check_access(update, context):
        return

    reply_markup = InlineKeyboardMarkup(excavation_selection_keyboard())

    # Обновляем сообщение
    query = update.callback_query
    await query.edit_message_text(
        "🏗️ Выберите забой, с которым хотите работать:",
        reply_markup=reply_markup
    )


async def show_global_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Глобальные настройки системы (доступны из главного меню)
    """
    user_id = update.effective_user.id
    is_admin = bot_simple_bd_func.get_user_role(user_id) == 'admin'

    # Кнопки доступные всем пользователям
    keyboard = [[InlineKeyboardButton("👤 Мой профиль", callback_data="user_profile")]]

    # Кнопки только для администраторов
    if is_admin:
        keyboard.append([InlineKeyboardButton("👨‍💼 Управление пользователями", callback_data="user_management")])
        keyboard.append([InlineKeyboardButton("🏗️ Добавить забой", callback_data="excavation_add")])
        keyboard.append([InlineKeyboardButton("🗑️ Удалить забой", callback_data="excavation_remove")])
        keyboard.append([InlineKeyboardButton("📦 Создать новый материал", callback_data="material_add")])
        # Место для будущих настроек:
        # keyboard.append([InlineKeyboardButton("📊 Настройки отчетов", callback_data="report_settings")])
        # keyboard.append([InlineKeyboardButton("🔧 Системные настройки", callback_data="system_settings")])

    keyboard.append([InlineKeyboardButton("◀️ Назад к выбору забоя", callback_data="back_to_excavations")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(
        "⚙️ Настройки системы",
        reply_markup=reply_markup
    )


async def show_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает информацию о текущем пользователе
    """
    user_id = update.effective_user.id
    user_info = bot_simple_bd_func.get_user_info(user_id)

    if user_info:
        user_id, username, full_name, role, added_date = user_info
        role_icon = "👑" if role == 'admin' else "👤"

        text = (
            f"{role_icon} Ваш профиль\n\n"
            f"📛 ФИО: {full_name or 'Не указано'}\n"
        )
        if username:
            text += f"📱 Username: @{username}\n"
        text += f"🎯 Роль: {role}\n"
        text += f"🆔 ID: {user_id}\n"
        text += f"📅 В системе с: {added_date}"
    else:
        text = "❌ Информация о пользователе не найдена"

    keyboard = [[InlineKeyboardButton("◀️ Назад в настройки", callback_data="back_to_settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


async def show_excavation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, excavation_id: int):
    """
    Главное меню выработки с дополнительными опциями для админов
    """
    excavation_name = bot_simple_bd_func.get_excavation_name(excavation_id)
    user_id = update.effective_user.id
    is_admin = bot_simple_bd_func.get_user_role(user_id) == 'admin'

    context.user_data['current_excavation_id'] = excavation_id
    context.user_data['current_excavation_name'] = excavation_name

    # Базовые кнопки для всех пользователей
    keyboard = [[InlineKeyboardButton("📦 Материалы в забое", callback_data="menu_stock")],
                [InlineKeyboardButton("📏 Проведение выработки", callback_data="menu_advance")],
                [InlineKeyboardButton("📄 Паспорт крепления", callback_data="menu_passport")],
                [InlineKeyboardButton("◀️ Назад к выбору забоя", callback_data="back_to_excavations")]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ Выбран забой: {excavation_name}\nВыберите необходимое действие.",
        reply_markup=reply_markup
    )


async def show_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран меню склада.
    Показывает доступные операции со складом выбранной выработки
    """
    excavation_name = context.user_data['current_excavation_name']

    reply_markup = InlineKeyboardMarkup(stock_menu_keyboard())

    # Обновляем сообщение
    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n📦 Управление остатками материалов в забое",
        reply_markup=reply_markup
    )


async def show_advance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран меню проходки.
    Показывает доступные операции с проходкой выбранной выработки
    """
    excavation_name = context.user_data['current_excavation_name']

    reply_markup = InlineKeyboardMarkup(advance_menu_keyboard())

    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n📏 Управление проведением горной выработки",
        reply_markup=reply_markup
    )


async def show_stock_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран просмотра остатков на складе.
    Показывает текущие остатки материалов для выбранной выработки
    """
    # Получаем данные из контекста
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    # Получаем актуальные остатки из базы данных
    stock_data = bot_simple_bd_func.get_current_stock(excavation_id)

    # Формируем читабельный текст с остатками
    if not stock_data:
        text = f"🏗️ {excavation_name}\n📦 Нет материалов в паспорте крепления этой выработки."
    else:
        text = f"🏗️ {excavation_name}\n📊 Текущие остатки материалов в забое:\n\n"
        for item in stock_data:
            # Форматируем вывод: "Анкер АС-2: 150.5 шт."
            text += f"• {item['name']}: {fmt_qty(item['quantity'])} {item['unit']}\n"

        text += f"\n📋 Всего позиций: {len(stock_data)}"

    # Кнопка для возврата в меню склада
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню остатков", callback_data="back_to_stock_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение с данными об остатках
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)
