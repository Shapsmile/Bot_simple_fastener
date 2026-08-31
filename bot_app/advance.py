"""Хендлеры учета проходки: дата, смена, ввод метров, удаление."""

from datetime import date, datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.common import show_input_error
from bot_app.config import shift_names, shift_names_with_clock
from bot_app.keyboards import advance_menu_keyboard


async def show_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран выбора даты для учета проходки.
    Показывает кнопки с вариантами дат
    """
    excavation_name = context.user_data['current_excavation_name']

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Создаем кнопки выбора даты
    keyboard = [
        [InlineKeyboardButton(f"📅 Сегодня ({today.strftime('%d.%m.%Y')})", callback_data="date_today")],
        [InlineKeyboardButton(f"📅 Вчера ({yesterday.strftime('%d.%m.%Y')})", callback_data="date_yesterday")],
        [InlineKeyboardButton("📅 Выбрать другую дату", callback_data="date_custom")],
        [InlineKeyboardButton("◀️ Назад в меню проходки", callback_data="back_to_advance_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение
    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📏 Меню ввода пройденных метров\n\n"
        f"📅 Выберите дату:",
        reply_markup=reply_markup
    )


async def handle_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор даты для проходки
    """
    query = update.callback_query
    await query.answer()

    today = date.today()

    if query.data == "date_today":
        work_date = today
    elif query.data == "date_yesterday":
        work_date = today - timedelta(days=1)
    else:  # date_custom
        # Для выбора произвольной даты переходим в текстовый ввод
        await ask_custom_date(update, context)
        return

    # Сохраняем выбранную дату в контексте
    context.user_data['advance_work_date'] = work_date
    context.user_data['advance_date_message_id'] = query.message.message_id

    # Переходим к выбору смены
    await show_shift_selection(update, context)


