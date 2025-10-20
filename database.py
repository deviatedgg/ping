# database.py
import sqlite3
import hashlib
from datetime import datetime

class UserDatabase:
    """
    Класс для работы с базой данных пользователей.
    Отвечает за хранение и проверку учетных данных.
    """
    
    def __init__(self, database_name="user_data.db"):
        """Инициализация базы данных"""
        self.database_name = database_name
        self.initialize_database()

    def initialize_database(self):
        """Создание таблиц в базе данных если они не существуют"""
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                failed_login_count INTEGER DEFAULT 0,
                last_login_attempt TIMESTAMP,
                account_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица логов входов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS authentication_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT NOT NULL,
                login_success BOOLEAN NOT NULL,
                attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_accounts (id)
            )
        ''')
        
        connection.commit()
        connection.close()

    def _generate_password_hash(self, password):
        """Генерация хеша пароля"""
        return hashlib.sha256(password.encode()).hexdigest()

    def check_email_exists(self, email):
        """Проверка существования email в базе"""
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM user_accounts WHERE email = ?", (email,))
        exists = cursor.fetchone() is not None
        connection.close()
        return exists

    def get_failed_login_count(self, email):
        """Получение количества неудачных попыток входа"""
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute("SELECT failed_login_count FROM user_accounts WHERE email=?", (email,))
        result = cursor.fetchone()
        connection.close()
        return result[0] if result else 0

    def verify_user_credentials(self, email, password):
        """Проверка email и пароля пользователя"""
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute("SELECT id, username, email, password_hash FROM user_accounts WHERE email=?", (email,))
        user_record = cursor.fetchone()

        if user_record and user_record[3] == self._generate_password_hash(password):
            user_info = (user_record[0], user_record[1], user_record[2])
            self._record_login_attempt(user_record[0], email, True)
            self.update_login_attempts(email, True)
            connection.close()
            return user_info

        self._record_login_attempt(user_record[0] if user_record else None, email, False)
        self.update_login_attempts(email, False)
        connection.close()
        return None

    def update_login_attempts(self, email, successful):
        """Обновление счетчика неудачных попыток входа"""
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        attempts = 0 if successful else self.get_failed_login_count(email) + 1
        cursor.execute('''
            UPDATE user_accounts
            SET failed_login_count = ?, last_login_attempt = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (attempts, email))
        connection.commit()
        connection.close()

    def create_new_user(self, username, email, password):
        """Создание нового пользователя"""
        if self.check_email_exists(email):
            return False
            
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        try:
            password_hash = self._generate_password_hash(password)
            cursor.execute('''
                INSERT INTO user_accounts (username, email, password_hash)
                VALUES (?, ?, ?)
            ''', (username, email, password_hash))
            connection.commit()
            connection.close()
            return True
        except sqlite3.IntegrityError:
            connection.close()
            return False

    def _record_login_attempt(self, user_id, email, success):
        """Запись попытки входа в лог"""
        connection = sqlite3.connect(self.database_name)
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO authentication_logs (user_id, email, login_success)
            VALUES (?, ?, ?)
        ''', (user_id, email, success))
        connection.commit()
        connection.close()


if __name__ == "__main__":
    db = UserDatabase()
    print("База данных инициализирована успешно")