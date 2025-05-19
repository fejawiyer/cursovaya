from PyQt5 import QtGui
from PyQt5.QtWidgets import (QVBoxLayout, QDialog, QLabel, QLineEdit, QDialogButtonBox, QHBoxLayout, QPushButton,
                             QSpinBox, QMessageBox, QGraphicsSimpleTextItem)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QColor, QFont, QBrush
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem


class MapSizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор размера карты")
        self.layout = QVBoxLayout(self)

        self.size_label = QLabel("Размер карты (метры):")
        self.size_input = QSpinBox()
        self.size_input.setRange(10, 1000)
        self.size_input.setValue(100)

        self.resolution_label = QLabel("Разрешение (пикселей на метр):")
        self.resolution_input = QSpinBox()
        self.resolution_input.setRange(1, 100)
        self.resolution_input.setValue(5)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.layout.addWidget(self.size_label)
        self.layout.addWidget(self.size_input)
        self.layout.addWidget(self.resolution_label)
        self.layout.addWidget(self.resolution_input)
        self.layout.addWidget(self.buttons)

    def get_values(self):
        return self.size_input.value(), self.resolution_input.value()


class MapView(QGraphicsView):
    def __init__(self, size_meters=100, resolution=5, parent=None):
        super().__init__(parent)
        self.size_meters = size_meters
        self.resolution = resolution  # пикселей на метр
        self.pixels = size_meters * resolution

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.sources = []
        self.current_source = None
        self.temp_source = None  # Временный источник перед сохранением

        # Настройка сцены
        self.scene.setSceneRect(0, 0, self.pixels, self.pixels)
        self.setFixedSize(self.pixels + 20, self.pixels + 20)

        # Рисуем сетку и шкалу
        self.draw_grid_and_scale()

    def draw_grid_and_scale(self):
        # Основная сетка (каждый метр)
        pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)
        for i in range(0, self.pixels + 1, self.resolution):
            self.scene.addLine(0, i, self.pixels, i, pen)
            self.scene.addLine(i, 0, i, self.pixels, pen)

        # Утолщённые линии (каждые 10 метров)
        pen = QPen(QColor(150, 150, 150), 1, Qt.SolidLine)
        for i in range(0, self.pixels + 1, 10 * self.resolution):
            self.scene.addLine(0, i, self.pixels, i, pen)
            self.scene.addLine(i, 0, i, self.pixels, pen)

        # Подписи шкалы (0, 10, 20 метров...)
        font = QFont()
        font.setPointSize(8)
        for i in range(0, self.pixels + 1, 10 * self.resolution):
            meters = i // self.resolution
            # Горизонтальная шкала
            text = self.scene.addText(f"{meters}m")
            text.setFont(font)
            text.setPos(i + 5, 0)
            # Вертикальная шкала
            text = self.scene.addText(f"{meters}m")
            text.setFont(font)
            text.setPos(0, i + 5)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            x, y = pos.x(), pos.y()

            # Проверяем, что клик внутри карты
            if 0 <= x <= self.pixels and 0 <= y <= self.pixels:
                # Создаем новый временный источник (красный)
                self.clear_temp_source()
                self.temp_source = {
                    'pos': (x, y),
                    'concentration': 0,
                    'frequency': 1,
                    'item': None,
                    'text_item': None
                }
                self.add_source_to_scene(self.temp_source, is_saved=False)

        elif event.button() == Qt.RightButton:
            # Удаляем последний клик
            if self.temp_source:
                self.clear_temp_source()
            elif self.sources:
                last_source = self.sources.pop()
                self.scene.removeItem(last_source['item'])
                if last_source['text_item']:
                    self.scene.removeItem(last_source['text_item'])

        super().mousePressEvent(event)

    def clear_temp_source(self):
        if self.temp_source:
            if self.temp_source['item']:
                self.scene.removeItem(self.temp_source['item'])
            if self.temp_source['text_item']:
                self.scene.removeItem(self.temp_source['text_item'])
            self.temp_source = None

    def add_source_to_scene(self, source, is_saved=False):
        x, y = source['pos']

        # Удаляем предыдущий маркер, если он есть
        if source['item']:
            self.scene.removeItem(source['item'])
        if source['text_item']:
            self.scene.removeItem(source['text_item'])

        # Создаем новый маркер
        radius = 6 if is_saved else 4  # Сохраненные источники немного больше
        item = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)

        if is_saved:
            item.setBrush(QBrush(QColor(0, 255, 0, 200)))  # Зеленый для сохраненных
            item.setPen(QPen(Qt.darkGreen, 1))
        else:
            item.setBrush(QBrush(QColor(255, 0, 0, 150)))  # Красный для временных
            item.setPen(QPen(Qt.red, 1))

        self.scene.addItem(item)
        source['item'] = item

        # Добавляем текст с концентрацией для сохраненных источников
        if is_saved and source['concentration'] > 0:
            text = QGraphicsSimpleTextItem(f"{source['concentration']:.1f}")
            text.setFont(QFont("Arial", 8))
            text.setPos(x + radius + 2, y - radius)
            text.setBrush(QBrush(Qt.black))
            self.scene.addItem(text)
            source['text_item'] = text

    def update_source(self, concentration, frequency):
        if self.temp_source:
            self.temp_source['concentration'] = concentration
            self.temp_source['frequency'] = frequency
            self.sources.append(self.temp_source)

            self.add_source_to_scene(self.temp_source, is_saved=True)
            self.temp_source = None


class NewConditions(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание начальных условий")
        self.setMinimumSize(600, 700)

        size_dialog = MapSizeDialog(self)
        if size_dialog.exec_() != QDialog.Accepted:
            self.reject()
            return

        size_meters, resolution = size_dialog.get_values()

        self.layout = QVBoxLayout(self)

        self.map_view = MapView(size_meters, resolution, self)
        self.layout.addWidget(self.map_view)

        self.source_params_layout = QHBoxLayout()

        self.concentration_label = QLabel("Концентрация (г/м²):")
        self.concentration_input = QLineEdit("0")
        self.concentration_input.setValidator(QtGui.QDoubleValidator(0, 1000, 2))

        self.frequency_label = QLabel("Частота выбросов:")
        self.frequency_input = QSpinBox()
        self.frequency_input.setRange(1, 1000)
        self.frequency_input.setValue(1)

        self.save_button = QPushButton("Сохранить источник")
        self.save_button.clicked.connect(self.save_source)

        self.source_params_layout.addWidget(self.concentration_label)
        self.source_params_layout.addWidget(self.concentration_input)
        self.source_params_layout.addWidget(self.frequency_label)
        self.source_params_layout.addWidget(self.frequency_input)
        self.source_params_layout.addWidget(self.save_button)

        self.layout.addLayout(self.source_params_layout)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def save_source(self):
        try:
            concentration = float(self.concentration_input.text())
            frequency = self.frequency_input.value()
            self.map_view.update_source(concentration, frequency)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректное значение концентрации")

    def get_properties(self):
        sources = []
        for source in self.map_view.sources:
            x, y = source['pos']
            # Переводим координаты обратно в метры
            x_meters = x / self.map_view.resolution
            y_meters = (self.map_view.pixels-y) / self.map_view.resolution
            sources.append({
                'x': x_meters,
                'y': y_meters,
                'concentration': source['concentration'],
                'frequency': source['frequency']
            })

        return {
            'sources': sources
        }