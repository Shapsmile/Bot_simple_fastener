import os
import sqlite3
from datetime import datetime


# Путь к данным.
# На Railway задаётся переменная DATA_DIR, указывающая на Volume
# (например, /app/data). Локально база создаётся в папке проекта.
data_dir = os.environ.get('DATA_DIR', '')
database = os.path.join(data_dir, 'fastener_v3.db') if data_dir else 'fastener_v3.db'


# ===== ОБЩИЙ ХЕЛПЕР ДЛЯ РАБОТЫ С БД (DRY) =====

class DatabaseConnection:
    """Контекстный менеджер соединения с БД. Автоматически закрывает соединение."""
    def __init__(self, commit=False):
        self.commit = commit
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(database)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.commit and exc_type is None:
            self.conn.commit()
        self.conn.close()
        return False


# ===== БАЗОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С БД =====

def init_database():
    """
    Инициализация базы данных с новой архитектурой
    Ключевое изменение: нормы расхода теперь в паспорте выработки, а не в материалах
    """

    # Если база лежит в DATA_DIR (Volume) - убеждаемся, что папка существует
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

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
            shift_number INTEGER NOT NULL DEFAULT 1, -- Номер смены (1, 2, 3)
            work_date DATE NOT NULL,               -- Дата выполнения работ
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Дата и время операции
            FOREIGN KEY (excavation_id) REFERENCES excavations (id)
        )
    ''')

    # МИГРАЦИЯ: старые базы могли быть созданы без колонок shift_number и work_date.
    # CREATE TABLE IF NOT EXISTS не меняет существующую таблицу, поэтому добавляем
    # недостающие колонки вручную, если их нет.
    try:
        cursor.execute("PRAGMA table_info(advance)")
        advance_cols = {row[1] for row in cursor.fetchall()}
        if 'shift_number' not in advance_cols:
            cursor.execute("ALTER TABLE advance ADD COLUMN shift_number INTEGER NOT NULL DEFAULT 1")
            print("   - Добавлена колонка shift_number в таблицу advance")
        if 'work_date' not in advance_cols:
            cursor.execute("ALTER TABLE advance ADD COLUMN work_date DATE")
            print("   - Добавлена колонка work_date в таблицу advance")
    except Exception as e:
        print(f"⚠️ Не удалось проверить/дополнить таблицу advance: {e}")

    # ЗАПОЛНЯЕМ РЕАЛЬНЫЕ ДАННЫЕ (перенесены из локальной fastener_v3.db)

    # 1. Удаляем старые демо-данные, если база была создана старым кодом
    cursor.execute("DELETE FROM supply WHERE excavation_id IN (SELECT id FROM excavations WHERE name IN ('Северная', 'Южная'))")
    cursor.execute("DELETE FROM advance WHERE excavation_id IN (SELECT id FROM excavations WHERE name IN ('Северная', 'Южная'))")
    cursor.execute("DELETE FROM excavation_materials WHERE excavation_id IN (SELECT id FROM excavations WHERE name IN ('Северная', 'Южная'))")
    cursor.execute("DELETE FROM excavations WHERE name IN ('Северная', 'Южная')")

    cursor.execute("DELETE FROM supply WHERE material_id IN (SELECT id FROM materials WHERE name IN ('Анкер АС-2', 'Сетка ОСС', 'Штанга талевая'))")
    cursor.execute("DELETE FROM excavation_materials WHERE material_id IN (SELECT id FROM materials WHERE name IN ('Анкер АС-2', 'Сетка ОСС', 'Штанга талевая'))")
    cursor.execute("DELETE FROM materials WHERE name IN ('Анкер АС-2', 'Сетка ОСС', 'Штанга талевая')")

    # 2. Справочник материалов (реальные данные)
    cursor.execute('''
        INSERT OR IGNORE INTO materials (id, name, unit) 
        VALUES 
        (1, 'Анкер АВ-20-2900 мм', 'шт'),
        (2, 'Анкер АС-18-2600 мм', 'шт'),
        (3, 'Решетка 100х100 мм', 'шт'),
        (4, 'Решетка 50х50 мм', 'шт'),
        (5, 'Анкер АК-01-7000 мм', 'шт'),
        (6, 'Ампула 1200 мм', 'шт'),
        (7, 'Анкер АН20В 2600 мм', 'шт'),
        (8, 'Анкер АН20В 1800 мм', 'шт'),
        (9, 'Анкер стеклопласт 1800 мм', 'шт'),
        (10, 'Шайба стеклопласт', 'шт'),
        (11, 'Шайба 250х250', 'шт'),
        (12, 'Шайба 100х100', 'шт')
    ''')

    # 3. Справочник выработок
    cursor.execute('''
        INSERT OR IGNORE INTO excavations (id, name) 
        VALUES 
        (5, 'Вентиляционный бремсберг пл. 15'),
        (7, 'Вентиляционный штрек 15-17')
    ''')

    # 4. Паспорта крепления (нормы расхода для каждой выработки)
    cursor.execute('''
        INSERT OR IGNORE INTO excavation_materials (excavation_id, material_id, consumption_per_meter) 
        VALUES 
        (5, 3, 2.0),
        (5, 7, 6.0),
        (7, 3, 4.0),
        (7, 6, 12.0),
        (7, 7, 6.0),
        (7, 8, 3.0),
        (7, 9, 3.0),
        (7, 10, 3.0),
        (7, 11, 9.0),
        (7, 12, 6.0)
    ''')

    # 5. Остатки на складе (приходы на забой 7)
    cursor.execute('''
        INSERT OR IGNORE INTO supply (excavation_id, material_id, quantity)
        VALUES 
        (7, 3, 50.0),
        (7, 6, 140.0),
        (7, 7, 100.0),
        (7, 8, 100.0),
        (7, 9, 100.0),
        (7, 10, 100.0),
        (7, 11, 200.0),
        (7, 12, 100.0)
    ''')

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
    ''', ('440447786', 'Shapsmile', 'Аркадий Шапошников', 'admin'))

    # Добавляем оператора
    cursor.execute('''
        INSERT OR IGNORE INTO authorized_users (user_id, username, full_name, role) 
        VALUES (?, ?, ?, ?)
    ''', ('1034243680', 'Shaposhnikova_hello', 'Шапошникова Анастасия', 'operator'))

    # Нормализуем роли: в старых базах админ мог быть записан как 'Admin'
    cursor.execute("UPDATE authorized_users SET role = LOWER(role)")

    conn.commit()
    conn.close()
    print("✅ База данных обновлена с системой пользователей!")


