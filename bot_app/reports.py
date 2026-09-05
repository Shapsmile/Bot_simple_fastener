"""Отчеты о поступлении материалов в забой за выбранный период."""

from datetime import date, datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.common import clear_input_state, fmt_qty, show_input_error


async def show_report_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Экран выбора периода отчета.
    Показывает готовые периоды и ввод произвольного диапазона.
    """
    clear_input_state(context)
    excavation_name = context.user_data['current_excavation_name']
    today = date.today()

    keyboard = [
        [InlineKeyboardButton(f"📅 Сегодня ({today.strftime('%d.%m.%Y')})", callback_data="report_period_today")],
        [InlineKeyboardButton("🕐 За последние 7 дней", callback_data="report_period_7")],
        [InlineKeyboardButton("🗓️ За последние 30 дней", callback_data="report_period_30")],
        [InlineKeyboardButton("📆 За текущий месяц", callback_data="report_period_month")],
        [InlineKeyboardButton("✏️ Свой период (ДД.ММ.ГГГГ - ДД.ММ.ГГГГ)", callback_data="report_period_custom")],
        [InlineKeyboardButton("◀️ Назад в меню склада", callback_data="back_to_stock_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📊 Отчет о поступлении материалов в забой\n\n"
        f"Выберите период:",
        reply_markup=reply_markup
    )


async def handle_report_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает выбор готового периода и показывает отчёт.
    """
    query = update.callback_query
    data = query.data

    today = date.today()

    if data == "report_period_today":
        start_date, end_date = today, today
    elif data == "report_period_7":
        start_date, end_date = today - timedelta(days=6), today
    elif data == "report_period_30":
        start_date, end_date = today - timedelta(days=29), today
    else:  # report_period_month
        start_date = today.replace(day=1)
        end_date = today

    await show_supply_report(update, context, start_date, end_date)


async def ask_custom_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает произвольный период у пользователя.
    """
    clear_input_state(context)
    excavation_name = context.user_data['current_excavation_name']

    keyboard = [[InlineKeyboardButton("❌ Отменить ввод периода", callback_data="cancel_report_period")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    message = await query.edit_message_text(
        f"🏗️ {excavation_name}\n"
        f"📊 Введите период в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ:\n"
        f"Пример: 01.01.2026 - 05.09.2026\n\n"
        f"Или используйте кнопку ниже для отмены:",
        reply_markup=reply_markup
    )

    context.user_data['report_period_message_id'] = message.message_id


async def process_custom_period_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод произвольного периода.
    """
    try:
        text = update.message.text.strip()
        left, right = text.split('-', 1)
        start_date = datetime.strptime(left.strip(), '%d.%m.%Y').date()
        end_date = datetime.strptime(right.strip(), '%d.%m.%Y').date()

        if start_date > end_date:
            await show_input_error(
                update, context, 'report_period_message_id',
                "❌ Начальная дата позже конечной.\nВведите период снова (ДД.ММ.ГГГГ - ДД.ММ.ГГГГ):",
                "❌ Отменить ввод периода", "cancel_report_period"
            )
            return

        if end_date > date.today():
            await show_input_error(
                update, context, 'report_period_message_id',
                "❌ Конечная дата не может быть в будущем.\nВведите период снова:",
                "❌ Отменить ввод периода", "cancel_report_period"
            )
            return

        await update.message.delete()

        if 'report_period_message_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['report_period_message_id']
                )
            except ValueError:
                pass

        context.user_data.pop('report_period_message_id', None)

        await show_supply_report_from_message(update, context, start_date, end_date)

    except (ValueError, IndexError):
        await show_input_error(
            update, context, 'report_period_message_id',
            "❌ Неверный формат периода. Используйте ДД.ММ.ГГГГ - ДД.ММ.ГГГГ\n"
            "Пример: 01.01.2026 - 05.09.2026\n\nВведите период снова:",
            "❌ Отменить ввод периода", "cancel_report_period"
        )


async def show_supply_report(update: Update, context: ContextTypes.DEFAULT_TYPE, start_date: date, end_date: date):
    """
    Показывает сводный отчет по поступлениям за период.
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    report_data = bot_simple_bd_func.get_supply_report(
        excavation_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    )

    total_operations = sum(item['operations'] for item in report_data)

    text = (
        f"🏗️ {excavation_name}\n"
        f"📊 Отчет о поступлении материалов\n\n"
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"
        f"📥 Всего поступлений: {total_operations}\n"
    )

    if report_data:
        text += f"\n📦 По материалам:\n"
        for item in report_data:
            text += (
                f"• {item['name']}: {fmt_qty(item['total'])} {item['unit']} "
                f"(операций: {item['operations']})\n"
            )
    else:
        text += "\n📭 За выбранный период поступлений не было"

    keyboard = [
        [InlineKeyboardButton("📋 Детализация по дням", callback_data="report_details")],
        [InlineKeyboardButton("◀️ К выбору периода", callback_data="report_period_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


async def show_supply_report_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE, start_date: date, end_date: date):
    """
    Показывает отчет после ввода периода через сообщение (без промежуточных сообщений).
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    report_data = bot_simple_bd_func.get_supply_report(
        excavation_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    )

    total_operations = sum(item['operations'] for item in report_data)

    text = (
        f"🏗️ {excavation_name}\n"
        f"📊 Отчет о поступлении материалов\n\n"
        f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"
        f"📥 Всего поступлений: {total_operations}\n"
    )

    if report_data:
        text += f"\n📦 По материалам:\n"
        for item in report_data:
            text += (
                f"• {item['name']}: {fmt_qty(item['total'])} {item['unit']} "
                f"(операций: {item['operations']})\n"
            )
    else:
        text += "\n📭 За выбранный период поступлений не было"

    keyboard = [
        [InlineKeyboardButton("📋 Детализация по дням", callback_data="report_details")],
        [InlineKeyboardButton("◀️ К выбору периода", callback_data="report_period_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup
    )


async def show_report_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает детализацию поступлений по дням за выбранный период.
    """
    excavation_id = context.user_data['current_excavation_id']
    excavation_name = context.user_data['current_excavation_name']

    start_date = context.user_data.get('report_start_date')
    end_date = context.user_data.get('report_end_date')

    if not start_date or not end_date:
        await show_report_menu(update, context)
        return

    operations = bot_simple_bd_func.get_supply_operations(
        excavation_id, start_date, end_date
    )

    text = (
        f"🏗️ {excavation_name}\n"
        f"📋 Детализация поступлений\n\n"
        f"📅 Период: {datetime.strptime(start_date, '%Y-%m-%d').strftime('%d.%m.%Y')} - "
        f"{datetime.strptime(end_date, '%Y-%m-%d').strftime('%d.%m.%Y')}\n\n"
    )

    if operations:
        for op_date, quantity, name, unit in operations:
            text += f"• {op_date}: {fmt_qty(quantity)} {unit} — {name}\n"
    else:
        text += "📭 За выбранный период поступлений не было"

    keyboard = [
        [InlineKeyboardButton("◀️ К сводному отчету", callback_data="report_back_to_summary")],
        [InlineKeyboardButton("◀️ К выбору периода", callback_data="report_period_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)