async def ask_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает произвольную дату у пользователя
    """
    excavation_name = context.user_data['current_excavation_name']

    # Создаем клавиатуру с кнопкой отмены
    keyboard = [[InlineKeyboardButton("❌ Отменить ввод даты", callback_data="cancel_date_input")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Запрашиваем дату
    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📅 Введите дату в формате ДД.ММ.ГГГГ:\n"
        f"Пример: 25.12.2025\n\n"
        f"Или используйте кнопку ниже для отмены:",
        reply_markup=reply_markup
    )

    # Сохраняем ID сообщения для последующего редактирования
    context.user_data['date_input_message_id'] = message.message_id


async def show_shift_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран выбора смены для проходки.
    Показывает сколько метров уже учтено в каждой смене
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']
    work_date = context.user_data['advance_work_date']

    # Создаем кнопки выбора смены с информацией о существующих данных
    keyboard = []

    for shift_num in [1, 2, 3]:
        # Проверяем есть ли уже проходка для этой смены
        existing_meters = bot_simple_bd_func.get_existing_advance(excavation_id, work_date, shift_num)

        button_text = shift_names_with_clock[shift_num]

        # Добавляем информацию о существующих метрах
        if existing_meters:
            button_text += f" 📏 {existing_meters} м"

        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"shift_{shift_num}")])

    # Добавляем кнопку возврата
    keyboard.append([InlineKeyboardButton("◀️ Назад к выбору даты", callback_data="back_to_date_selection")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Формируем текст с предупреждением если есть учтенные данные
    warning_text = ""
    total_existing = 0
    for shift_num in [1, 2, 3]:
        existing_meters = bot_simple_bd_func.get_existing_advance(excavation_id, work_date, shift_num)
        if existing_meters:
            total_existing += existing_meters

    if total_existing > 0:
        warning_text = f"\n⚠️ За ути сутки уже учтено: {total_existing} м\n"

    # Обновляем сообщение
    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📅 Дата: {work_date.strftime('%d.%m.%Y')}"
        f"{warning_text}\n"
        f"🕒 Выберите смену:\n"
        f"📏 - уже учтенные метры",
        reply_markup=reply_markup
    )

    # Сохраняем ID сообщения для навигации
    context.user_data['shift_selection_message_id'] = message.message_id


async def show_shift_selection_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает выбор смены после ввода даты через сообщение
    БЕЗ промежуточных сообщений
    """
    excavation_name = context.user_data['current_excavation_name']
    work_date = context.user_data['advance_work_date']

    keyboard = [
        [InlineKeyboardButton(shift_names_with_clock[1], callback_data="shift_1")],
        [InlineKeyboardButton(shift_names_with_clock[2], callback_data="shift_2")],
        [InlineKeyboardButton(shift_names_with_clock[3], callback_data="shift_3")],
        [InlineKeyboardButton("◀️ Назад к выбору даты", callback_data="back_to_date_selection")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🏗️ {excavation_name}\n"
             f"📅 Дата: {work_date.strftime('%d.%m.%Y')}\n\n"
             f"🕒 Выберите смену:",
        reply_markup=reply_markup
    )


async def handle_shift_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор смены и предупреждает о замене если данные уже есть
    """
    query = update.callback_query
    await query.answer()

    # Получаем номер смены из callback_data
    shift_number = int(query.data.replace("shift_", ""))

    # Сохраняем выбранную смену в контексте
    context.user_data['advance_shift_number'] = shift_number

    # Проверяем есть ли уже данные для этой смены
    excavation_id = context.user_data['current_excavation_id']
    work_date = context.user_data['advance_work_date']
    existing_meters = bot_simple_bd_func.get_existing_advance(excavation_id, work_date, shift_number)

    if existing_meters:
        # Если данные уже есть - показываем предупреждение
        await show_replace_warning(update, context, existing_meters)
    else:
        # Если данных нет - сразу переходим к вводу метров
        await ask_meters_input(update, context)


async def show_replace_warning(update: Update, context: ContextTypes.DEFAULT_TYPE, existing_meters: float):
    """
    Показывает предупреждение о замене существующих данных с опцией удаления
    """
    excavation_name = context.user_data['current_excavation_name']
    work_date = context.user_data['advance_work_date']
    shift_number = context.user_data['advance_shift_number']

    shift_name = shift_names.get(shift_number, f"Смена {shift_number}")

    # Создаем клавиатуру с вариантами действий (ДОБАВЛЯЕМ УДАЛЕНИЕ)
    keyboard = [
        [InlineKeyboardButton("✅ Изменить уход", callback_data="confirm_replace")],
        [InlineKeyboardButton("📝 Добавить к существующему", callback_data="add_to_existing")],
        [InlineKeyboardButton("🗑️ Удалить уход", callback_data="delete_meters")],  # НОВАЯ КНОПКА
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_meters_input")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение с предупреждением
    query = update.callback_query
    message = await query.edit_message_text(
        f"⚠️ Внимание!\n\n"
        f"🏗️ {excavation_name}\n"
        f"📅 {work_date.strftime('%d.%m.%Y')}\n"
        f"🕒 {shift_name} смена\n\n"
        f"📏 Уже учтено: {existing_meters} м\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup
    )

    # Сохраняем существующие метры для использования в дальнейшем
    context.user_data['existing_meters'] = existing_meters
    context.user_data['warning_message_id'] = message.message_id


async def ask_meters_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает количество пройденных метров
    """
    excavation_name = context.user_data['current_excavation_name']
    work_date = context.user_data['advance_work_date']
    shift_number = context.user_data['advance_shift_number']

    # Форматируем название смены для красивого отображения
    shift_name = shift_names.get(shift_number, f"Смена {shift_number}")

    # Создаем клавиатуру с кнопкой отмены
    keyboard = [[InlineKeyboardButton("❌ Отменить ввод метров", callback_data="cancel_meters_input")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Запрашиваем метры
    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📅 {work_date.strftime('%d.%m.%Y')}\n"
        f"🕒 {shift_name} смена\n\n"
        f"📏 Введите количество пройденных метров:\n"
        f"Только цифры. Пример: 1.6, 3, 5",
        reply_markup=reply_markup
    )

    # Сохраняем ID сообщения для последующего редактирования
    context.user_data['meters_input_message_id'] = message.message_id


async def ask_additional_meters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает дополнительные метры для добавления к существующим
    """
    excavation_name = context.user_data['current_excavation_name']
    work_date = context.user_data['advance_work_date']
    shift_number = context.user_data['advance_shift_number']
    existing_meters = context.user_data.get('existing_meters', 0)

    shift_name = shift_names.get(shift_number, f"Смена {shift_number}")

    # Создаем клавиатуру с кнопкой отмены
    keyboard = [[InlineKeyboardButton("❌ Отменить добавление", callback_data="cancel_meters_input")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Запрашиваем дополнительные метры
    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📅 {work_date.strftime('%d.%m.%Y')}\n"
        f"🕒 {shift_name} смена\n\n"
        f"📏 Сейчас за учтено: {existing_meters} м\n\n"
        f"➕ Введите количество ДОПОЛНИТЕЛЬНЫХ метров:\n"
        f"Пример: 1.6, 3, 5\n"
        f"📏 Будет всего: {existing_meters} + введенное количество",
        reply_markup=reply_markup
    )

    # Сохраняем ID сообщения для последующего редактирования
    context.user_data['meters_input_message_id'] = message.message_id


async def process_meters_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод метров с учетом замены или добавления
    """
    try:
        meters = float(update.message.text)

        if meters <= 0:
            await show_input_error(
                update, context, 'meters_input_message_id',
                "❌ Количество метров должно быть больше 0. Введите снова:",
                "❌ Отменить ввод метров", "cancel_meters_input"
            )
            return

        # Получаем данные из контекста
        excavation_id = context.user_data['current_excavation_id']
        excavation_name = context.user_data['current_excavation_name']
        work_date = context.user_data['advance_work_date']
        shift_number = context.user_data['advance_shift_number']

        # Определяем тип операции
        is_replacement = context.user_data.get('is_replacement', False)
        is_addition = context.user_data.get('is_addition', False)
        existing_meters = context.user_data.get('existing_meters', 0)

        final_meters = meters
        operation_text = "учтено"

        if is_replacement:
            # Замена существующих данных
            bot_simple_bd_func.add_advance_to_db(excavation_id, meters, shift_number, work_date, replace_existing=True)
            operation_text = "заменено"
        elif is_addition:
            # Добавление к существующим
            final_meters = existing_meters + meters
            bot_simple_bd_func.add_advance_to_db(excavation_id, final_meters, shift_number, work_date, replace_existing=True)
            operation_text = "добавлено"
        else:
            # Обычное добавление (данных не было)
            bot_simple_bd_func.add_advance_to_db(excavation_id, meters, shift_number, work_date)

        # Рассчитываем списание материалов
        consumption_data = bot_simple_bd_func.calculate_consumption(excavation_id, final_meters)

        # Формируем сообщение об успехе
        shift_name = shift_names.get(shift_number, f"Смена {shift_number}")

        if meters == 0 and is_replacement:
            success_text = (
                f"✅ Данные успешно обнулены!\n\n"
                f"🏗️ {excavation_name}\n"
                f"📅 {work_date.strftime('%d.%m.%Y')}\n"
                f"🕒 {shift_name} смена\n"
                f"📏 Проходка удалена из учета\n"
            )
        else:
            success_text = (
                f"✅ Метры за выбранную смену успешно учтены!\n\n"
                f"🏗️ {excavation_name}\n"
                f"📅 {work_date.strftime('%d.%m.%Y')}\n"
                f"🕒 {shift_name} смена\n"
                f"📏 {operation_text.capitalize()}: {meters} м\n"
            )

            if is_addition:
                success_text += f"📏 Теперь всего: {final_meters} м\n\n"
            else:
                success_text += f"📏 Всего: {final_meters} м\n\n"

            if final_meters > 0:
                success_text += f"📋 Списано материалов:\n"
                for item in consumption_data:
                    success_text += f"• {item['name']}: {item['consumed']:.1f} {item['unit']}\n"
            else:
                success_text += f"📋 Списание материалов: нет\n"

        # Удаляем сообщение пользователя и редактируем предыдущее сообщение бота
        await update.message.delete()

        # ВМЕСТО показа кнопок навигации - ВОЗВРАЩАЕМСЯ В МЕНЮ ПРОХОДКИ
        if 'meters_input_message_id' in context.user_data:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['meters_input_message_id']
            )

        # Очищаем временные данные проходки
        context.user_data.pop('advance_work_date', None)
        context.user_data.pop('advance_shift_number', None)
        context.user_data.pop('advance_date_message_id', None)
        context.user_data.pop('shift_selection_message_id', None)
        context.user_data.pop('meters_input_message_id', None)
        context.user_data.pop('date_input_message_id', None)
        context.user_data.pop('is_replacement', None)
        context.user_data.pop('is_addition', None)
        context.user_data.pop('existing_meters', None)
        context.user_data.pop('warning_message_id', None)

        # ПОКАЗЫВАЕМ МЕНЮ ПРОХОДКИ с сообщением об успехе
        await show_advance_menu_with_success(update, context, success_text)

    except ValueError:
        await show_input_error(
            update, context, 'meters_input_message_id',
            "❌ Пожалуйста, введите число. Например: 1.6, 3, 5\nВведите количество метров:",
            "❌ Отменить ввод метров", "cancel_meters_input"
        )


async def show_advance_menu_with_success(update: Update, context: ContextTypes.DEFAULT_TYPE, success_message: str):
    """
    Показывает меню проходки с сообщением об успешной операции
    """
    excavation_name = context.user_data['current_excavation_name']

    reply_markup = InlineKeyboardMarkup(advance_menu_keyboard())

    # Отправляем новое сообщение с успехом и меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{success_message}\n\n"
             f"🏗️ {excavation_name}\n"
             f"📏 Учет пройденных метров",
        reply_markup=reply_markup
    )


