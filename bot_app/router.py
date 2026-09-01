"""Диспетчеры: маршрутизация нажатий на кнопки и текстового ввода."""

from telegram import Update
from telegram.ext import ContextTypes

import bot_simple_bd_func
from bot_app.advance import (
    ask_additional_meters,
    ask_meters_input,
    handle_date_selection,
    handle_shift_selection,
    process_custom_date_input,
    process_meters_input,
    show_date_selection,
    show_delete_confirmation,
    show_delete_success,
    show_replace_warning,
    show_shift_selection,
)
from bot_app.common import check_access, clear_input_state
from bot_app.config import pending_users
from bot_app.excavations import (
    process_excavation_name,
    process_excavation_removal,
    show_excavation_add,
    show_excavation_remove,
    show_excavation_remove_confirmation,
)
from bot_app.history import show_advance_history, show_day_detail, show_filtered_history
from bot_app.materials import (
    ask_passport_consumption,
    process_material_name,
    process_passport_consumption,
    show_material_add,
    show_passport_material_selection,
)
from bot_app.passport import (
    ask_new_consumption,
    ask_password_for_edit,
    process_new_consumption,
    process_password_input,
    show_passport_edit,
    show_passport_menu,
    show_passport_view,
)
from bot_app.screens import (
    show_advance_menu,
    show_excavation_menu,
    show_global_settings,
    show_stock_menu,
    show_stock_view,
    show_user_profile,
    start_from_button,
)
from bot_app.stock import (
    ask_quantity,
    cancel_add_material,
    process_quantity_input,
    show_material_selection,
    show_stock_add,
)
from bot_app.users import (
    ask_user_details,
    process_new_user,
    process_user_removal,
    show_remove_confirmation,
    show_user_management,
    show_users_for_removal,
    show_users_list,
)


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
        clear_input_state(context)  # Сбрасываем любые состояния ввода
        excavation_id = context.user_data['current_excavation_id']
        await show_excavation_menu(update, context, excavation_id)
    elif data == "back_to_excavations":
        # Возврат к выбору выработки
        clear_input_state(context)  # Сбрасываем любые состояния ввода
        await start_from_button(update, context)
    elif data == "back_to_stock_menu":
        # Возврат в меню склада
        clear_input_state(context)  # Сбрасываем любые состояния ввода
        await show_stock_menu(update, context)
    elif data == "back_to_advance_menu":
        # Возврат в меню проходки
        clear_input_state(context)  # Сбрасываем любые состояния ввода
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
        clear_input_state(context)  # Сбрасываем любые состояния ввода
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
        clear_input_state(context)  # Сбрасываем состояния ввода
        await show_date_selection(update, context)
    elif data == "cancel_date_input":
        clear_input_state(context)  # Сбрасываем состояния ввода
        await show_date_selection(update, context)
    elif data == "cancel_meters_input":
        clear_input_state(context)  # Сбрасываем состояния ввода
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
        # Сохраняем ID сообщения для редактирования "одно окно"
        consumption_message_id = context.user_data.pop('consumption_edit_message_id', None)
        # Сбрасываем любые состояния ввода и флаги редактирования
        clear_input_state(context)
        context.user_data.pop('passport_edit_authorized', None)
        context.user_data.pop('editing_material_id', None)
        context.user_data.pop('editing_material_name', None)
        context.user_data.pop('editing_material_unit', None)
        context.user_data.pop('current_consumption', None)
        await show_passport_edit(update, context, message_id=consumption_message_id)

    # Обработка навигации в паспорте
    elif data == "back_to_passport_menu":
        # Очищаем флаг авторизации при возврате
        context.user_data.pop('passport_edit_authorized', None)
        clear_input_state(context)  # Сбрасываем любые состояния ввода
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
        clear_input_state(context)  # Сбрасываем любые состояния ввода
        await show_user_management(update, context)

    # Обработка удаления пользователей
    elif data.startswith("remove_user_"):
        user_id = int(data.replace("remove_user_", ""))
        await show_remove_confirmation(update, context, user_id)
    elif data == "confirm_remove":
        await process_user_removal(update, context)
    elif data == "cancel_remove":
        await show_users_for_removal(update, context)

    # Обработка глобальных настроек
    elif data == "global_settings":
        await show_global_settings(update, context)
    elif data == "back_to_settings":
        clear_input_state(context)  # Сбрасываем любые состояния ввода
        await show_global_settings(update, context)
    elif data == "user_profile":
        await show_user_profile(update, context)

    # Обработка добавления забоя
    elif data == "excavation_add":
        await show_excavation_add(update, context)
    elif data == "excavation_remove":
        await show_excavation_remove(update, context)
    elif data.startswith("remove_exc_"):
        excavation_id = int(data.replace("remove_exc_", ""))
        await show_excavation_remove_confirmation(update, context, excavation_id)
    elif data == "confirm_remove_excavation":
        await process_excavation_removal(update, context)
    elif data == "cancel_remove_excavation":
        await show_excavation_remove(update, context)

    # Обработка материалов
    elif data == "material_add":
        await show_material_add(update, context)
    elif data == "passport_add_material":
        await show_passport_material_selection(update, context)
    elif data.startswith("passport_add_mat_"):
        material_id = int(data.replace("passport_add_mat_", ""))
        await ask_passport_consumption(update, context, material_id)


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

    # 6.3 Если пользователь вводит норму расхода для добавления в паспорт
    # (проверяем ДО создания забоя/материала, чтобы активный ввод паспорта
    #  не перехватывался застрявшими ключами)
    elif 'passport_consumption_message_id' in context.user_data:
        print("🎯 Направляем в обработку нормы расхода для паспорта")
        await process_passport_consumption(update, context)

    # 6.1 Если пользователь вводит название нового забоя
    elif 'excavation_add_message_id' in context.user_data:
        print("🎯 Направляем в обработку названия забоя")
        await process_excavation_name(update, context)

    # 6.2 Если пользователь вводит данные нового материала
    elif 'material_add_message_id' in context.user_data:
        print("🎯 Направляем в обработку данных материала")
        await process_material_name(update, context)

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


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает все текстовые сообщения: проверяет доступ,
    авторизацию и направляет в соответствующий обработчик
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
