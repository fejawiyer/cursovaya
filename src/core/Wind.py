from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QDoubleSpinBox, QSpinBox,
                             QGraphicsView, QGraphicsScene, QGraphicsLineItem,
                             QMessageBox, QGroupBox, QDialogButtonBox)
from PyQt5.QtCore import Qt, QPointF, QLineF
from PyQt5.QtGui import QPen, QColor, QPainter, QFont, QTransform
import json
import os
import math


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


class WindMapView(QGraphicsView):
    def __init__(self, size_meters=100, resolution=5, parent=None):
        super().__init__(parent)
        self.size_meters = size_meters
        self.resolution = resolution
        self.pixels = size_meters * resolution

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)

        # Initialize attributes
        self.grid_size = resolution
        self.arrow_size = 10
        self.wind_lines = []
        self.current_line = None
        self.start_point = None

        # Setup scene
        self.scene.setSceneRect(0, 0, self.pixels, self.pixels)
        self.setFixedSize(self.pixels + 20, self.pixels + 20)

        # Invert Y axis to match typical coordinate systems
        self.scale(1, -1)
        self.translate(0, -self.pixels)

        # Draw grid and scale
        self.drawGrid()

    def drawGrid(self):
        """Draw a grid for the map background with scale labels"""
        self.scene.clear()
        self.wind_lines = []

        # Draw grid lines (every meter)
        pen = QPen(QColor(200, 200, 200), 1, Qt.DotLine)
        for i in range(0, self.pixels + 1, self.resolution):
            self.scene.addLine(0, i, self.pixels, i, pen)
            self.scene.addLine(i, 0, i, self.pixels, pen)

        # Draw thicker lines (every 10 meters)
        pen = QPen(QColor(150, 150, 150), 1, Qt.SolidLine)
        for i in range(0, self.pixels + 1, 10 * self.resolution):
            self.scene.addLine(0, i, self.pixels, i, pen)
            self.scene.addLine(i, 0, i, self.pixels, pen)

        # Add scale labels
        font = QFont()
        font.setPointSize(8)
        for i in range(0, self.pixels + 1, 10 * self.resolution):
            meters = i // self.resolution
            # Horizontal scale (bottom)
            text = self.scene.addText(f"{meters}m")
            text.setFont(font)
            text.setPos(i + 5, 15)
            text.setTransform(QTransform().scale(1, -1))
            # Vertical scale (left)
            if i != 0:
                text = self.scene.addText(f"{meters}m")
                text.setFont(font)
                text.setPos(0, i + 5)
                text.setTransform(QTransform().scale(1, -1))

    def addWindLine(self, start_point, end_point, strength):
        """Add a wind line with arrow indicating direction"""
        line = QLineF(start_point, end_point)

        # Calculate color based on strength (blue to red gradient)
        strength_color = min(255, max(0, int(strength * 2.55)))
        color = QColor(strength_color, 100, 255 - strength_color)

        # Create the line item
        pen = QPen(color, 2)
        line_item = QGraphicsLineItem(line)
        line_item.setPen(pen)
        self.scene.addItem(line_item)

        # Add arrow head
        angle = math.atan2(line.dy(), line.dx())
        arrow_p1 = end_point - QPointF(math.cos(angle + math.pi / 3) * self.arrow_size,
                                       math.sin(angle + math.pi / 3) * self.arrow_size)
        arrow_p2 = end_point - QPointF(math.cos(angle - math.pi / 3) * self.arrow_size,
                                       math.sin(angle - math.pi / 3) * self.arrow_size)

        arrow_head1 = QGraphicsLineItem(QLineF(end_point, arrow_p1))
        arrow_head1.setPen(pen)
        self.scene.addItem(arrow_head1)

        arrow_head2 = QGraphicsLineItem(QLineF(end_point, arrow_p2))
        arrow_head2.setPen(pen)
        self.scene.addItem(arrow_head2)

        # Add strength label
        font = QFont()
        font.setPointSize(8)
        text = self.scene.addText(f"{strength:.1f}")
        text.setFont(font)
        text.setPos(end_point.x() + 5, end_point.y() + 5)
        text.setTransform(QTransform().scale(1, -1))

        # Store wind data - теперь включаем все элементы стрелки
        self.wind_lines.append({
            'start': start_point,
            'end': end_point,
            'strength': strength,
            'items': [line_item, arrow_head1, arrow_head2, text]  # Все 4 элемента
        })

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = self.mapToScene(event.pos())

    def mouseMoveEvent(self, event):
        if self.start_point:
            if self.current_line:
                self.scene.removeItem(self.current_line)

            end_point = self.mapToScene(event.pos())
            line = QLineF(self.start_point, end_point)

            pen = QPen(QColor(0, 100, 255, 150), 2, Qt.DashLine)
            self.current_line = self.scene.addLine(line, pen)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_point:
            if self.current_line:
                self.scene.removeItem(self.current_line)
                self.current_line = None

            end_point = self.mapToScene(event.pos())

            parent = self.parent()
            while parent and not isinstance(parent, WindRulesDialog):
                parent = parent.parent()

            if parent:
                strength = parent.getCurrentStrength()
                time_sec = parent.getCurrentTime()
                self.addWindLine(self.start_point, end_point, strength)

            self.start_point = None

    def clearAllWind(self):
        """Remove all wind lines from the scene"""
        for wind_data in self.wind_lines:
            for item in wind_data['items']:
                self.scene.removeItem(item)
        self.wind_lines = []

    def getWindData(self):
        """Return wind data in a serializable format"""
        data = []
        for wind in self.wind_lines:
            data.append({
                'start_x': wind['start'].x() / self.resolution,
                'start_y': (self.pixels - wind['start'].y()) / self.resolution,
                'end_x': wind['end'].x() / self.resolution,
                'end_y': (self.pixels - wind['end'].y()) / self.resolution,
                'strength': wind['strength']
            })
        return data


