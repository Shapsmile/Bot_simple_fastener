"""Управление материалами: создание материала и добавление в паспорт забоя (только для админов)."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.common import clear_input_state
from bot_app.screens import show_global_settings


# ===== СОЗДАНИЕ НОВОГО МАТЕРИАЛА =====

async def show_material_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает данные нового материала (только для админов)
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if bot_simple_bd_func.get_user_role(user_id) != 'admin':
        await query.answer("🚫 Недостаточно прав!", show_alert=True)
        return

    clear_input_state(context)  # Сбрасываем любые предыдущие состояния ввода

    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="back_to_settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await query.edit_message_text(
        "➕ Добавление нового материала\n\n"
        "Отправьте данные в формате:\n"
        "`Название | Единица измерения`\n\n"
        "Примеры:\n"
        "`Анкер АС-2 | шт`\n"
        "`Сетка ОСС | м²`\n"
        "`Цемент | кг`",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    context.user_data['material_add_message_id'] = message.message_id


async def process_material_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод данных нового материала
    """
    try:
        text = update.message.text.strip()

        print(f"🔍 Обрабатываем данные материала: '{text}'")

        # Парсим формат "Название | Единица"
        if '|' not in text:
            raise ValueError("Используйте формат: Название | Единица измерения")

        name, unit = [part.strip() for part in text.split('|', 1)]

        if not name or not unit:
            raise ValueError("Название и единица измерения не могут быть пустыми")

        # Удаляем сообщение администратора
        await update.message.delete()

        # Добавляем материал в базу
        success, material_id = bot_simple_bd_func.add_material(name, unit)

        if success:
            success_text = (
                f"✅ Материал успешно добавлен!\n\n"
                f"📦 {name}\n"
                f"📏 Единица: {unit}\n"
                f"🆔 ID: {material_id}\n\n"
                f"Теперь его можно добавить в паспорт забоя."
            )
        else:
            success_text = (
                f"❌ Не удалось добавить материал.\n\n"
                f"Материал «{name}» уже существует в справочнике."
            )

        if 'material_add_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['material_add_message_id'],
                text=success_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ В настройки", callback_data="back_to_settings")
                ]])
            )

    except Exception as e:
        print(f"❌ Ошибка при добавлении материала: {e}")
        await update.message.delete()

        error_text = f"❌ Ошибка: {str(e)}"

        if 'material_add_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['material_add_message_id'],
                text=error_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="back_to_settings")
                ]])
            )

    finally:
        # Всегда очищаем ключ, чтобы он не перехватывал последующий ввод
        context.user_data.pop('material_add_message_id', None)


# ===== ДОБАВЛЕНИЕ МАТЕРИАЛА В ПАСПОРТ ЗАБОЯ =====

async def show_passport_material_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает список материалов для добавления в паспорт забоя (только для админов)
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if bot_simple_bd_func.get_user_role(user_id) != 'admin':
        await query.answer("🚫 Недостаточно прав!", show_alert=True)
        return

    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    # Все материалы из справочника
    all_materials = bot_simple_bd_func.get_all_materials()
    # Материалы уже в паспорте
    passport_materials = bot_simple_bd_func.get_excavation_materials(excavation_id)
    passport_ids = {m[0] for m in passport_materials}

    # Только те, которых ещё нет в паспорте
    available = [m for m in all_materials if m[0] not in passport_ids]

    if not available:
        text = (
            f"🏗️ {excavation_name}\n"
            f"📄 Добавление в паспорт\n\n"
            f"❌ Нет доступных материалов для добавления.\n"
            f"Все материалы уже есть в паспорте, либо справочник пуст."
        )
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню паспорта", callback_data="back_to_passport_menu")]]
    else:
        text = (
            f"🏗️ {excavation_name}\n"
            f"📄 Добавление в паспорт\n\n"
            f"Выберите материал для добавления:\n\n"
        )
        keyboard = []
        for material_id, name, unit in available:
            keyboard.append([InlineKeyboardButton(f"📦 {name} ({unit})", callback_data=f"passport_add_mat_{material_id}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад в меню паспорта", callback_data="back_to_passport_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)


async def ask_passport_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    """
    Запрашивает норму расхода для добавляемого в паспорт материала
    """
    clear_input_state(context)  # Сбрасываем любые предыдущие состояния ввода
    material_info = bot_simple_bd_func.get_material_info(material_id)
    if not material_info:
        await update.callback_query.answer("❌ Материал не найден!", show_alert=True)
        return

    material_name, unit = material_info
    excavation_name = context.user_data['current_excavation_name']

    context.user_data['passport_add_material_id'] = material_id
    context.user_data['passport_add_material_name'] = material_name
    context.user_data['passport_add_material_unit'] = unit

    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="back_to_passport_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📄 Добавление в паспорт\n\n"
        f"📦 Материал: {material_name}\n"
        f"📏 Единица: {unit}\n\n"
        f"Введите норму расхода на 1 метр:\n"
        f"Пример: 10.5 или 8",
        reply_markup=reply_markup
    )

    context.user_data['passport_consumption_message_id'] = message.message_id


async def process_passport_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод нормы расхода и добавляет материал в паспорт
    """
    try:
        consumption = float(update.message.text)

        if consumption < 0:
            raise ValueError("Норма расхода не может быть отрицательной")

        excavation_id = context.user_data['current_excavation_id']
        excavation_name = context.user_data['current_excavation_name']
        material_id = context.user_data['passport_add_material_id']
        material_name = context.user_data['passport_add_material_name']
        material_unit = context.user_data['passport_add_material_unit']

        # Удаляем сообщение пользователя
        await update.message.delete()

        # Добавляем материал в паспорт
        success = bot_simple_bd_func.add_material_to_passport(excavation_id, material_id, consumption)

        if success:
            success_text = (
                f"✅ Материал добавлен в паспорт!\n\n"
                f"🏗️ {excavation_name}\n"
                f"📦 {material_name}\n"
                f"📏 Норма: {consumption} {material_unit}/м"
            )
        else:
            success_text = (
                f"❌ Не удалось добавить материал.\n\n"
                f"Материал «{material_name}» уже есть в паспорте этого забоя."
            )

        # Удаляем сообщение с запросом нормы
        if 'passport_consumption_message_id' in context.user_data:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['passport_consumption_message_id']
            )

        # Очищаем временные данные
        context.user_data.pop('passport_add_material_id', None)
        context.user_data.pop('passport_add_material_name', None)
        context.user_data.pop('passport_add_material_unit', None)
        context.user_data.pop('passport_consumption_message_id', None)

        # Показываем результат
        keyboard = [[InlineKeyboardButton("◀️ В меню паспорта", callback_data="back_to_passport_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=success_text,
            reply_markup=reply_markup
        )

    except ValueError:
        await update.message.delete()
        if 'passport_consumption_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['passport_consumption_message_id'],
                text=(
                    "❌ Пожалуйста, введите число. Например: 10.5 или 8\n"
                    "Введите норму расхода на 1 метр:"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="back_to_passport_menu")
                ]])
            )