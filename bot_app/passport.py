"""Хендлеры паспорта крепления: просмотр, редактирование норм расхода."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.common import clear_input_state, show_input_error
from bot_app.config import ADMIN_PASSWORD
from bot_app.keyboards import passport_edit_keyboard


async def show_passport_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Меню управления паспортом крепления
    """
    excavation_name = context.user_data['current_excavation_name']

    keyboard = [
        [InlineKeyboardButton("📋 Просмотр паспорта", callback_data="passport_view")],
        [InlineKeyboardButton("✏️ Редактирование паспорта", callback_data="passport_edit")],
        [InlineKeyboardButton("➕ Добавить материал в паспорт", callback_data="passport_add_material")],
        [InlineKeyboardButton("◀️ В главное меню", callback_data="back_to_excavation_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📄 Управление паспортом крепления",
        reply_markup=reply_markup
    )


async def show_passport_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Просмотр паспорта крепления выработки
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    # Получаем данные паспорта
    passport_data = bot_simple_bd_func.get_excavation_passport(excavation_id)

    if not passport_data:
        text = (
            f"🏗️ {excavation_name}\n"
            f"📄 Паспорт крепления\n\n"
            f"❌ Паспорт не настроен\n"
            f"Используйте редактирование для настройки"
        )
    else:
        text = (
            f"🏗️ {excavation_name}\n"
            f"📄 Паспорт крепления\n\n"
            f"📏 Нормы расхода на 1 метр проведения выработки:\n\n"
        )

        for item in passport_data:
            text += f"• {item['name']}: {item['consumption_per_meter']} {item['unit']}\n"

        text += f"\n📋 Всего материалов: {len(passport_data)}"

    # Кнопка возврата
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню паспорта", callback_data="back_to_passport_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


async def ask_password_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает пароль для редактирования паспорта
    """
    clear_input_state(context)  # Сбрасываем любые предыдущие состояния ввода
    excavation_name = context.user_data['current_excavation_name']

    # Создаем клавиатуру с кнопкой отмены
    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="back_to_passport_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"✏️ Редактировать паспорт крепления\n\n"
        f"🔒 Требуется пароль для доступа:\n\n"
        f"Введите пароль администратора:",
        reply_markup=reply_markup
    )

    # Сохраняем ID сообщения для последующего редактирования
    context.user_data['password_message_id'] = message.message_id


async def process_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод пароля для редактирования паспорта
    """
    password_attempt = update.message.text.strip()

    # Удаляем сообщение пользователя
    await update.message.delete()

    if password_attempt == ADMIN_PASSWORD:
        # Пароль верный - переходим к редактированию
        if 'password_message_id' in context.user_data:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['password_message_id']
            )

        context.user_data.pop('password_message_id', None)

        # ДОБАВЛЯЕМ: устанавливаем флаг, что пользователь авторизован для редактирования
        context.user_data['passport_edit_authorized'] = True

        await show_passport_edit(update, context)

    else:
        # Пароль неверный
        error_text = (
            f"❌ Неверный пароль!\n\n"
            f"Введите пароль снова:"
        )

        if 'password_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['password_message_id'],
                text=error_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="back_to_passport_menu")
                ]])
            )