def get_excavations_list():
    """
    Получаем список всех выработок из БД
    Возвращает: список кортежей [(id, name), ...]
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM excavations")
        return cursor.fetchall()


def add_excavation(name):
    """
    Добавляет новую выработку (забой) в справочник.
    Возвращает: (True, id) при успехе, (False, None) если такая уже существует.
    """
    name = name.strip()
    if not name:
        return False, None

    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()
        # Проверяем, нет ли уже такой выработки (без учета регистра)
        cursor.execute("SELECT id FROM excavations WHERE LOWER(name) = LOWER(?)", (name,))
        if cursor.fetchone():
            return False, None
        cursor.execute("INSERT INTO excavations (name) VALUES (?)", (name,))
        return True, cursor.lastrowid


def delete_excavation(excavation_id):
    """
    Удаляет выработку (забой) и все связанные данные:
    паспорт крепления, приходы материалов, записи проходки.
    Возвращает True при успехе, False если выработка не найдена.
    """
    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()
        # Проверяем, что выработка существует
        cursor.execute("SELECT id FROM excavations WHERE id = ?", (excavation_id,))
        if not cursor.fetchone():
            return False
        # Удаляем связанные данные (внешние ключи не включены, чистим вручную)
        cursor.execute("DELETE FROM advance WHERE excavation_id = ?", (excavation_id,))
        cursor.execute("DELETE FROM supply WHERE excavation_id = ?", (excavation_id,))
        cursor.execute("DELETE FROM excavation_materials WHERE excavation_id = ?", (excavation_id,))
        cursor.execute("DELETE FROM excavations WHERE id = ?", (excavation_id,))
        return True


def get_excavation_name(excavation_id):
    """
    Получаем название выработки по ID
    Возвращает: строку с названием выработки
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM excavations WHERE id = ?", (excavation_id,))
        result = cursor.fetchone()
        return result[0] if result else "Неизвестная выработка"


