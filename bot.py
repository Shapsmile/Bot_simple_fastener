from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import sqlite3
from datetime import datetime, date
# from config import token
import bot_simple_bd_func
import time

# Состояния для диалога добавления материалов (если используете ConversationHandler)
# Если нет - можно использовать контекст для управления состоянием

# Токен бота
TOKEN = "8300949534:AAE31UX-QcgouJ2iwluz5MYwXCe_t8rOnHw"

# Добавим в начало файла (после TOKEN)
ADMIN_PASSWORD = "1234"  # Временный пароль, потом можно вынести в config

# Глобально или внутри функций используйте:
shift_names = {1: "Первая", 2: "Вторая", 3: "Третья"}

# Глобальное хранилище ожидаемых пользователей
pending_users = {}  # {username_lower: user_data}


# Вызывать cleanup_pending_users() периодически или при добавлении новых пользователей
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


# ===== ОСНОВНЫЕ ЭКРАНЫ =====

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

    # Получаем список выработок из БД
    excavations = bot_simple_bd_func.get_excavations_list()

    # Создаем кнопки для каждой выработки
    keyboard = []
    for exc_id, name in excavations:
        # callback_data будет в формате "exc_1", "exc_2" и т.д.
        keyboard.append([InlineKeyboardButton(name, callback_data=f"exc_{exc_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение с кнопками выбора выработки
    await update.message.reply_text(
        "🏗️ Выберите забой для работы:",
        reply_markup=reply_markup
    )


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
    keyboard = [
        [InlineKeyboardButton("📦 Склад", callback_data="menu_stock")],
        [InlineKeyboardButton("📏 Проходка", callback_data="menu_advance")],
        [InlineKeyboardButton("📄 Паспорт крепления", callback_data="menu_passport")],
    ]

    # Дополнительные кнопки только для администраторов
    if is_admin:
        keyboard.append([InlineKeyboardButton("👨‍💼 Управление пользователями", callback_data="user_management")])

    keyboard.append([InlineKeyboardButton("◀️ Назад к выбору забоя", callback_data="back_to_excavations")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ Выбран забой: {excavation_name}",
        reply_markup=reply_markup
    )


async def show_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран меню склада.
    Показывает доступные операции со складом выбранной выработки
    """
    excavation_name = context.user_data['current_excavation_name']

    # Кнопки для работы со складом
    keyboard = [
        [InlineKeyboardButton("📊 Просмотр остатков", callback_data="stock_view")],
        [InlineKeyboardButton("➕ Пополнение материалов", callback_data="stock_add")],
        [InlineKeyboardButton("◀️ Назад в главное меню", callback_data="back_to_excavation_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение
    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n📦 Управление складом",
        reply_markup=reply_markup
    )


async def show_advance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран меню проходки.
    Показывает доступные операции с проходкой выбранной выработки
    """
    excavation_name = context.user_data['current_excavation_name']

    keyboard = [
        [InlineKeyboardButton("✅ Учесть проходку", callback_data="advance_add")],
        [InlineKeyboardButton("📋 История проходки", callback_data="advance_history")],
        [InlineKeyboardButton("◀️ Назад в главное меню", callback_data="back_to_excavation_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n📏 Управление проходкой",
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
        text = f"🏗️ {excavation_name}\n📦 Склад пуст\n\nНет материалов в паспорте крепления этой выработки."
    else:
        text = f"🏗️ {excavation_name}\n📊 Текущие остатки материалов:\n\n"
        for item in stock_data:
            # Форматируем вывод: "Анкер АС-2: 150.5 шт."
            text += f"• {item['name']}: {item['quantity']:.1f} {item['unit']}\n"

        text += f"\n📋 Всего позиций: {len(stock_data)}"

    # Кнопка для возврата в меню склада
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню склада", callback_data="back_to_stock_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение с данными об остатках
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


# ===== ЭКРАНЫ ДЛЯ ДОБАВЛЕНИЯ МАТЕРИАЛОВ =====

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
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню склада", callback_data="back_to_stock_menu")]]
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
    keyboard.append([InlineKeyboardButton("◀️ Назад в меню склада", callback_data="back_to_stock_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение
    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"➕ Выберите материал для пополнения:",
        reply_markup=reply_markup
    )


async def ask_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    """
    Запрашивает количество для выбранного материала.
    Сохраняет message_id для последующего редактирования
    """
    # Получаем информацию о материале
    conn = sqlite3.connect(bot_simple_bd_func.database)
    cursor = conn.cursor()
    cursor.execute("SELECT name, unit FROM materials WHERE id = ?", (material_id,))
    material_name, unit = cursor.fetchone()
    conn.close()

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
        f"Введите количество для добавления на склад:",
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
            # Удаляем сообщение пользователя с ошибкой
            await update.message.delete()

            # Редактируем предыдущее сообщение с ошибкой
            error_text = (
                f"❌ Количество должно быть больше 0.\n"
                f"Введите количество снова:"
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
            f"📊 Теперь на складе: {current_quantity} {material_unit}"
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

    keyboard = [
        [InlineKeyboardButton("📊 Просмотр остатков", callback_data="stock_view")],
        [InlineKeyboardButton("➕ Пополнение материалов", callback_data="stock_add")],
        [InlineKeyboardButton("◀️ В главное меню", callback_data="back_to_excavation_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем новое сообщение с успехом и меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{success_message}\n\n"
             f"🏗️ {excavation_name}\n"
             f"📦 Управление складом",
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


# ===== ЭКРАНЫ ДЛЯ УЧЕТА ПРОХОДКИ =====

async def show_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран выбора даты для учета проходки.
    Показывает кнопки с вариантами дат
    """
    excavation_name = context.user_data['current_excavation_name']

    # Получаем текущую дату для отображения
    from datetime import date, timedelta
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
        f"📏 Учет проходки\n\n"
        f"📅 Выберите дату:",
        reply_markup=reply_markup
    )


async def handle_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор даты для проходки
    """
    query = update.callback_query
    await query.answer()

    from datetime import date, timedelta
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

        if shift_num == 1:
            button_text = "1️⃣ Первая смена (09:00-17:00)"
        elif shift_num == 2:
            button_text = "2️⃣ Вторая смена (17:00-01:00)"
        else:
            button_text = "3️⃣ Третья смена (01:00-09:00)"

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
        warning_text = f"\n⚠️ В этот день уже учтено: {total_existing} м\n"

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
        [InlineKeyboardButton("✅ Заменить существующие данные", callback_data="confirm_replace")],
        [InlineKeyboardButton("📝 Добавить к существующим", callback_data="add_to_existing")],
        [InlineKeyboardButton("🗑️ Удалить метры", callback_data="delete_meters")],  # НОВАЯ КНОПКА
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
        f"Пример: 2.5 или 3",
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
        f"📏 Сейчас учтено: {existing_meters} м\n\n"
        f"➕ Введите количество ДОПОЛНИТЕЛЬНЫХ метров:\n"
        f"Пример: 1.5 или 2\n\n"
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
            await update.message.delete()
            error_text = "❌ Количество метров должно быть больше 0. Введите снова:"

            if 'meters_input_message_id' in context.user_data:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['meters_input_message_id'],
                    text=error_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Отменить ввод метров", callback_data="cancel_meters_input")
                    ]])
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
                f"✅ Проходка успешно {operation_text}!\n\n"
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
        await update.message.delete()

        error_text = (
            "❌ Пожалуйста, введите число. Например: 2.5 или 3\n"
            "Введите количество метров:"
        )

        if 'meters_input_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['meters_input_message_id'],
                text=error_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить ввод метров", callback_data="cancel_meters_input")
                ]])
            )


async def show_advance_menu_with_success(update: Update, context: ContextTypes.DEFAULT_TYPE, success_message: str):
    """
    Показывает меню проходки с сообщением об успешной операции
    """
    excavation_name = context.user_data['current_excavation_name']

    keyboard = [
        [InlineKeyboardButton("✅ Учесть проходку", callback_data="advance_add")],
        [InlineKeyboardButton("📋 История проходки", callback_data="advance_history")],
        [InlineKeyboardButton("◀️ В главное меню", callback_data="back_to_excavation_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем новое сообщение с успехом и меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{success_message}\n\n"
             f"🏗️ {excavation_name}\n"
             f"📏 Управление проходкой",
        reply_markup=reply_markup
    )


# ===== ЗАГЛУШКИ ДЛЯ ФУНКЦИЙ В РАЗРАБОТКЕ =====

async def show_stock_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран пополнения материалов.
    Перенаправляет на экран выбора материала
    """
    await show_material_selection(update, context)


async def show_advance_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заглушка для учета проходки"""
    excavation_name = context.user_data['current_excavation_name']

    keyboard = [[InlineKeyboardButton("◀️ Назад в меню проходки", callback_data="back_to_advance_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"✅ Учет проходки\n\n"
        f"🔧 Функция находится в разработке\n"
        f"Скоро можно будет учитывать пройденные метры",
        reply_markup=reply_markup
    )


# ===== ЭКРАНЫ ИСТОРИИ ПРОХОДКИ =====

async def show_advance_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Главный экран истории проходки - сводка по дням.
    Показывает кнопки с датами и общей проходкой
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    # Получаем данные за последние 30 дней
    daily_data = bot_simple_bd_func.get_advance_history(excavation_id, 30)
    monthly_total = bot_simple_bd_func.get_monthly_total(excavation_id)

    # Формируем текст заголовка
    current_month = datetime.now().strftime('%B %Y')

    text = (
        f"🏗️ {excavation_name}\n"
        f"📏 История проходки\n\n"
        f"📊 С начала месяца ({current_month}):\n"
        f"📏 {monthly_total} м\n\n"
        f"📅 Проходка по дням:\n"
    )

    # Создаем кнопки для каждого дня
    keyboard = []

    for day, data in daily_data.items():
        day_str = day.strftime('%Y-%m-%d')  # Сохраняем в формате для callback_data
        display_date = day.strftime('%d.%m.%Y')  # Для отображения пользователю
        button_text = f"📅 {display_date} - {data['total']} м"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"day_detail_{day_str}")])

    # Добавляем кнопки фильтров и навигации
    keyboard.extend([
        [InlineKeyboardButton("🕐 За 7 дней", callback_data="filter_7"),
         InlineKeyboardButton("🗓️ За 30 дней", callback_data="filter_30")],
        [InlineKeyboardButton("◀️ В меню проходки", callback_data="back_to_advance_menu")]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Если нет данных за период
    if not daily_data:
        text += "\n📭 За выбранный период метров не было"

    # Обновляем сообщение
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


async def show_day_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, day_str: str):
    """
    Детальный экран проходки за конкретный день.
    Показывает проходку по сменам
    """

    try:
        # Парсим дату из строки (формат из callback_data: YYYY-MM-DD)
        # Например: "2024-01-15"
        day = datetime.strptime(day_str, '%Y-%m-%d').date()
        excavation_name = context.user_data['current_excavation_name']

        # Получаем данные за день
        excavation_id = context.user_data['current_excavation_id']
        daily_data = bot_simple_bd_func.get_advance_history(excavation_id, 30)

        day_data = daily_data.get(day, {'total': 0, 'shifts': {1: 0, 2: 0, 3: 0}})

        # Формируем текст с деталями по сменам
        text = (
            f"🏗️ {excavation_name}\n"
            f"📅 {day.strftime('%d.%m.%Y')}\n\n"
            f"📏 Пройдено за сутки: {day_data['total']} м\n\n"
            f"🕒 Пройдено по сменам:\n"
        )

        shift_names_with_clock = {
            1: "1️⃣ Первая смена (09:00-17:00)",
            2: "2️⃣ Вторая смена (17:00-01:00)",
            3: "3️⃣ Третья смена (01:00-09:00)"
        }

        for shift_num in [1, 2, 3]:
            meters = day_data['shifts'][shift_num]
            shift_text = shift_names_with_clock[shift_num]
            if meters > 0:
                text += f"  {shift_text}: {meters} м\n"
            else:
                text += f"  {shift_text}: ❌\n"

        # Кнопка возврата
        keyboard = [[InlineKeyboardButton("◀️ Назад к истории", callback_data="back_to_history")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Обновляем сообщение
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    except ValueError as e:
        # Если ошибка парсинга даты
        print(f"❌ Ошибка парсинга даты: {day_str}, ошибка: {e}")
        await update.callback_query.edit_message_text(
            "❌ Ошибка отображения данных. Попробуйте снова."
        )


async def show_filtered_history(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    """
    Показывает историю за определенный период
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    # Получаем данные за указанный период
    daily_data = bot_simple_bd_func.get_advance_history(excavation_id, days)

    # Формируем текст
    period_names = {7: "7 дней", 30: "30 дней"}
    text = (
        f"🏗️ {excavation_name}\n"
        f"📏 История проходки\n\n"
        f"📅 Период: последние {period_names[days]}\n\n"
        f"📅 Проходка по дням:\n"
    )

    # Создаем кнопки для каждого дня
    keyboard = []

    for day, data in daily_data.items():
        day_str = day.strftime('%d.%m.%Y')
        button_text = f"📅 {day_str} - {data['total']} м"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"day_detail_{day}")])

    # Добавляем кнопки фильтров
    keyboard.extend([
        [InlineKeyboardButton("🕐 За 7 дней", callback_data="filter_7"),
         InlineKeyboardButton("🗓️ За 30 дней", callback_data="filter_30")],
        [InlineKeyboardButton("◀️ В меню проходки", callback_data="back_to_advance_menu")]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if not daily_data:
        text += "\n📭 За выбранный период проходок не было"

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


# ===== Обработчики для текстового ввода даты и навигации =====

async def process_custom_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод произвольной даты
    """
    try:
        date_str = update.message.text.strip()
        work_date = datetime.strptime(date_str, '%d.%m.%Y').date()

        # Проверяем что дата не в будущем
        if work_date > date.today():
            await update.message.delete()  # Удаляем сообщение с ошибкой

            error_text = "❌ Дата не может быть в будущем. Введите корректную дату:"

            if 'date_input_message_id' in context.user_data:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['date_input_message_id'],
                    text=error_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Отменить ввод даты", callback_data="cancel_date_input")
                    ]])
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
        await update.message.delete()  # Удаляем сообщение с ошибкой

        error_text = (
            "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ\n"
            "Пример: 25.12.2025\n\n"
            "Введите дату снова:"
        )

        if 'date_input_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['date_input_message_id'],
                text=error_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить ввод даты", callback_data="cancel_date_input")
                ]])
            )


async def show_shift_selection_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает выбор смены после ввода даты через сообщение
    БЕЗ промежуточных сообщений
    """
    excavation_name = context.user_data['current_excavation_name']
    work_date = context.user_data['advance_work_date']

    keyboard = [
        [InlineKeyboardButton("1️⃣ Первая смена (09:00-17:00)", callback_data="shift_1")],
        [InlineKeyboardButton("2️⃣ Вторая смена (17:00-01:00)", callback_data="shift_2")],
        [InlineKeyboardButton("3️⃣ Третья смена (01:00-09:00)", callback_data="shift_3")],
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


# ===== ЭКРАНЫ ДЛЯ ПАСПОРТА КРЕПЛЕНИЯ =====

async def show_passport_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Меню управления паспортом крепления
    """
    excavation_name = context.user_data['current_excavation_name']

    keyboard = [
        [InlineKeyboardButton("📋 Просмотр паспорта", callback_data="passport_view")],
        [InlineKeyboardButton("✏️ Редактирование паспорта", callback_data="passport_edit")],
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
            f"📏 Нормы расхода на 1 метр проходки:\n\n"
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
    excavation_name = context.user_data['current_excavation_name']

    # Создаем клавиатуру с кнопкой отмены
    keyboard = [[InlineKeyboardButton("❌ Отменить", callback_data="back_to_passport_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"✏️ Редактирование паспорта\n\n"
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


async def show_passport_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран редактирования паспорта крепления.
    Показывает материалы с текущими нормами расхода
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

        # Создаем кнопки для каждого материала
        keyboard = []
        for item in passport_data:
            button_text = f"{item['name']}: {item['consumption_per_meter']} {item['unit']}/м"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_mat_{item['material_id']}")])

        # Добавляем кнопку возврата
        keyboard.append([InlineKeyboardButton("◀️ Назад в меню паспорта", callback_data="back_to_passport_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup
    )


async def ask_new_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE, material_id: int):
    """
    Запрашивает новую норму расхода для материала
    """
    # Получаем информацию о материале
    conn = sqlite3.connect(bot_simple_bd_func.database)
    cursor = conn.cursor()
    cursor.execute("SELECT name, unit FROM materials WHERE id = ?", (material_id,))
    material_name, unit = cursor.fetchone()

    # Получаем текущую норму расхода
    excavation_id = context.user_data['current_excavation_id']
    cursor.execute('''
        SELECT consumption_per_meter 
        FROM excavation_materials 
        WHERE excavation_id = ? AND material_id = ?
    ''', (excavation_id, material_id))

    current_consumption = cursor.fetchone()[0]
    conn.close()

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
            await update.message.delete()
            error_text = "❌ Норма расхода не может быть отрицательной. Введите снова:"

            if 'consumption_edit_message_id' in context.user_data:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['consumption_edit_message_id'],
                    text=error_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Отменить редактирование", callback_data="cancel_edit_consumption")
                    ]])
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
        await update.message.delete()

        error_text = (
            "❌ Пожалуйста, введите число. Например: 10.5 или 8\n"
            "Введите новую норму расхода:"
        )

        if 'consumption_edit_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['consumption_edit_message_id'],
                text=error_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить редактирование", callback_data="cancel_edit_consumption")
                ]])
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
    text += f"✏️ Редактирование паспорта\n\n"
    text += f"📏 Выберите материал для изменения нормы расхода:\n\n"

    # Создаем кнопки для каждого материала
    keyboard = []
    for item in passport_data:
        button_text = f"{item['name']}: {item['consumption_per_meter']} {item['unit']}/м"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_mat_{item['material_id']}")])

    # Добавляем кнопку возврата
    keyboard.append([InlineKeyboardButton("◀️ Назад в меню паспорта", callback_data="back_to_passport_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем новое сообщение
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup
    )


# ===== СИСТЕМА УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ =====

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
        [InlineKeyboardButton("🗑️ Удалить пользователя", callback_data="users_remove")],  # НОВАЯ КНОПКА
        [InlineKeyboardButton("◀️ В главное меню", callback_data="back_to_excavation_menu")]
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


# ===== ГЛАВНЫЙ ОБРАБОТЧИК КНОПОК =====

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Основной обработчик всех нажатий на кнопки.
    Определяет какая кнопка нажата и вызывает соответствующую функцию
    """
    # Проверяем доступ
    if not await check_access(update, context):
        return

    query = update.callback_query
    await query.answer()  # Убираем "часики" на кнопке

    # Получаем данные с нажатой кнопки
    data = query.data

    # Обработка выбора выработки
    if data.startswith("exc_"):
        excavation_id = int(data.replace("exc_", ""))
        await show_excavation_menu(update, context, excavation_id)

    # Обработка главного меню
    elif data == "menu_stock":
        await show_stock_menu(update, context)
    elif data == "menu_advance":
        await show_advance_menu(update, context)

    # Обработка навигации "Назад"
    elif data == "back_to_excavation_menu":
        # Возврат в главное меню выработки
        excavation_id = context.user_data['current_excavation_id']
        await show_excavation_menu(update, context, excavation_id)
    elif data == "back_to_excavations":
        # Возврат к выбору выработки
        await start_from_button(update, context)
    elif data == "back_to_stock_menu":
        # Возврат в меню склада
        await show_stock_menu(update, context)
    elif data == "back_to_advance_menu":
        # Возврат в меню проходки
        await show_advance_menu(update, context)

    # Обработка функций склада
    elif data == "stock_view":
        await show_stock_view(update, context)
    elif data == "stock_add":
        await show_stock_add(update, context)

    # Обработка выбора материала для добавления
    elif data.startswith("add_mat_"):
        material_id = int(data.replace("add_mat_", ""))
        await ask_quantity(update, context, material_id)

    # Обработка отмены добавления материала
    elif data == "cancel_add_material":
        await cancel_add_material(update, context)

    # Обработка учета проходки
    elif data == "advance_add":
        await show_date_selection(update, context)

    # Обработка выбора даты
    elif data.startswith("date_"):
        await handle_date_selection(update, context)

    # Обработка выбора смены
    elif data.startswith("shift_"):
        await handle_shift_selection(update, context)

    # Обработка навигации в учете проходки
    elif data == "back_to_date_selection":
        await show_date_selection(update, context)
    elif data == "cancel_date_input":
        await show_date_selection(update, context)
    elif data == "cancel_meters_input":
        await show_shift_selection(update, context)

    # Обработка истории проходки
    elif data == "advance_history":
        await show_advance_history(update, context)

    # Обработка деталей дня
    elif data.startswith("day_detail_"):
        day_str = data.replace("day_detail_", "")
        await show_day_detail(update, context, day_str)

    # Обработка фильтров периода
    elif data == "filter_7":
        await show_filtered_history(update, context, 7)
    elif data == "filter_30":
        await show_filtered_history(update, context, 30)

    # Обработка навигации в истории
    elif data == "back_to_history":
        await show_advance_history(update, context)

    # Обработка вариантов при замене данных
    elif data == "confirm_replace":
        # Пользователь выбрал замену - переходим к вводу новых метров
        await ask_meters_input(update, context)
        # Устанавливаем флаг, что это замена
        context.user_data['is_replacement'] = True

    elif data == "add_to_existing":
        # Пользователь выбрал добавление - переходим к вводу дополнительных метров
        await ask_additional_meters(update, context)
        context.user_data['is_addition'] = True

        # Обработка вариантов при замене данных
    elif data == "confirm_replace":
        # Пользователь выбрал замену - переходим к вводу новых метров
        await ask_meters_input(update, context)
        context.user_data['is_replacement'] = True

    elif data == "add_to_existing":
        # Пользователь выбрал добавление - переходим к вводу дополнительных метров
        await ask_additional_meters(update, context)
        context.user_data['is_addition'] = True

        # Обработка удаления метров
    elif data == "delete_meters":
        # Пользователь выбрал удаление - показываем подтверждение
        await show_delete_confirmation(update, context)

    elif data == "confirm_delete":
        # Пользователь подтвердил удаление - удаляем данные
        excavation_id = context.user_data['current_excavation_id']
        work_date = context.user_data['advance_work_date']
        shift_number = context.user_data['advance_shift_number']

        # Удаляем данные из БД
        bot_simple_bd_func.delete_advance_from_db(excavation_id, work_date, shift_number)

        # Показываем сообщение об успехе
        await show_delete_success(update, context)

    elif data == "cancel_delete":
        # Пользователь отменил удаление - возвращаемся к выбору действия
        existing_meters = context.user_data.get('existing_meters', 0)
        await show_replace_warning(update, context, existing_meters)

    # Обработка главного меню выработки (ДОБАВЛЯЕМ ПАСПОРТ)
    elif data == "menu_passport":
        await show_passport_menu(update, context)

    # Обработка паспорта крепления
    elif data == "passport_view":
        await show_passport_view(update, context)
    elif data == "passport_edit":
        await ask_password_for_edit(update, context)

    # Обработка редактирования паспорта
    elif data.startswith("edit_mat_"):
        material_id = int(data.replace("edit_mat_", ""))
        await ask_new_consumption(update, context, material_id)
    elif data == "cancel_edit_consumption":
        await show_passport_edit(update, context)

    # Обработка навигации в паспорте
    elif data == "back_to_passport_menu":
        await show_passport_menu(update, context)

    # Обработка отмены редактирования потребления
    elif data == "cancel_edit_consumption":
        # Очищаем флаг авторизации при отмене
        context.user_data.pop('passport_edit_authorized', None)
        await show_passport_edit(update, context)

    # Обработка возврата в меню паспорта
    elif data == "back_to_passport_menu":
        # Очищаем флаг авторизации при возврате
        context.user_data.pop('passport_edit_authorized', None)
        await show_passport_menu(update, context)

        # Обработка управления пользователями
    elif data == "user_management":
        await show_user_management(update, context)
    elif data == "users_list":
        await show_users_list(update, context)
    elif data == "users_add":
        await ask_user_details(update, context)
    elif data == "users_remove":
        await show_users_for_removal(update, context)
    elif data == "back_to_user_management":
        await show_user_management(update, context)

    # Обработка удаления пользователей
    elif data.startswith("remove_user_"):
        user_id = int(data.replace("remove_user_", ""))
        await show_remove_confirmation(update, context, user_id)
    elif data == "confirm_remove":
        await process_user_removal(update, context)
    elif data == "cancel_remove":
        await show_users_for_removal(update, context)


async def handle_all_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Определяет тип текстового ввода и направляет нужный обработчик
    """
    text = update.message.text.strip()

    print(f"🔍 Текстовый ввод: '{text}'")
    print(f"🔍 Контекст: {list(context.user_data.keys())}")

    # 1. Если пользователь вводит данные нового пользователя
    if 'user_add_message_id' in context.user_data:
        print("🎯 Направляем в обработку нового пользователя")
        await process_new_user(update, context)

    # 2. Если пользователь вводит пароль для редактирования паспорта
    elif 'password_message_id' in context.user_data:
        print("🎯 Направляем в обработку пароля")
        await process_password_input(update, context)

    # 3. Если пользователь вводит новую норму расхода
    elif 'consumption_edit_message_id' in context.user_data:
        print("🎯 Направляем в обработку нормы расхода")
        await process_new_consumption(update, context)

    # 4. Если пользователь вводит дату для проходки
    elif 'date_input_message_id' in context.user_data:
        print("🎯 Направляем в обработку даты")
        await process_custom_date_input(update, context)

    # 5. Если пользователь вводит метры для проходки
    elif 'meters_input_message_id' in context.user_data:
        print("🎯 Направляем в обработку метров")
        await process_meters_input(update, context)

    # 6. Если пользователь вводит количество материала
    elif 'quantity_message_id' in context.user_data:
        print("🎯 Направляем в обработку количества материала")
        await process_quantity_input(update, context)

    # 7. Специальные случаи
    elif (context.user_data.get('is_replacement') or
          context.user_data.get('is_addition') or
          'advance_shift_number' in context.user_data):
        print("🎯 Направляем в обработку метров (специальный случай для 0)")
        await process_meters_input(update, context)

    # 8. Если пользователь авторизован и редактирует паспорт
    elif (context.user_data.get('passport_edit_authorized') and
          'editing_material_id' in context.user_data):
        print("🎯 Направляем в обработку нормы расхода (авторизован)")
        await process_new_consumption(update, context)

    else:
        # Если непонятно что вводит - показываем справку
        print("❓ Неизвестный ввод, показываем справку")
        await update.message.reply_text(
            "🤔 Не понял что вы хотите сделать.\n"
            "Используйте кнопки меню или /start для начала работы."
        )


async def start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запуск из кнопки (когда пользователь нажимает "Назад к выбору забоя")
    Показывает экран выбора выработки без команды /start
    """
    # Проверяем доступ
    if not await check_access(update, context):
        return

    # Получаем актуальный список выработок
    excavations = bot_simple_bd_func.get_excavations_list()

    # Создаем кнопки выбора
    keyboard = []
    for exc_id, name in excavations:
        keyboard.append([InlineKeyboardButton(name, callback_data=f"exc_{exc_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Обновляем сообщение
    query = update.callback_query
    await query.edit_message_text(
        "🏗️ Выберите забой для работы:",
        reply_markup=reply_markup
    )


async def handle_new_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает сообщения от потенциально новых пользователей
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    print(f"🔍 Новое сообщение от пользователя: ID={user_id}, @{username}, {full_name}")
    print(f"🔍 Ожидаемые пользователи: {list(pending_users.keys())}")

    # Если пользователь уже авторизован - пропускаем обычную обработку
    if bot_simple_bd_func.is_user_authorized(user_id):
        print("✅ Пользователь уже авторизован, перенаправляем в обычную обработку")
        await handle_all_text_input(update, context)
        return

    # ПРОВЕРЯЕМ ГЛОБАЛЬНОЕ ХРАНИЛИЩЕ
    if username and username.lower() in pending_users:
        pending_user = pending_users[username.lower()]
        print(f"✅ Совпадение найдено в глобальном хранилище! Добавляем пользователя {user_id}")

        # Добавляем пользователя в базу
        bot_simple_bd_func.add_authorized_user(
            user_id=user_id,
            username=username,  # Реальный username (с регистром)
            full_name=pending_user['full_name'],
            role=pending_user['role'],
            added_by=pending_user['added_by']
        )

        # Удаляем из ожидаемых
        del pending_users[username.lower()]
        print(f"✅ Пользователь удален из ожидаемых. Остались: {list(pending_users.keys())}")

        # Уведомляем администратора
        admin_id = pending_user['added_by']
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"✅ Пользователь успешно добавлен!\n\n"
                    f"👤 @{username}\n"
                    f"📛 {pending_user['full_name']}\n"
                    f"🎯 Роль: {pending_user['role']}\n"
                    f"🆔 ID: {user_id}\n\n"
                    f"Пользователь теперь имеет доступ к боту."
                )
            )
            print(f"✅ Уведомление отправлено администратору {admin_id}")
        except Exception as e:
            print(f"❌ Не удалось уведомить администратора: {e}")

        # Приветствуем нового пользователя
        await update.message.reply_text(
            f"✅ Добро пожаловать, {pending_user['full_name']}!\n\n"
            f"Вы были успешно добавлены в систему учета.\n"
            f"Ваша роль: {pending_user['role']}\n\n"
            f"Используйте /start для начала работы."
        )

        return

    # Если пользователь не авторизован и не ожидается - блокируем
    print("🚫 Пользователь не авторизован и не ожидается")
    await update.message.reply_text(
        "🚫 Доступ запрещен!\n\n"
        "Вы не авторизованы для использования этого бота.\n"
        "Обратитесь к администратору для получения доступа."
    )


async def user_management_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для управления пользователями
    """
    # Проверяем доступ
    if not await check_access(update, context):
        return

    await show_user_management(update, context)


# ===== MIDDLEWARE ДЛЯ ПРОВЕРКИ ДОСТУПА =====

async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


# ===== ЗАПУСК БОТА =====

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


if __name__ == "__main__":
    main()
