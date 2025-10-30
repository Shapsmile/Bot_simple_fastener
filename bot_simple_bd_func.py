import sqlite3
from datetime import datetime


# Переменная базы данных
database = 'fastener_v3.db'

# ===== БАЗОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БД =====

def init_database():
    """
    Инициализация базы данных с новой архитектурой
    Ключевое изменение: нормы расхода теперь в паспорте выработки, а не в материалах
    """

    # Создаем соединение с базой данных.
    # Если файл database не существует - он будет создан автоматически
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # ТАБЛИЦА 1: Материалы (СПРАВОЧНИК)
    # Хранит только общую информацию о материалах, без привязки к выработкам
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID материала
            name TEXT NOT NULL,                    -- Название (Анкер АС-2, Сетка ОСС)
            unit TEXT NOT NULL                     -- Единица измерения (шт, м², кг)
        )
    ''')
    # КОММЕНТАРИЙ: Эта таблица теперь чисто справочная.
    # Она не знает о выработках и нормах расхода.

    # ТАБЛИЦА 2: Выработки (СПРАВОЧНИК)
    # Хранит список всех горных выработок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS excavations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID выработки
            name TEXT NOT NULL UNIQUE              -- Название выработки (Северная, Южная)
        )
    ''')
    # КОММЕНТАРИЙ: Каждая выработка - это отдельный объект учета
    # с собственными остатками и нормами расхода

    # ТАБЛИЦА 3: Паспорта крепления (СВЯЗУЮЩАЯ ТАБЛИЦА)
    # Связывает выработки с материалами и хранит нормы расхода
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS excavation_materials (
            excavation_id INTEGER NOT NULL,        -- ID выработки
            material_id INTEGER NOT NULL,          -- ID материала
            consumption_per_meter REAL NOT NULL,   -- Норма расхода на 1 метр проходки
            PRIMARY KEY (excavation_id, material_id),  -- Составной первичный ключ
            FOREIGN KEY (excavation_id) REFERENCES excavations (id),
            FOREIGN KEY (material_id) REFERENCES materials (id)
        )
    ''')
    # КОММЕНТАРИЙ: Это САМАЯ ВАЖНАЯ таблица в новой архитектуре!
    # Она определяет: "Какие материалы и в каком количестве используются в каждой выработке"
    # PRIMARY KEY (excavation_id, material_id) гарантирует, что
    # одна выработка не может иметь два одинаковых материала

    # ТАБЛИЦА 4: Приход материалов.
    # Фиксирует поступление материалов на КОНКРЕТНУЮ выработку
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supply (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID операции прихода
            excavation_id INTEGER NOT NULL,        -- ID выработки, куда поступили материалы
            material_id INTEGER NOT NULL,          -- ID материала
            quantity REAL NOT NULL,                -- Количество поступивших материалов
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Дата и время операции
            FOREIGN KEY (excavation_id) REFERENCES excavations (id),
            FOREIGN KEY (material_id) REFERENCES materials (id)
        )
    ''')
    # КОММЕНТАРИЙ: Теперь каждый приход привязан к конкретной выработке
    # Это позволяет вести раздельный учет остатков

    # ТАБЛИЦА 5: Проходка забоя.
    # Фиксирует продвижение КОНКРЕТНОЙ выработки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID операции проходки
            excavation_id INTEGER NOT NULL,        -- ID выработки, где была проходка
            meters REAL NOT NULL,                  -- Количество пройденных метров
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Дата и время операции
            FOREIGN KEY (excavation_id) REFERENCES excavations (id)
        )
    ''')
    # КОММЕНТАРИЙ: Проходка тоже привязана к выработке
    # При списании материалов будем использовать нормы из паспорта этой выработки

    # ЗАПОЛНЯЕМ ТЕСТОВЫЕ ДАННЫЕ

    # 1. Заполняем справочник материалов (БЕЗ норм расхода!)
    cursor.execute('''
        INSERT OR IGNORE INTO materials (id, name, unit) 
        VALUES 
        (1, 'Анкер АС-2', 'шт'),      -- Анкеры в штуках
        (2, 'Сетка ОСС', 'м²'),       -- Сетка в квадратных метрах  
        (3, 'Штанга талевая', 'шт')   -- Штанги в штуках
    ''')
    # КОММЕНТАРИЙ: Обратите внимание - нет поля consumption_per_meter!
    # Нормы будут задаваться для каждой выработки отдельно

    # 2. Заполняем справочник выработок
    cursor.execute('''
        INSERT OR IGNORE INTO excavations (id, name) 
        VALUES 
        (1, 'Северная'),  -- Выработка №1
        (2, 'Южная')      -- Выработка №2
    ''')

    # 3. Заполняем паспорта крепления (нормы расхода для каждой выработки)
    cursor.execute('''
        INSERT OR IGNORE INTO excavation_materials (excavation_id, material_id, consumption_per_meter) 
        VALUES 
        (1, 1, 10.0),   -- Северная выработка: Анкер 10 шт/метр
        (1, 2, 1.2),    -- Северная выработка: Сетка 1.2 м²/метр
        (2, 1, 15.0),   -- Южная выработка: Анкер 15 шт/метр (ДРУГАЯ НОРМА!)
        (2, 3, 8.0)     -- Южная выработка: Штанга 8 шт/метр
    ''')
    # КОММЕНТАРИЙ: Здесь видна разница в нормах!
    # В Северной выработке анкер 10 шт/м, в Южной - 15 шт/м
    # Также в Южной выработке используется штанга, которой нет в Северной

    # Сохраняем изменения и закрываем соединение
    conn.commit()
    conn.close()
    print("✅ База данных обновлена с новой архитектурой!")
    print("   - Материалы отделены от норм расхода")
    print("   - Нормы задаются в паспорте каждой выработки")
    print("   - Учет ведется раздельно по выработкам")


def user_system_database():
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # НОВАЯ ТАБЛИЦА: Авторизованные пользователи
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authorized_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'operator',
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            added_by INTEGER
        )
    ''')

    # Добавляем себя как администратора (замените на ваш user_id)
    cursor.execute('''
        INSERT OR IGNORE INTO authorized_users (user_id, username, full_name, role) 
        VALUES (?, ?, ?, ?)
    ''', ('440447786', 'Shapsmile', 'Аркадий Шапошников', 'Admin'))

    conn.commit()
    conn.close()
    print("✅ База данных обновлена с системой пользователей!")


