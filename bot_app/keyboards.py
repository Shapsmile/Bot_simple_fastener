"""Общие клавиатуры (DRY)."""

from telegram import InlineKeyboardButton

import bot_simple_bd_func


def excavation_selection_keyboard():
    """Клавиатура выбора выработки (используется в start и start_from_button)"""
    excavations = bot_simple_bd_func.get_excavations_list()
    keyboard = []
    for exc_id, name in excavations:
        keyboard.append([InlineKeyboardButton("⚒️ " + name, callback_data=f"exc_{exc_id}")])
    keyboard.append([InlineKeyboardButton("⚙️ Настройки", callback_data="global_settings")])
    return keyboard


def stock_menu_keyboard():
    """Клавиатура меню склада"""
    return [
        [InlineKeyboardButton("📊 Просмотр остатков", callback_data="stock_view")],
        [InlineKeyboardButton("📈 Отчет по поступлениям", callback_data="report_menu")],
        [InlineKeyboardButton("➕ Пополнение материалов", callback_data="stock_add")],
        [InlineKeyboardButton("◀️ Назад в главное меню", callback_data="back_to_excavation_menu")]
    ]


def advance_menu_keyboard():
    """Клавиатура меню проходки"""
    return [
        [InlineKeyboardButton("✅ Ввести уход", callback_data="advance_add")],
        [InlineKeyboardButton("📋 История проведения", callback_data="advance_history")],
        [InlineKeyboardButton("◀️ Назад в главное меню", callback_data="back_to_excavation_menu")]
    ]


def passport_edit_keyboard(passport_data):
    """Клавиатура выбора материала для редактирования паспорта"""
    keyboard = []
    for item in passport_data:
        button_text = f"{item['name']}: {item['consumption_per_meter']} {item['unit']}/м"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_mat_{item['material_id']}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад в меню паспорта", callback_data="back_to_passport_menu")])
    return keyboard