def get_current_stock(excavation_id):
    """ИСПРАВЛЕННАЯ версия расчета остатков"""
    with DatabaseConnection() as conn:
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

        return stock_data


def get_excavation_materials(excavation_id):
    """
    Получаем список материалов из паспорта крепления выработки
    Возвращает: список материалов с ID, названием и единицами измерения
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.id, m.name, m.unit
            FROM materials m
            JOIN excavation_materials em ON m.id = em.material_id
            WHERE em.excavation_id = ?
        ''', (excavation_id,))
        return cursor.fetchall()


def add_material(name, unit):
    """
    Добавляет новый материал в справочник.
    Возвращает: (True, id) при успехе, (False, None) если такой уже существует.
    """
    name = name.strip()
    unit = unit.strip()
    if not name or not unit:
        return False, None

    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM materials WHERE LOWER(name) = LOWER(?)", (name,))
        if cursor.fetchone():
            return False, None
        cursor.execute("INSERT INTO materials (name, unit) VALUES (?, ?)", (name, unit))
        return True, cursor.lastrowid


def get_all_materials():
    """
    Получает список всех материалов из справочника.
    Возвращает: список кортежей [(id, name, unit), ...]
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, unit FROM materials ORDER BY name")
        return cursor.fetchall()


def add_material_to_passport(excavation_id, material_id, consumption_per_meter):
    """
    Добавляет материал в паспорт крепления забоя с нормой расхода.
    Возвращает: True при успехе, False если материал уже есть в паспорте.
    """
    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM excavation_materials WHERE excavation_id = ? AND material_id = ?",
            (excavation_id, material_id)
        )
        if cursor.fetchone():
            return False
        cursor.execute(
            "INSERT INTO excavation_materials (excavation_id, material_id, consumption_per_meter) VALUES (?, ?, ?)",
            (excavation_id, material_id, consumption_per_meter)
        )
        return True


def get_material_info(material_id):
    """
    Получает название и единицу измерения материала по ID
    Возвращает: кортеж (name, unit) или None
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, unit FROM materials WHERE id = ?", (material_id,))
        return cursor.fetchone()


def get_consumption_rate(excavation_id, material_id):
    """
    Получает норму расхода материала в паспорте выработки
    Возвращает: значение consumption_per_meter или None
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT consumption_per_meter 
            FROM excavation_materials 
            WHERE excavation_id = ? AND material_id = ?
        ''', (excavation_id, material_id))
        result = cursor.fetchone()
        return result[0] if result else None


def add_material_to_stock(excavation_id, material_id, quantity):
    """
    Добавляет приход материала на склад выработки.
    Сохраняет операцию в таблицу supply
    """
    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO supply (excavation_id, material_id, quantity) VALUES (?, ?, ?)",
            (excavation_id, material_id, quantity)
        )


def get_supply_report(excavation_id, start_date, end_date):
    """
    Отчет о поступлении материалов за период (сводка по материалам).
    start_date/end_date - строки 'YYYY-MM-DD' (включительно).
    Возвращает список словарей: name, unit, operations, total
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.name, m.unit, COUNT(s.id), SUM(s.quantity)
            FROM supply s
            JOIN materials m ON s.material_id = m.id
            WHERE s.excavation_id = ?
              AND date(s.date) >= date(?)
              AND date(s.date) <= date(?)
            GROUP BY m.id
            ORDER BY m.name
        ''', (excavation_id, start_date, end_date))

        report = []
        for name, unit, operations, total in cursor.fetchall():
            report.append({
                'name': name,
                'unit': unit,
                'operations': operations,
                'total': total or 0
            })
        return report


