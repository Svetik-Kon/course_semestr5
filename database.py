import sqlite3

def create_tables():
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            description TEXT,
            date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS limits (
            user_id INTEGER,
            year INTEGER,
            month INTEGER,
            limit_amount REAL,
            PRIMARY KEY (user_id, year, month)
        )
    ''')  # Добавляем таблицу для хранения лимитов
    conn.commit()
    conn.close()


def add_transaction(user_id, amount, category, description, date):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (user_id, amount, category, description, date)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, category, description, date))
    conn.commit()
    conn.close()

def get_summary(user_id, date_filter=None):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    query = '''
        SELECT category, SUM(amount) FROM transactions
        WHERE user_id = ?
    '''
    params = [user_id]
    if date_filter:
        query += " AND date = ?"  # Меняем >= на = для точного соответствия дате
        params.append(date_filter)
    query += " GROUP BY category"
    cursor.execute(query, params)
    summary = cursor.fetchall()
    conn.close()
    return summary


def get_monthly_summary(user_id, year, month):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    # Запрос для группировки по категориям
    category_query = '''
           SELECT category, SUM(amount) FROM transactions
           WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
           GROUP BY category
       '''
    # Запрос для общей суммы
    total_query = '''
           SELECT SUM(amount) FROM transactions
           WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
       '''
    params = [user_id, str(year), f"{int(month):02d}"]

    # Получаем данные по категориям
    cursor.execute(category_query, params)
    category_summary = cursor.fetchall()

    # Получаем общую сумму
    cursor.execute(total_query, params)
    total_amount = cursor.fetchone()[0]  # Извлекаем единственное значение

    conn.close()
    return category_summary, total_amount


def set_monthly_limit(user_id, year, month, limit_amount):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO limits (user_id, year, month, limit_amount)
        VALUES (?, ?, ?, ?)
    ''', (user_id, year, month, limit_amount))
    conn.commit()
    conn.close()

def get_monthly_limit(user_id, year, month):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT limit_amount FROM limits
        WHERE user_id = ? AND year = ? AND month = ?
    ''', (user_id, year, month))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def create_monthly_reminders_table():
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_reminders (
            user_id INTEGER,
            chat_id INTEGER,
            day INTEGER,
            time TEXT,
            message TEXT,
            PRIMARY KEY (user_id, day, time)
        )
    ''')
    conn.commit()
    conn.close()

def add_monthly_reminder(user_id, chat_id, day, time, message):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO monthly_reminders (user_id, chat_id, day, time, message)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, chat_id, day, time, message))
    conn.commit()
    conn.close()

def get_all_monthly_reminders():
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, chat_id, day, time, message FROM monthly_reminders')
    reminders = cursor.fetchall()
    conn.close()
    return reminders
