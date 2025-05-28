import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QMessageBox, QHeaderView, QHBoxLayout)


class SubstancesDialog(QDialog):
    def __init__(self, json_file, parent=None):
        super().__init__(parent)
        self.json_file = json_file
        self.setWindowTitle("Редактирование ПДК веществ")
        self.setModal(True)
        self.resize(600, 400)

        # Загрузка данных из JSON
        self.load_data()

        # Создание интерфейса
        self.init_ui()

    def load_data(self):
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            if "substances" not in self.data:
                self.data["substances"] = []
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл: {str(e)}")
            self.data = {"substances": []}

    def save_data(self):
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
            return False

    def init_ui(self):
        layout = QVBoxLayout()

        # Создание таблицы
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Название", "ПДК", "ПДК рабочей зоны"])

        # Заполнение таблицы данными
        self.update_table()

        # Настройка таблицы
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.AllEditTriggers)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("Добавить")
        btn_add.clicked.connect(self.add_row)
        btn_layout.addWidget(btn_add)

        btn_delete = QPushButton("Удалить")
        btn_delete.clicked.connect(self.delete_row)
        btn_layout.addWidget(btn_delete)

        # Кнопки OK/Отмена
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.on_ok)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)

        # Добавление элементов в layout
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)
        layout.addWidget(btn_ok)
        layout.addWidget(btn_cancel)

        self.setLayout(layout)

    def update_table(self):
        substances = self.data.get("substances", [])
        self.table.setRowCount(len(substances))

        for row, substance in enumerate(substances):
            name_item = QTableWidgetItem(substance["name"])
            pdk_item = QTableWidgetItem(str(substance["pdk"]))
            pdk_work_item = QTableWidgetItem(str(substance["pdk_work"]))

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, pdk_item)
            self.table.setItem(row, 2, pdk_work_item)

    def add_row(self):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

        # Добавляем пустые ячейки
        name_item = QTableWidgetItem("Новое вещество")
        pdk_item = QTableWidgetItem("0")
        pdk_work_item = QTableWidgetItem("0")

        self.table.setItem(row_count, 0, name_item)
        self.table.setItem(row_count, 1, pdk_item)
        self.table.setItem(row_count, 2, pdk_work_item)

        # Перемещаем фокус на новую строку
        self.table.setCurrentCell(row_count, 0)

    def delete_row(self):
        current_row = self.table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите строку для удаления")
            return

        reply = QMessageBox.question(
            self, 'Подтверждение',
            'Вы уверены, что хотите удалить это вещество?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.table.removeRow(current_row)

    def on_ok(self):
        # Очищаем текущие данные
        self.data["substances"] = []

        # Собираем данные из таблицы
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            pdk_item = self.table.item(row, 1)
            pdk_work_item = self.table.item(row, 2)

            if not name_item or not pdk_item or not pdk_work_item:
                continue

            name = name_item.text().strip()
            if not name:
                QMessageBox.warning(self, "Ошибка", f"Название вещества в строке {row + 1} не может быть пустым")
                return

            try:
                pdk = float(pdk_item.text())
                pdk_work = float(pdk_work_item.text())
            except ValueError:
                QMessageBox.warning(self, "Ошибка", f"ПДК в строке {row + 1} должны быть числовыми значениями")
                return

            # Проверяем на дубликаты названий
            for substance in self.data["substances"]:
                if substance["name"].lower() == name.lower():
                    QMessageBox.warning(self, "Ошибка", f"Вещество '{name}' уже существует")
                    return

            # Добавляем новое вещество
            self.data["substances"].append({
                "name": name,
                "pdk": pdk,
                "pdk_work": pdk_work
            })

        # Сохраняем в файл
        if self.save_data():
            self.accept()
