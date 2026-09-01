"""Управление забоями (выработками): добавление нового забоя (только для админов)."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.common import clear_input_state
from bot_app.screens import show_global_settings


async def show_excavation_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Запрашивает название нового забоя (только для админов)
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
        "➕ Добавление нового забоя\n\n"
        "Отправьте название забоя одним сообщением.\n\n"
        "Пример:\n"
        "`Вентиляционный бремсберг пл. 15`",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    context.user_data['excavation_add_message_id'] = message.message_id


async def process_excavation_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ввод названия нового забоя
    """
    try:
        text = update.message.text.strip()

        print(f"🔍 Обрабатываем название забоя: '{text}'")

        if not text:
            raise ValueError("Название не может быть пустым")

        # Удаляем сообщение администратора
        await update.message.delete()

        # Добавляем забой в базу
        success, exc_id = bot_simple_bd_func.add_excavation(text)

        if success:
            success_text = (
                f"✅ Забой успешно добавлен!\n\n"
                f"🏗️ {text}\n"
                f"🆔 ID: {exc_id}\n\n"
                f"Теперь он доступен в списке забоев."
            )
        else:
            success_text = (
                f"❌ Не удалось добавить забой.\n\n"
                f"Забой с названием «{text}» уже существует."
            )

        if 'excavation_add_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['excavation_add_message_id'],
                text=success_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ В настройки", callback_data="back_to_settings")
                ]])
            )

    except Exception as e:
        print(f"❌ Ошибка при добавлении забоя: {e}")
        await update.message.delete()

        error_text = f"❌ Ошибка: {str(e)}"

        if 'excavation_add_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['excavation_add_message_id'],
                text=error_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отменить", callback_data="back_to_settings")
                ]])
            )

    finally:
        # Всегда очищаем ключ, чтобы он не перехватывал последующий ввод
        context.user_data.pop('excavation_add_message_id', None)


async def show_excavation_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает список забоев для удаления (только для админов)
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if bot_simple_bd_func.get_user_role(user_id) != 'admin':
        await query.answer("🚫 Недостаточно прав!", show_alert=True)
        return

    excavations = bot_simple_bd_func.get_excavations_list()

    if not excavations:
        text = "📭 Нет забоев для удаления."
        keyboard = [[InlineKeyboardButton("◀️ Назад в настройки", callback_data="back_to_settings")]]
    else:
        text = "🗑️ Выберите забой для удаления:\n\n"
        keyboard = []
        for exc_id, name in excavations:
            keyboard.append([InlineKeyboardButton("⚒️ " + name, callback_data=f"remove_exc_{exc_id}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад в настройки", callback_data="back_to_settings")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)


async def show_excavation_remove_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, excavation_id: int):
    """
    Подтверждение удаления забоя (только для админов)
    """
    excavation_name = bot_simple_bd_func.get_excavation_name(excavation_id)

    context.user_data['excavation_to_remove'] = excavation_id

    text = (
        f"🗑️ Подтверждение удаления\n\n"
        f"🏗️ Забой: {excavation_name}\n"
        f"🆔 ID: {excavation_id}\n\n"
        f"⚠️ Будут удалены:\n"
        f"• Паспорт крепления забоя\n"
        f"• Все приходы материалов\n"
        f"• Вся история проведения выработки\n\n"
        f"Это действие необратимо. Продолжить?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_remove_excavation")],
        [InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_remove_excavation")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)


async def process_excavation_removal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает подтверждение удаления забоя
    """
    excavation_id = context.user_data.get('excavation_to_remove')

    if not excavation_id:
        await update.callback_query.answer("❌ Ошибка: данные забоя не найдены!", show_alert=True)
        return

    excavation_name = bot_simple_bd_func.get_excavation_name(excavation_id)
    success = bot_simple_bd_func.delete_excavation(excavation_id)

    context.user_data.pop('excavation_to_remove', None)

    if success:
        text = (
            f"✅ Забой успешно удален!\n\n"
            f"🏗️ {excavation_name}\n"
            f"🗑️ Забой больше не доступен в списке."
        )
    else:
        text = f"❌ Не удалось удалить забой: {excavation_name}"

    keyboard = [[InlineKeyboardButton("◀️ В настройки", callback_data="back_to_settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    await query.edit_message_text(text, reply_markup=reply_markup)

    # Логируем действие
    admin_id = update.effective_user.id
    admin_name = update.effective_user.full_name
    print(f"👮 Администратор {admin_name} (ID: {admin_id}) удалил забой {excavation_name} (ID: {excavation_id})")