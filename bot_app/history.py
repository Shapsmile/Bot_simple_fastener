"""Экраны истории проходки."""

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.config import shift_names_with_clock


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
        f"📏 История проведения горной выработки\n\n"
        f"📊 С начала месяца ({current_month}):\n"
        f"📏 {monthly_total} м\n\n"
        f"📅 Уходы по суткам:\n"
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
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_advance_menu")]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Если нет данных за период
    if not daily_data:
        text += "\n📭 За выбранный период уходов нет"

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
        f"📏 История уходов\n\n"
        f"📅 Период: последние {period_names[days]}\n\n"
        f"📅 Уходы по суткам:\n"
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
        [InlineKeyboardButton("◀️ В меню проведения", callback_data="back_to_advance_menu")]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if not daily_data:
        text += "\n📭 За выбранный период уходы не внесены"

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)