def get_supply_operations(excavation_id, start_date, end_date):
    """
    Детализация поступлений материалов по датам за период.
    Возвращает список кортежей: (date, quantity, name, unit)
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date(s.date), s.quantity, m.name, m.unit
            FROM supply s
            JOIN materials m ON s.material_id = m.id
            WHERE s.excavation_id = ?
              AND date(s.date) >= date(?)
              AND date(s.date) <= date(?)
            ORDER BY s.date DESC, m.name
        ''', (excavation_id, start_date, end_date))
        return cursor.fetchall()


def add_advance_to_db(excavation_id, meters, shift_number, work_date, replace_existing=False):
    """
    Добавляет или обновляет запись о проходке в базе данных
    """
    with DatabaseConnection(commit=True) as conn:
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


def calculate_consumption(excavation_id, meters):
    """
    Рассчитывает списание материалов по нормам расхода.
    Возвращает список списанных материалов для отчета
    """
    with DatabaseConnection() as conn:
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

        return consumption_data


def get_advance_history(excavation_id, period_days=30):
    """
    Получает историю проходки за период.
    Возвращает данные с группировкой по дням и сменам
    """
    with DatabaseConnection() as conn:
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

        return daily_data


def get_monthly_total(excavation_id):
    """
    Получает общую проходку с начала текущего месяца
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT SUM(meters) 
            FROM advance 
            WHERE excavation_id = ? 
              AND work_date >= date('now', 'start of month')
        ''', (excavation_id,))

        result = cursor.fetchone()
        return result[0] or 0


def get_existing_advance(excavation_id, work_date, shift_number):
    """
    Проверяет есть ли уже учтенная проходка для данной выработки, даты и смены.
    Возвращает количество метров если есть, иначе None
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT SUM(meters) 
            FROM advance 
            WHERE excavation_id = ? 
              AND work_date = ? 
              AND shift_number = ?
        ''', (excavation_id, work_date, shift_number))

        result = cursor.fetchone()

        existing_meters = result[0] if result and result[0] else None
        return existing_meters


def delete_advance_from_db(excavation_id, work_date, shift_number):
    """
    Полностью удаляет запись о проходке из базы данных
    """
    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM advance WHERE excavation_id = ? AND work_date = ? AND shift_number = ?",
            (excavation_id, work_date, shift_number)
        )


def get_excavation_passport(excavation_id):
    """
    Получает паспорт крепления выработки.
    Возвращает список материалов с нормами расхода
    """
    with DatabaseConnection() as conn:
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

        return passport_data


def update_passport_consumption(excavation_id, material_id, new_consumption):
    """
    Обновляет норму расхода материала в паспорте крепления
    """
    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE excavation_materials 
            SET consumption_per_meter = ?
            WHERE excavation_id = ? AND material_id = ?
        ''', (new_consumption, excavation_id, material_id))


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ =====

def is_user_authorized(user_id):
    """
    Проверяет есть ли пользователь в белом списке
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT user_id FROM authorized_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        return result is not None


def get_user_role(user_id):
    """
    Получает роль пользователя
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT role FROM authorized_users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        return result[0] if result else None


def get_authorized_users():
    """
    Получает список всех авторизованных пользователей
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_id, username, full_name, role, added_date 
            FROM authorized_users 
            ORDER BY role, full_name
        ''')
        return cursor.fetchall()


def add_authorized_user(user_id, username, full_name, role='operator', added_by=None):
    """
    Добавляет пользователя в белый список
    """
    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO authorized_users (user_id, username, full_name, role, added_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, full_name, role, added_by))


def remove_authorized_user(user_id):
    """
    Удаляет пользователя из белого списка
    С защитой от удаления последнего администратора
    """
    with DatabaseConnection(commit=True) as conn:
        cursor = conn.cursor()

        # Проверяем не удаляем ли мы последнего администратора
        cursor.execute('SELECT COUNT(*) FROM authorized_users WHERE role = "admin"')
        admin_count = cursor.fetchone()[0]

        cursor.execute('SELECT role FROM authorized_users WHERE user_id = ?', (user_id,))
        user_role = cursor.fetchone()

        if user_role and user_role[0] == 'admin' and admin_count <= 1:
            raise Exception("Нельзя удалить последнего администратора!")

        # Удаляем пользователя
        cursor.execute('DELETE FROM authorized_users WHERE user_id = ?', (user_id,))


def get_user_info(user_id):
    """
    Получает полную информацию о пользователе по ID
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT user_id, username, full_name, role, added_date 
            FROM authorized_users 
            WHERE user_id = ?
        ''', (user_id,))

        return cursor.fetchone()