def get_excavations_list():
    """
    Получаем список всех выработок из БД
    Возвращает: список кортежей [(id, name), ...]
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM excavations")
    excavations = cursor.fetchall()
    conn.close()
    return excavations


def get_excavation_name(excavation_id):
    """
    Получаем название выработки по ID
    Возвращает: строку с названием выработки
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM excavations WHERE id = ?", (excavation_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "Неизвестная выработка"


def get_current_stock(excavation_id):
    """ИСПРАВЛЕННАЯ версия расчета остатков"""
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            m.name, 
            m.unit,
            -- Приход: сумма quantity из supply для этой выработки
            COALESCE((
                SELECT SUM(quantity) 
                FROM supply 
                WHERE material_id = m.id AND excavation_id = ?
            ), 0) as total_supply,
            -- Расход: сумма (метры * норма) из advance для этой выработки
            COALESCE((
                SELECT SUM(a.meters * em.consumption_per_meter)
                FROM advance a
                JOIN excavation_materials em ON a.excavation_id = em.excavation_id
                WHERE em.material_id = m.id AND a.excavation_id = ?
            ), 0) as total_consumption
        FROM materials m
        JOIN excavation_materials em ON m.id = em.material_id
        WHERE em.excavation_id = ?
    ''', (excavation_id, excavation_id, excavation_id))

    stock_data = []
    for name, unit, total_supply, total_consumption in cursor.fetchall():
        stock_data.append({
            'name': name,
            'quantity': total_supply - total_consumption,
            'unit': unit
        })

    conn.close()
    return stock_data


def get_excavation_materials(excavation_id):
    """
    Получаем список материалов из паспорта крепления выработки
    Возвращает: список материалов с ID, названием и единицами измерения
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.id, m.name, m.unit
        FROM materials m
        JOIN excavation_materials em ON m.id = em.material_id
        WHERE em.excavation_id = ?
    ''', (excavation_id,))
    materials = cursor.fetchall()
    conn.close()
    return materials


def add_material_to_stock(excavation_id, material_id, quantity):
    """
    Добавляет приход материала на склад выработки.
    Сохраняет операцию в таблицу supply
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO supply (excavation_id, material_id, quantity) VALUES (?, ?, ?)",
        (excavation_id, material_id, quantity)
    )
    conn.commit()
    conn.close()


def add_advance_to_db(excavation_id, meters, shift_number, work_date, replace_existing=False):
    """
    Добавляет или обновляет запись о проходке в базе данных
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    if replace_existing:
        # Удаляем существующие записи для этой смены
        cursor.execute(
            "DELETE FROM advance WHERE excavation_id = ? AND work_date = ? AND shift_number = ?",
            (excavation_id, work_date, shift_number)
        )

    # Добавляем новую запись
    cursor.execute(
        "INSERT INTO advance (excavation_id, meters, shift_number, work_date) VALUES (?, ?, ?, ?)",
        (excavation_id, meters, shift_number, work_date)
    )

    conn.commit()
    conn.close()