async def show_delete_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню проходки после успешного удаления
    """
    excavation_name = context.user_data['current_excavation_name']
    work_date = context.user_data['advance_work_date']
    shift_number = context.user_data['advance_shift_number']
    existing_meters = context.user_data.get('existing_meters', 0)

    shift_name = shift_names.get(shift_number, f"Смена {shift_number}")

    success_text = (
        f"✅ Данные успешно удалены!\n\n"
        f"🏗️ {excavation_name}\n"
        f"📅 {work_date.strftime('%d.%m.%Y')}\n"
        f"🕒 {shift_name} смена\n\n"
        f"🗑️ Удалено: {existing_meters} м\n"
        f"📋 Списание материалов отменено"
    )

    # Удаляем сообщение с подтверждением удаления
    if 'delete_confirmation_message_id' in context.user_data:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['delete_confirmation_message_id']
        )

    # Очищаем временные данные проходки
    context.user_data.pop('advance_work_date', None)
    context.user_data.pop('advance_shift_number', None)
    context.user_data.pop('existing_meters', None)
    context.user_data.pop('delete_confirmation_message_id', None)
    context.user_data.pop('warning_message_id', None)

    # ПОКАЗЫВАЕМ МЕНЮ ПРОХОДКИ
    await show_advance_menu_with_success(update, context, success_text)


async def show_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает подтверждение удаления метров
    """
    excavation_name = context.user_data['current_excavation_name']
    work_date = context.user_data['advance_work_date']
    shift_number = context.user_data['advance_shift_number']
    existing_meters = context.user_data.get('existing_meters', 0)

    shift_name = shift_names.get(shift_number, f"Смена {shift_number}")

    # Создаем клавиатуру с подтверждением удаления
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_delete")],
        [InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_delete")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение с подтверждением
    query = update.callback_query
    message = await query.edit_message_text(
        f"🗑️ Подтверждение удаления\n\n"
        f"🏗️ {excavation_name}\n"
        f"📅 {work_date.strftime('%d.%m.%Y')}\n"
        f"🕒 {shift_name} смена\n\n"
        f"📏 Будет удалено: {existing_meters} м\n\n"
        f"Вы уверены что хотите удалить эти данные?",
        reply_markup=reply_markup
    )

    context.user_data['delete_confirmation_message_id'] = message.message_id


async def process_custom_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод произвольной даты
    """
    try:
        date_str = update.message.text.strip()
        work_date = datetime.strptime(date_str, '%d.%m.%Y').date()

        # Проверяем что дата не в будущем
        if work_date > date.today():
            await show_input_error(
                update, context, 'date_input_message_id',
                "❌ Дата не может быть в будущем. Введите корректную дату:",
                "❌ Отменить ввод даты", "cancel_date_input"
            )
            return

        # Сохраняем дату в контексте
        context.user_data['advance_work_date'] = work_date

        # Удаляем сообщение пользователя
        await update.message.delete()

        # Редактируем предыдущее сообщение бота и переходим к выбору смены
        if 'date_input_message_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['date_input_message_id']
                )
            except ValueError:
                pass  # Игнорируем ошибки если сообщение уже удалено

        # Очищаем ID сообщения ввода даты
        context.user_data.pop('date_input_message_id', None)

        # СРАЗУ переходим к выбору смены
        await show_shift_selection_from_message(update, context)

    except ValueError:
        await show_input_error(
            update, context, 'date_input_message_id',
            "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ\nПример: 25.12.2025\n\nВведите дату снова:",
            "❌ Отменить ввод даты", "cancel_date_input"
        )