async def show_passport_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int = None):
    """
    Экран редактирования паспорта крепления.
    Показывает материалы с текущими нормами расхода.
    Если передан message_id - редактирует существующее сообщение (одно окно),
    иначе отправляет новое.
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    # Получаем данные паспорта
    passport_data = bot_simple_bd_func.get_excavation_passport(excavation_id)

    if not passport_data:
        text = (
            f"🏗️ {excavation_name}\n"
            f"✏️ Редактирование паспорта\n\n"
            f"❌ В паспорте нет материалов\n"
            f"Обратитесь к администратору"
        )

        keyboard = [[InlineKeyboardButton("◀️ Назад в меню паспорта", callback_data="back_to_passport_menu")]]
    else:
        text = (
            f"🏗️ {excavation_name}\n"
            f"✏️ Редактирование паспорта\n\n"
            f"📏 Выберите материал для изменения нормы расхода:\n\n"
        )

        keyboard = passport_edit_keyboard(passport_data)

    reply_markup = InlineKeyboardMarkup(keyboard)

    if message_id is not None:
        # Редактируем существующее сообщение, сохраняя "одно окно"
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    else:
        # Отправляем новое сообщение
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup
        )


async def ask_new_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    """
    Запрашивает новую норму расхода для материала
    """
    clear_input_state(context)  # Сбрасываем любые предыдущие состояния ввода
    # Получаем информацию о материале
    material_name, unit = bot_simple_bd_func.get_material_info(material_id)

    # Получаем текущую норму расхода
    excavation_id = context.user_data['current_excavation_id']
    current_consumption = bot_simple_bd_func.get_consumption_rate(excavation_id, material_id)

    # Сохраняем данные в контексте
    context.user_data['editing_material_id'] = material_id
    context.user_data['editing_material_name'] = material_name
    context.user_data['editing_material_unit'] = unit
    context.user_data['current_consumption'] = current_consumption

    excavation_name = context.user_data['current_excavation_name']

    # Создаем клавиатуру с кнопкой отмены
    keyboard = [[InlineKeyboardButton("❌ Отменить редактирование", callback_data="cancel_edit_consumption")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Запрашиваем новую норму расхода
    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"✏️ Изменение нормы расхода\n\n"
        f"📦 Материал: {material_name}\n"
        f"📏 Текущая норма: {current_consumption} {unit}/м\n\n"
        f"Введите новую норму расхода на 1 метр:\n"
        f"Пример: 10.5 или 8",
        reply_markup=reply_markup
    )

    # Сохраняем ID сообщения для последующего редактирования
    context.user_data['consumption_edit_message_id'] = message.message_id


async def process_new_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод новой нормы расхода и обновляет паспорт
    """
    try:
        new_consumption = float(update.message.text)

        if new_consumption < 0:
            await show_input_error(
                update, context, 'consumption_edit_message_id',
                "❌ Норма расхода не может быть отрицательной. Введите снова:",
                "❌ Отменить редактирование", "cancel_edit_consumption"
            )
            return

        # Получаем данные из контекста
        excavation_id = context.user_data['current_excavation_id']
        excavation_name = context.user_data['current_excavation_name']
        material_id = context.user_data['editing_material_id']
        material_name = context.user_data['editing_material_name']
        material_unit = context.user_data['editing_material_unit']
        current_consumption = context.user_data['current_consumption']

        # Обновляем норму расхода в базе данных
        bot_simple_bd_func.update_passport_consumption(excavation_id, material_id, new_consumption)

        # Формируем сообщение об успехе
        success_text = (
            f"✅ Норма расхода успешно изменена!\n\n"
            f"🏗️ {excavation_name}\n"
            f"📦 {material_name}\n"
            f"📏 Было: {current_consumption} {material_unit}/м\n"
            f"📏 Стало: {new_consumption} {material_unit}/м\n\n"
            f"✅ Изменения сохранены в паспорте"
        )

        # Удаляем сообщение пользователя
        await update.message.delete()

        # Удаляем сообщение с запросом новой нормы
        if 'consumption_edit_message_id' in context.user_data:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['consumption_edit_message_id']
            )

        # Очищаем временные данные (ДОБАВЛЯЕМ ОЧИСТКУ АВТОРИЗАЦИИ)
        context.user_data.pop('editing_material_id', None)
        context.user_data.pop('editing_material_name', None)
        context.user_data.pop('editing_material_unit', None)
        context.user_data.pop('current_consumption', None)
        context.user_data.pop('consumption_edit_message_id', None)
        context.user_data.pop('passport_edit_authorized', None)  # Очищаем флаг авторизации

        # Возвращаемся в меню редактирования паспорта
        await show_passport_edit_with_success(update, context, success_text)

    except ValueError:
        await show_input_error(
            update, context, 'consumption_edit_message_id',
            "❌ Пожалуйста, введите число. Например: 10.5 или 8\nВведите новую норму расхода:",
            "❌ Отменить редактирование", "cancel_edit_consumption"
        )


async def show_passport_edit_with_success(update: Update, context: ContextTypes.DEFAULT_TYPE, success_message: str):
    """
    Показывает меню редактирования паспорта с сообщением об успехе
    """
    excavation_name = context.user_data['current_excavation_name']

    # Получаем обновленные данные паспорта
    excavation_id = context.user_data['current_excavation_id']
    passport_data = bot_simple_bd_func.get_excavation_passport(excavation_id)

    text = f"{success_message}\n\n"
    text += f"🏗️ {excavation_name}\n"
    text += f"✏️ Редактировать паспорт крепления\n\n"
    text += f"📏 Выберите материал для изменения нормы расхода:\n\n"

    reply_markup = InlineKeyboardMarkup(passport_edit_keyboard(passport_data))

    # Отправляем новое сообщение
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup
    )
