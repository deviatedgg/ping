# main.py
import sys
import random
import re
import os
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QFormLayout, QMessageBox, QGridLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QMimeData, QTimer
from PyQt5.QtGui import (
    QPixmap, QDrag, QPainter, QColor, QFont, QBrush, QLinearGradient
)
from database import UserDatabase


class DraggablePuzzlePiece(QLabel):
    """Перетаскиваемый элемент пазла, который пользователь может перемещать."""

    def __init__(self, image, correct_position_index, parent=None):
        # """Инициализирует элемент пазла с изображением и его правильной."""
        super().__init__(parent)
        self.setPixmap(image.scaled(100, 100, Qt.KeepAspectRatio))
        self.correct_position_index = correct_position_index
        self.setStyleSheet(
            "border: 2px solid #444; background: #e0e0e0; "
            "margin: 2px; border-radius: 8px;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(True)

    def mousePressEvent(self, event):
        """Обрабатывает нажатие мыши для начала перетаскивания элемента."""
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(self.correct_position_index))
            drag.setMimeData(mime_data)
            drag.setPixmap(self.pixmap())
            drag.setHotSpot(event.pos())
            drag.exec(Qt.DropAction.MoveAction)


class PuzzleTargetArea(QLabel):
    """Целевая область, куда пользователь может перетащить элементы пазла."""

    def __init__(self, position_index, captcha_widget):
        """Инициализирует целевую область с указанным индексом позиции."""
        super().__init__()
        self.position_index = position_index
        self.captcha_widget = captcha_widget
        self.setFixedSize(110, 110)
        self.setStyleSheet(
            "border: 2px dashed #777; background: #f0f0f0; border-radius: 8px;"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """Разрешает перетаскивание, если элемент содержит текстовые данные."""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Обрабатывает событие отпускания элемента в целевой области."""
        if event.mimeData().hasText():
            correct_position = int(event.mimeData().text())
            source_widget = event.source()
            if isinstance(source_widget, DraggablePuzzlePiece):
                if self.pixmap() and not self.pixmap().isNull():
                    self.captcha_widget.return_piece_to_origin(self)
                self.setPixmap(source_widget.pixmap())
                source_widget.hide()
                self.correct_position_index = correct_position
                event.acceptProposedAction()
                self.captcha_widget.check_puzzle_completion()


class SecurityPuzzleWidget(QWidget):
    """Окно капчи с пазлом."""

    def __init__(self, parent=None):
        """Инициализирует окно капчи с пазлом из 4 элементов."""
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.piece_count = 4
        self.target_areas = []
        self.correct_positions = list(range(self.piece_count))
        self.puzzle_complete = False
        self.success_callback = None
        self.setup_interface()

    def get_image_paths(self):
        """Ищет файлы изображений Image1-Image4 в текущей директории."""
        current_dir = os.path.dirname(__file__)

        image_paths = []
        for i in range(1, 5):
            found = False
            for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                path = os.path.join(current_dir, f"Image{i}{ext}")
                if os.path.exists(path):
                    image_paths.append(path)
                    found = True
                    break
            if not found:
                pixmap = self.create_temporary_image(i)
                image_paths.append(pixmap)

        return image_paths

    def create_temporary_image(self, number):
        """Создает временное изображение если файл не найден."""
        pixmap = QPixmap(200, 200)
        colors = [
            QColor(255, 100, 100),
            QColor(100, 255, 100),
            QColor(100, 100, 255),
            QColor(255, 255, 100),
        ]

        color_idx = (number - 1) % len(colors)
        pixmap.fill(colors[color_idx])
        painter = QPainter(pixmap)
        painter.setPen(QColor(0, 0, 0))
        painter.setFont(QFont('Arial', 16))
        painter.drawText(
            pixmap.rect(), Qt.AlignCenter, f"Image{number}\n(не найден)"
        )
        painter.end()
        return pixmap

    def setup_interface(self):
        """Создает и настраивает пользовательский интерфейс окна капчи."""
        self.setWindowTitle("Проверка безопасности")
        self.setFixedSize(800, 600)
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(15)

        title = QLabel("Соберите пазл для проверки")
        title.setStyleSheet(
            "font: bold 20px; margin: 15px; color: #2c3e50;"
        )
        main_layout.addWidget(title, alignment=Qt.AlignCenter)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(30)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_label = QLabel("Перетащите кусочки отсюда:")
        left_label.setStyleSheet(
            "font: bold 14px; color: #34495e; margin: 10px;"
        )
        left_layout.addWidget(left_label, alignment=Qt.AlignCenter)

        self.piece_container = QWidget()
        self.piece_layout = QGridLayout(self.piece_container)
        self.piece_layout.setSpacing(8)
        self.piece_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.piece_container)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_label = QLabel("Перетащите кусочки сюда для сборки:")
        right_label.setStyleSheet(
            "font: bold 14px; color: #34495e; margin: 10px;"
        )
        right_layout.addWidget(right_label, alignment=Qt.AlignCenter)

        self.target_container = QWidget()
        self.target_layout = QGridLayout(self.target_container)
        self.target_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.target_layout.setSpacing(8)
        right_layout.addWidget(self.target_container)

        content_layout.addWidget(left_container)
        content_layout.addWidget(right_container)

        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget, alignment=Qt.AlignCenter)

        button_layout = QHBoxLayout()

        self.reset_btn = QPushButton("🔄 Сбросить пазл")
        self.reset_btn.setFixedSize(140, 40)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_puzzle)

        button_layout.addWidget(self.reset_btn)

        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget, alignment=Qt.AlignCenter)

        self.load_puzzle_pieces()

    def load_puzzle_pieces(self):
        """Загружает изображения и создает элементы пазла."""
        self.clear_layout(self.piece_layout)
        self.clear_layout(self.target_layout)

        self.puzzle_pieces = []
        self.target_areas = []

        self.current_image_paths = self.get_image_paths()

        puzzle_images = []
        for path in self.current_image_paths:
            if isinstance(path, str):
                pixmap = QPixmap(path)
                if pixmap.isNull():
                    pixmap = self.create_temporary_image(
                        len(puzzle_images) + 1
                    )
            else:
                pixmap = path

            puzzle_images.append(pixmap)

        self.puzzle_pieces = [
            DraggablePuzzlePiece(img, i, self)
            for i, img in enumerate(puzzle_images)
        ]

        random.shuffle(self.puzzle_pieces)

        grid_positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for i, piece in enumerate(self.puzzle_pieces):
            if i < len(grid_positions):
                row, col = grid_positions[i]
                self.piece_layout.addWidget(piece, row, col, Qt.AlignCenter)

        self.target_areas = [PuzzleTargetArea(i, self) for i in range(4)]
        for i, area in enumerate(self.target_areas):
            row, col = i // 2, i % 2
            self.target_layout.addWidget(area, row, col, Qt.AlignCenter)

        self.puzzle_complete = False

    def clear_layout(self, layout):
        """Очищает layout от всех виджетов."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)

    def return_piece_to_origin(self, target_area):
        """Возвращает элемент пазла обратно в исходную область."""
        if hasattr(target_area, 'correct_position_index'):
            for piece in self.puzzle_pieces:
                if piece.correct_position_index == target_area.correct_position_index:
                    piece.show()
                    empty_found = False
                    for i in range(self.piece_layout.count()):
                        item = self.piece_layout.itemAt(i)
                        if not item or not item.widget():
                            row, col = i // 2, i % 2
                            self.piece_layout.addWidget(piece, row, col)
                            empty_found = True
                            break

                    if not empty_found:
                        row, col = self.piece_layout.rowCount(), 0
                        self.piece_layout.addWidget(piece, row, col)
                    break
        target_area.clear()
        target_area.setStyleSheet(
            "border: 2px dashed #777; background: #f0f0f0; border-radius: 8px;"
        )

    def all_targets_filled(self):
        """Проверяет, все ли целевые области заполнены элементами."""
        return all(
            area.pixmap() and not area.pixmap().isNull()
            for area in self.target_areas
        )

    def check_puzzle_completion(self):
        """Автоматически проверяет завершенность пазла."""
        if not self.all_targets_filled():
            return

        self.puzzle_complete = all(
            hasattr(area, 'correct_position_index') and
            area.correct_position_index == i
            for i, area in enumerate(self.target_areas)
        )

        if self.puzzle_complete:
            QTimer.singleShot(300, self.puzzle_solved)
        else:
            QTimer.singleShot(500, self.reset_puzzle)

    def puzzle_solved(self):
        """Вызывается при успешном решении пазла."""
        self.close()
        QMessageBox.information(None, "Успех", "Проверка безопасности пройдена!")
        if self.success_callback:
            self.success_callback()

    def reset_puzzle(self):
        """Сбрасывает пазл - перемешивает элементы."""
        for area in self.target_areas:
            if area.pixmap() and not area.pixmap().isNull():
                self.return_piece_to_origin(area)

        for piece in self.puzzle_pieces:
            piece.show()

        random.shuffle(self.puzzle_pieces)

        self.clear_layout(self.piece_layout)
        grid_positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for i, piece in enumerate(self.puzzle_pieces):
            if i < len(grid_positions):
                row, col = grid_positions[i]
                self.piece_layout.addWidget(piece, row, col, Qt.AlignCenter)

        self.puzzle_complete = False


class AuthenticationWindow(QWidget):
    """Главное окно аутентификации с вкладками для входа и регистрации."""

    def __init__(self):
        """Инициализирует окно аутентификации и базу данных."""
        super().__init__()
        self.database = UserDatabase()
        self.max_login_attempts = 3
        self.pong_game = None
        self.initialize_interface()

    def initialize_interface(self):
        """Создает и настраивает пользовательский интерфейс."""
        self.setWindowTitle("Система аутентификации")
        self.resize(500, 450)

        layout = QVBoxLayout()
        layout.setSpacing(20)

        title = QLabel("Портал аутентификации")
        title.setStyleSheet("font: bold 24px; color: #2c3e50; margin: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                background: #ecf0f1;
            }
            QTabBar::tab {
                background: #95a5a6;
                color: white;
                padding: 10px 20px;
                margin: 2px;
                border-radius: 3px;
            }
            QTabBar::tab:selected {
                background: #3498db;
            }
        """)

        self.setup_login_tab()
        self.setup_registration_tab()

        self.tab_widget.addTab(self.login_tab, "🔐 Вход")
        self.tab_widget.addTab(self.registration_tab, "👤 Регистрация")

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def setup_login_tab(self):
        """Создает вкладку для входа в систему."""
        self.login_tab = QWidget()
        login_layout = QFormLayout()
        login_layout.setSpacing(15)
        login_layout.setContentsMargins(30, 30, 30, 30)

        input_style = """
            QLineEdit {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """

        self.login_email_input = QLineEdit()
        self.login_email_input.setPlaceholderText("Введите ваш email")
        self.login_email_input.setStyleSheet(input_style)

        self.login_password_input = QLineEdit()
        self.login_password_input.setPlaceholderText("Введите ваш пароль")
        self.login_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password_input.setStyleSheet(input_style)

        self.login_btn = QPushButton("🚀 Войти")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: #27ae60;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #219653;
            }
            QPushButton:pressed {
                background: #1e8449;
            }
        """)
        self.login_btn.clicked.connect(self.process_login)

        login_layout.addRow("📧 Email:", self.login_email_input)
        login_layout.addRow("🔒 Пароль:", self.login_password_input)
        login_layout.addRow(self.login_btn)

        self.login_tab.setLayout(login_layout)

    def setup_registration_tab(self):
        """Создает вкладку для регистрации нового пользователя."""
        self.registration_tab = QWidget()
        register_layout = QFormLayout()
        register_layout.setSpacing(15)
        register_layout.setContentsMargins(30, 30, 30, 30)

        input_style = """
            QLineEdit {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """

        self.reg_name_input = QLineEdit()
        self.reg_name_input.setPlaceholderText("Введите ваше имя")
        self.reg_name_input.setStyleSheet(input_style)

        self.reg_email_input = QLineEdit()
        self.reg_email_input.setPlaceholderText("Введите ваш email")
        self.reg_email_input.setStyleSheet(input_style)

        self.reg_password_input = QLineEdit()
        self.reg_password_input.setPlaceholderText(
            "Придумайте пароль (минимум 6 символов)"
        )
        self.reg_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password_input.setStyleSheet(input_style)

        self.register_btn = QPushButton("✨ Создать аккаунт")
        self.register_btn.setStyleSheet("""
            QPushButton {
                background: #e67e22;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #d35400;
            }
            QPushButton:pressed {
                background: #ba4a00;
            }
        """)
        self.register_btn.clicked.connect(self.process_registration)

        register_layout.addRow("👤 Имя:", self.reg_name_input)
        register_layout.addRow("📧 Email:", self.reg_email_input)
        register_layout.addRow("🔒 Пароль:", self.reg_password_input)
        register_layout.addRow(self.register_btn)

        self.registration_tab.setLayout(register_layout)

    def process_login(self):
        """Обрабатывает попытку входа пользователя."""
        email = self.login_email_input.text().strip()
        password = self.login_password_input.text().strip()

        if not email or not password:
            QMessageBox.warning(
                self, "Ошибка ввода", "Пожалуйста, заполните все поля!"
            )
            return

        if not self.database.check_email_exists(email):
            self.create_temporary_user_record(email)

        current_attempts = self.database.get_failed_login_count(email)

        if current_attempts >= self.max_login_attempts:
            QMessageBox.warning(
                self,
                "Доступ ограничен",
                "Слишком много неудачных попыток входа. "
                "Требуется проверка безопасности."
            )
            self.display_security_puzzle(email)
            return

        user_exists = self.database.check_email_exists(email)
        user_data = self.database.verify_user_credentials(
            email, password
        ) if user_exists else None

        if user_exists and user_data:
            self.database.update_login_attempts(email, True)
            QMessageBox.information(
                self, "Добро пожаловать", f"Вход выполнен, {user_data[1]}!"
            )
            self.launch_pong_game(user_data[1])
            return

        self.database.update_login_attempts(email, False)
        updated_attempts = self.database.get_failed_login_count(email)
        remaining_attempts = self.max_login_attempts - updated_attempts

        if remaining_attempts > 0:
            error_msg = (
                "Пользователь не найден"
                if not user_exists else "Неверный пароль"
            )
            QMessageBox.warning(
                self,
                "Ошибка входа",
                f"{error_msg}. Осталось попыток: {remaining_attempts}"
            )
        else:
            QMessageBox.warning(
                self,
                "Предупреждение безопасности",
                "Превышено максимальное количество попыток. "
                "Требуется проверка безопасности."
            )
            self.display_security_puzzle(email)

    def create_temporary_user_record(self, email):
        """Создает временную запись пользователя."""
        connection = sqlite3.connect(self.database.database_name)
        cursor = connection.cursor()
        try:
            sql = '''
                INSERT OR IGNORE INTO user_accounts
                (email, password_hash, username, failed_login_count)
                VALUES (?, ?, ?, ?)
            '''
            cursor.execute(
                sql, (email, 'temporary_hash', 'temporary_user', 1)
            )
            connection.commit()
        except Exception as e:
            print(f"Ошибка создания временной записи: {e}")
        finally:
            connection.close()

    def display_security_puzzle(self, email):
        """Показывает окно капчи для проверки безопасности."""
        self.puzzle_window = SecurityPuzzleWidget(self)
        self.puzzle_window.success_callback = lambda: self.security_passed(email)
        self.puzzle_window.show()

    def security_passed(self, email):
        """Вызывается после успешного прохождения капчи."""
        self.database.update_login_attempts(email, True)
        self.login_password_input.clear()
        self.login_password_input.setFocus()
        self.activateWindow()
        self.raise_()

    def process_registration(self):
        """Обрабатывает регистрацию нового пользователя."""
        name = self.reg_name_input.text().strip()
        email = self.reg_email_input.text().strip()
        password = self.reg_password_input.text().strip()

        if not name or not email or not password:
            QMessageBox.warning(
                self, "Ошибка ввода", "Все поля обязательны для заполнения!"
            )
            return

        if len(password) < 6:
            QMessageBox.warning(
                self,
                "Ошибка пароля",
                "Пароль должен содержать не менее 6 символов!"
            )
            return

        if not self.validate_email_format(email):
            QMessageBox.warning(
                self,
                "Ошибка email",
                "Пожалуйста, введите корректный email адрес!"
            )
            return

        if self.database.create_new_user(name, email, password):
            QMessageBox.information(
                self, "Успех", "Аккаунт успешно создан!"
            )
            self.reg_name_input.clear()
            self.reg_email_input.clear()
            self.reg_password_input.clear()
            self.tab_widget.setCurrentIndex(0)
        else:
            QMessageBox.warning(
                self, "Ошибка регистрации", "Email уже зарегистрирован!"
            )

    def validate_email_format(self, email):
        """Проверяет корректность формата email адреса."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def launch_pong_game(self, username):
        """Запускает игру в пинг-понг после успешного входа."""
        if self.pong_game is None:
            self.pong_game = PongGame(username)
        self.pong_game.show()
        self.close()


class PongGame(QWidget):
    """Окно игры в пинг-понг."""

    def __init__(self, username):
        """Инициализирует игровое поле и параметры игры."""
        super().__init__()
        self.username = username

        self.paddle_width = 12
        self.paddle_height = 90
        self.ball_size = 18
        self.paddle_velocity = 12
        self.ball_velocity_x = 7.0
        self.ball_velocity_y = 7.0
        self.ball_acceleration = 0.002
        self.max_ball_speed = 14.0

        self.player1_y = 255
        self.player2_y = 255
        self.ball_x = 391.0
        self.ball_y = 291.0
        self.player1_score = 0
        self.player2_score = 0

        self.active_keys = {}
        self.game_font = QFont('Arial', 22, QFont.Bold)
        self.info_font = QFont('Arial', 12)

        self.setFixedSize(800, 600)
        self.setWindowTitle("Космический Понг - Мультиплеер")

        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self.game_loop)
        self.game_timer.start(16)

    def keyPressEvent(self, event):
        """Обрабатывает нажатия клавиш для управления ракетками."""
        self.active_keys[event.key()] = True
        if event.key() == Qt.Key_F:
            self.restart_match()

    def keyReleaseEvent(self, event):
        """Обрабатывает отпускание клавиш."""
        self.active_keys[event.key()] = False

    def game_loop(self):
        """Основной игровой цикл, обновляющий состояние игры."""
        if self.active_keys.get(Qt.Key_W, False):
            self.player1_y = max(0, self.player1_y - self.paddle_velocity)
        if self.active_keys.get(Qt.Key_S, False):
            self.player1_y = min(
                self.height() - self.paddle_height,
                self.player1_y + self.paddle_velocity
            )

        if self.active_keys.get(Qt.Key_Up, False):
            self.player2_y = max(0, self.player2_y - self.paddle_velocity)
        if self.active_keys.get(Qt.Key_Down, False):
            self.player2_y = min(
                self.height() - self.paddle_height,
                self.player2_y + self.paddle_velocity
            )

        acceleration = self.ball_acceleration
        direction_x = 1 if self.ball_velocity_x > 0 else -1
        direction_y = 1 if self.ball_velocity_y > 0 else -1

        self.ball_velocity_x += acceleration * direction_x
        self.ball_velocity_y += acceleration * direction_y

        self.ball_velocity_x = min(
            max(self.ball_velocity_x, -self.max_ball_speed),
            self.max_ball_speed
        )
        self.ball_velocity_y = min(
            max(self.ball_velocity_y, -self.max_ball_speed),
            self.max_ball_speed
        )

        self.ball_x += self.ball_velocity_x
        self.ball_y += self.ball_velocity_y

        if self.ball_y <= 0 or self.ball_y + self.ball_size >= self.height():
            self.ball_velocity_y *= -1

        if (self.ball_x <= self.paddle_width and
                self.player1_y <= self.ball_y + self.ball_size and
                self.ball_y <= self.player1_y + self.paddle_height):
            self.ball_velocity_x = abs(self.ball_velocity_x) * 1.05
            self.ball_x = self.paddle_width + 1

        if (self.ball_x + self.ball_size >= self.width() - self.paddle_width and
                self.player2_y <= self.ball_y + self.ball_size and
                self.ball_y <= self.player2_y + self.paddle_height):
            self.ball_velocity_x = -abs(self.ball_velocity_x) * 1.05
            self.ball_x = (
                self.width() - self.paddle_width - self.ball_size - 1
            )

        if self.ball_x < 0:
            self.player2_score += 1
            self.reset_ball_position()

        if self.ball_x > self.width():
            self.player1_score += 1
            self.reset_ball_position()

        if self.player1_score >= 5 or self.player2_score >= 5:
            self.game_timer.stop()
            winner_name = (
                self.username
                if self.player1_score > self.player2_score
                else "Игрок 2"
            )
            QMessageBox.information(
                self,
                "Результат матча",
                f"Победитель: {winner_name}\n"
                "Нажмите F для перезапуска матча."
            )

        self.update()

    def reset_ball_position(self):
        """Сбрасывает мяч в центр поля после гола."""
        self.ball_x = self.width() // 2 - self.ball_size // 2
        self.ball_y = self.height() // 2 - self.ball_size // 2
        self.ball_velocity_x = 7.0 if random.choice([True, False]) else -7.0
        self.ball_velocity_y = 7.0 if random.choice([True, False]) else -7.0

    def paintEvent(self, event):
        """Отрисовывает все игровые объекты на экране."""
        painter = QPainter(self)

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(10, 10, 40))
        gradient.setColorAt(1, QColor(30, 10, 60))
        painter.fillRect(self.rect(), QBrush(gradient))

        painter.setPen(QColor(100, 100, 150, 150))
        for i in range(0, self.height(), 20):
            painter.drawRect(self.width() // 2 - 1, i, 2, 10)

        painter.setBrush(QColor(70, 200, 255))
        painter.drawRect(0, self.player1_y, self.paddle_width, self.paddle_height)
        painter.drawRect(
            self.width() - self.paddle_width,
            self.player2_y,
            self.paddle_width,
            self.paddle_height
        )

        painter.setBrush(QColor(255, 255, 200))
        painter.drawEllipse(
            int(self.ball_x), int(self.ball_y), self.ball_size, self.ball_size
        )

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(self.game_font)
        painter.drawText(self.width() // 4, 40, str(self.player1_score))
        painter.drawText(self.width() * 3 // 4, 40, str(self.player2_score))

        painter.setFont(self.info_font)
        painter.drawText(15, self.height() - 20, self.username)
        painter.drawText(self.width() - 100, self.height() - 20, "Игрок 2")

        painter.setPen(QColor(200, 200, 200, 180))
        painter.drawText(10, 20, "Нажмите F для перезапуска")

    def restart_match(self):
        """Перезапускает матч, сбрасывая счет и позиции."""
        self.player1_score = 0
        self.player2_score = 0
        self.player1_y = self.height() // 2 - self.paddle_height // 2
        self.player2_y = self.height() // 2 - self.paddle_height // 2
        self.ball_velocity_x = 7.0
        self.ball_velocity_y = 7.0
        self.reset_ball_position()
        self.game_timer.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    auth_window = AuthenticationWindow()
    auth_window.show()
    sys.exit(app.exec())