class WindRulesDialog(QDialog):
    def __init__(self, wind_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wind Rules Editor - Graphical Mode")
        self.wind_json_path = str(wind_path)

        # First show map size dialog
        size_dialog = MapSizeDialog(self)
        if size_dialog.exec_() != QDialog.Accepted:
            self.reject()
            return

        size_meters, resolution = size_dialog.get_values()

        # Initialize with loaded or empty data
        self.wind_data = []
        self.load_rules()

        self.initUI(size_meters, resolution)

    def initUI(self, size_meters, resolution):
        layout = QVBoxLayout()

        # Create the map view with specified size
        self.map_view = WindMapView(size_meters, resolution)
        layout.addWidget(self.map_view)

        # Controls panel
        controls_layout = QHBoxLayout()

        # Wind parameters group
        params_group = QGroupBox("Wind Parameters")
        params_layout = QHBoxLayout()

        params_layout.addWidget(QLabel("Strength (m/s):"))
        self.strength_spin = QDoubleSpinBox()
        self.strength_spin.setRange(0.1, 100.0)
        self.strength_spin.setValue(5.0)
        self.strength_spin.setSingleStep(0.5)
        params_layout.addWidget(self.strength_spin)

        params_layout.addWidget(QLabel("Time (sec):"))
        self.time_spin = QSpinBox()
        self.time_spin.setRange(0, 86400)
        self.time_spin.setValue(0)
        params_layout.addWidget(self.time_spin)

        params_group.setLayout(params_layout)
        controls_layout.addWidget(params_group)

        # Action buttons
        btn_layout = QVBoxLayout()

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.map_view.clearAllWind)
        btn_layout.addWidget(self.clear_btn)

        self.undo_btn = QPushButton("Undo Last")
        self.undo_btn.clicked.connect(self.undoLastWind)
        btn_layout.addWidget(self.undo_btn)

        controls_layout.addLayout(btn_layout)
        layout.addLayout(controls_layout)

        # Dialog buttons
        button_box = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_and_accept)
        button_box.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(cancel_btn)

        layout.addLayout(button_box)
        self.setLayout(layout)

        # Load existing wind data
        self.loadWindDataToMap()

    def getCurrentStrength(self):
        return self.strength_spin.value()

    def getCurrentTime(self):
        return self.time_spin.value()

    def undoLastWind(self):
        if self.map_view.wind_lines:
            last_wind = self.map_view.wind_lines.pop()
            # Удаляем все элементы стрелки (основную линию и две части стрелки)
            for item in last_wind['items']:
                self.map_view.scene.removeItem(item)

    def load_rules(self):
        if os.path.exists(self.wind_json_path):
            try:
                with open(self.wind_json_path, 'r') as f:
                    self.wind_data = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Failed to load wind rules: {str(e)}")
                self.wind_data = []

    def loadWindDataToMap(self):
        for wind in self.wind_data:
            try:
                # Convert from meters to pixels
                start_x = wind['start_x'] * self.map_view.resolution
                start_y = self.map_view.pixels - (wind['start_y'] * self.map_view.resolution)
                end_x = wind['end_x'] * self.map_view.resolution
                end_y = self.map_view.pixels - (wind['end_y'] * self.map_view.resolution)

                start_point = QPointF(start_x, start_y)
                end_point = QPointF(end_x, end_y)
                self.map_view.addWindLine(start_point, end_point, wind['strength'])
            except KeyError as e:
                print(f"Skipping invalid wind data: {wind}. Missing key: {e}")

    def save_rules(self):
        try:
            self.wind_data = self.map_view.getWindData()

            with open(self.wind_json_path, 'w') as f:
                json.dump(self.wind_data, f, indent=4)
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save wind rules: {str(e)}")
            return False

    def save_and_accept(self):
        if self.save_rules():
            self.accept()

    def get_rules(self):
        return self.wind_data.copy()