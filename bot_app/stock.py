"""Хендлеры склада: пополнение материалов."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.common import clear_input_state, show_input_error
from bot_app.keyboards import stock_menu_keyboard


async def show_material_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран выбора материала для пополнения.
    Показывает все материалы из паспорта выработки в виде кнопок
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    # Получаем материалы из паспорта выработки
    materials = bot_simple_bd_func.get_excavation_materials(excavation_id)

    if not materials:
        # Если нет материалов в паспорте - показываем сообщение
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню остатков", callback_data="back_to_stock_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query = update.callback_query
        await query.edit_message_text(
            f"🏗️ {excavation_name}\n"
            f"❌ В паспорте выработки нет материалов\n"
            f"Обратитесь к администратору для настройки паспорта крепления",
            reply_markup=reply_markup
        )
        return

    # Создаем кнопки для каждого материала
    keyboard = []
    for material_id, name, unit in materials:
        # callback_data будет в формате "add_mat_1", "add_mat_2" и т.д.
        keyboard.append([InlineKeyboardButton(f"{name} ({unit})", callback_data=f"add_mat_{material_id}")])

    # Добавляем кнопку возврата
    keyboard.append([InlineKeyboardButton("◀️ Назад в меню остатков", callback_data="back_to_stock_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение
    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"➕ Выберите материал для пополнения:",
        reply_markup=reply_markup
    )


async def show_stock_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран пополнения материалов.
    Перенаправляет на экран выбора материала
    """
    await show_material_selection(update, context)


async def ask_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    """
    Запрашивает количество для выбранного материала.
    Сохраняет message_id для последующего редактирования
    """
    clear_input_state(context)  # Сбрасываем любые предыдущие состояния ввода
    # Получаем информацию о материале
    material_name, unit = bot_simple_bd_func.get_material_info(material_id)

    # Сохраняем выбранный материал в контексте
    context.user_data['selected_material_id'] = material_id
    context.user_data['selected_material_name'] = material_name
    context.user_data['selected_material_unit'] = unit

    excavation_name = context.user_data['current_excavation_name']

    # Создаем клавиатуру с кнопкой отмены
    keyboard = [[InlineKeyboardButton("❌ Отменить добавление", callback_data="cancel_add_material")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Запрашиваем количество и сохраняем ID сообщения
    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📦 Материал: {material_name}\n"
        f"📏 Единица: {unit}\n\n"
        f"Введите количество для добавления в забой:",
        reply_markup=reply_markup
    )

    # Сохраняем ID сообщения для последующего редактирования
    context.user_data['quantity_message_id'] = message.message_id


async def process_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод количества и добавляет материал на склад
    """
    try:
        # Пытаемся преобразовать ввод в число
        quantity = float(update.message.text)

        if quantity <= 0:
            await show_input_error(
                update, context, 'quantity_message_id',
                "❌ Количество должно быть больше 0.\nВведите количество снова:",
                "❌ Отменить добавление", "cancel_add_material"
            )
            return

        # Получаем данные
        excavation_id = context.user_data['current_excavation_id']
        excavation_name = context.user_data['current_excavation_name']
        material_id = context.user_data['selected_material_id']
        material_name = context.user_data['selected_material_name']
        material_unit = context.user_data['selected_material_unit']

        # Добавляем в базу
        bot_simple_bd_func.add_material_to_stock(excavation_id, material_id, quantity)

        # Получаем остатки
        stock_data = bot_simple_bd_func.get_current_stock(excavation_id)
        current_quantity = next(
            (item['quantity'] for item in stock_data if item['name'] == material_name),
            0
        )

        # Сообщение об успехе
        success_text = (
            f"✅ Материал успешно добавлен!\n\n"
            f"🏗️ {excavation_name}\n"
            f"📦 {material_name}\n"
            f"📥 Добавлено: {quantity} {material_unit}\n"
            f"📊 Теперь в забое: {current_quantity} {material_unit}"
        )

        # Удаляем сообщение пользователя
        await update.message.delete()

        # ВМЕСТО показа кнопок навигации - ВОЗВРАЩАЕМСЯ В МЕНЮ СКЛАДА
        if 'quantity_message_id' in context.user_data:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['quantity_message_id']
            )

        # Очищаем временные данные
        context.user_data.pop('selected_material_id', None)
        context.user_data.pop('selected_material_name', None)
        context.user_data.pop('selected_material_unit', None)
        context.user_data.pop('quantity_message_id', None)

        # ПОКАЗЫВАЕМ МЕНЮ СКЛАДА с сообщением об успехе
        await show_stock_menu_with_success(update, context, success_text)

    except ValueError:
        # Удаляем сообщение пользователя с ошибкой
        await update.message.delete()
        # Редактируем предыдущее сообщение с ошибкой формата
        error_text = (
            f"❌ Пожалуйста, введите число.\n"
            f"Пример: 100 или 50.5\n\n"
            f"Введите количество:"
        )

        if 'quantity_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['quantity_message_id'],
                text=error_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить добавление", callback_data="cancel_add_material")
                ]])
            )


async def show_stock_menu_with_success(update: Update, context: ContextTypes.DEFAULT_TYPE, success_message: str):
    """
    Показывает меню склада с сообщением об успешной операции
    """
    excavation_name = context.user_data['current_excavation_name']

    reply_markup = InlineKeyboardMarkup(stock_menu_keyboard())

    # Отправляем новое сообщение с успехом и меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{success_message}\n\n"
             f"🏗️ {excavation_name}\n"
             f"📦 Управление остатками материалов в забое",
        reply_markup=reply_markup
    )


async def cancel_add_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отмена процесса добавления материала.
    Возвращает в меню выбора материалов
    """
    # Очищаем временные данные
    context.user_data.pop('selected_material_id', None)
    context.user_data.pop('selected_material_name', None)
    context.user_data.pop('selected_material_unit', None)

    # Возвращаемся к выбору материалов
    await show_material_selection(update, context)