def calculate_consumption(excavation_id, meters):
    """
    Рассчитывает списание материалов по нормам расхода.
    Возвращает список списанных материалов для отчета
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # Получаем материалы и нормы расхода для выработки
    cursor.execute('''
        SELECT m.name, m.unit, em.consumption_per_meter
        FROM materials m
        JOIN excavation_materials em ON m.id = em.material_id
        WHERE em.excavation_id = ?
    ''', (excavation_id,))

    consumption_data = []
    for name, unit, consumption_rate in cursor.fetchall():
        consumed = meters * consumption_rate
        consumption_data.append({
            'name': name,
            'consumed': consumed,
            'unit': unit
        })

    conn.close()
    return consumption_data


def get_advance_history(excavation_id, period_days=30):
    """
    Получает историю проходки за период.
    Возвращает данные с группировкой по дням и сменам
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # Получаем проходку за указанный период
    cursor.execute('''
        SELECT 
            date(work_date) as day,
            shift_number,
            SUM(meters) as total_meters
        FROM advance 
        WHERE excavation_id = ? 
          AND work_date >= date('now', ?)
        GROUP BY date(work_date), shift_number
        ORDER BY day DESC, shift_number
    ''', (excavation_id, f'-{period_days} days'))

    # Группируем по дням
    daily_data = {}
    for day_str, shift, meters in cursor.fetchall():
        # Конвертируем строку в date объект
        day = datetime.strptime(day_str, '%Y-%m-%d').date()

        if day not in daily_data:
            daily_data[day] = {'total': 0, 'shifts': {1: 0, 2: 0, 3: 0}}

        daily_data[day]['shifts'][shift] = meters
        daily_data[day]['total'] += meters

    conn.close()
    return daily_data


def get_monthly_total(excavation_id):
    """
    Получает общую проходку с начала текущего месяца
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT SUM(meters) 
        FROM advance 
        WHERE excavation_id = ? 
          AND work_date >= date('now', 'start of month')
    ''', (excavation_id,))

    result = cursor.fetchone()
    conn.close()
    return result[0] or 0


def get_existing_advance(excavation_id, work_date, shift_number):
    """
    Проверяет есть ли уже учтенная проходка для данной выработки, даты и смены.
    Возвращает количество метров если есть, иначе None
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT SUM(meters) 
        FROM advance 
        WHERE excavation_id = ? 
          AND work_date = ? 
          AND shift_number = ?
    ''', (excavation_id, work_date, shift_number))

    result = cursor.fetchone()
    conn.close()

    existing_meters = result[0] if result and result[0] else None
    return existing_meters


def delete_advance_from_db(excavation_id, work_date, shift_number):
    """
    Полностью удаляет запись о проходке из базы данных
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM advance WHERE excavation_id = ? AND work_date = ? AND shift_number = ?",
        (excavation_id, work_date, shift_number)
    )

    conn.commit()
    conn.close()


def get_excavation_passport(excavation_id):
    """
    Получает паспорт крепления выработки.
    Возвращает список материалов с нормами расхода
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT m.id, m.name, m.unit, em.consumption_per_meter
        FROM materials m
        JOIN excavation_materials em ON m.id = em.material_id
        WHERE em.excavation_id = ?
        ORDER BY m.name
    ''', (excavation_id,))

    passport_data = []
    for material_id, name, unit, consumption in cursor.fetchall():
        passport_data.append({
            'material_id': material_id,
            'name': name,
            'unit': unit,
            'consumption_per_meter': consumption
        })

    conn.close()
    return passport_data


def update_passport_consumption(excavation_id, material_id, new_consumption):
    """
    Обновляет норму расхода материала в паспорте крепления
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE excavation_materials 
        SET consumption_per_meter = ?
        WHERE excavation_id = ? AND material_id = ?
    ''', (new_consumption, excavation_id, material_id))

    conn.commit()
    conn.close()


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ =====

def is_user_authorized(user_id):
    """
    Проверяет есть ли пользователь в белом списке
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM authorized_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    return result is not None


def get_user_role(user_id):
    """
    Получает роль пользователя
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('SELECT role FROM authorized_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def get_authorized_users():
    """
    Получает список всех авторизованных пользователей
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, username, full_name, role, added_date 
        FROM authorized_users 
        ORDER BY role, full_name
    ''')
    users = cursor.fetchall()
    conn.close()
    return users


def add_authorized_user(user_id, username, full_name, role='operator', added_by=None):
    """
    Добавляет пользователя в белый список
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO authorized_users (user_id, username, full_name, role, added_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, full_name, role, added_by))

    conn.commit()
    conn.close()


def remove_authorized_user(user_id):
    """
    Удаляет пользователя из белого списка
    С защитой от удаления последнего администратора
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    # Проверяем не удаляем ли мы последнего администратора
    cursor.execute('SELECT COUNT(*) FROM authorized_users WHERE role = "admin"')
    admin_count = cursor.fetchone()[0]

    cursor.execute('SELECT role FROM authorized_users WHERE user_id = ?', (user_id,))
    user_role = cursor.fetchone()

    if user_role and user_role[0] == 'admin' and admin_count <= 1:
        conn.close()
        raise Exception("Нельзя удалить последнего администратора!")

    # Удаляем пользователя
    cursor.execute('DELETE FROM authorized_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def get_user_info(user_id):
    """
    Получает полную информацию о пользователе по ID
    """
    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, username, full_name, role, added_date 
        FROM authorized_users 
        WHERE user_id = ?
    ''', (user_id,))

    result = cursor.fetchone()
    conn.close()
    return result
