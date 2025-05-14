from PyQt5.QtWidgets import QVBoxLayout, QDialog, QLabel, QLineEdit, QDialogButtonBox, QCheckBox, QHBoxLayout, \
    QFileDialog, QPushButton


class NewConditions(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание начальных условий")

        try:
            self.h_layout_1 = QHBoxLayout()
            self.h_layout_2 = QHBoxLayout()
            self.h_layout_3 = QHBoxLayout()
            self.h_layout_4 = QHBoxLayout()
            self.h_layout_5 = QHBoxLayout()
            self.layout = QVBoxLayout(self)

            # Кнопка для выбора файла вместо поля ввода
            self.file_button = QPushButton("Выбрать файл...", self)
            self.file_button.clicked.connect(self.select_file)
            self.file_path = ""  # Здесь будет храниться путь к файлу
            self.h_layout_1.addWidget(self.file_button)

            self.toch_label = QLabel("Точечный источник", self)
            self.toch_label_checkbox = QCheckBox(self)
            self.toch_label_checkbox.stateChanged.connect(self.checkbox)
            self.h_layout_2.addWidget(self.toch_label)
            self.h_layout_2.addWidget(self.toch_label_checkbox)

            self.toch_x = QLineEdit()
            self.toch_y = QLineEdit()
            self.c = QLineEdit()
            self.repeat_freq = QLineEdit()
            self.repeat_label = QLabel("Частота повторения")
            self.const_checkbox_label = QLabel("Постоянный источник")
            self.const_checkbox = QCheckBox()
            self.toch_x.setPlaceholderText("x")
            self.toch_y.setPlaceholderText("y")
            self.c.setPlaceholderText("г/м^2")
            self.repeat_freq.setText("-1")

            self.layout.addLayout(self.h_layout_1)
            self.layout.addLayout(self.h_layout_2)
            self.layout.addLayout(self.h_layout_3)
            self.layout.addLayout(self.h_layout_4)
            self.layout.addLayout(self.h_layout_5)

            self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
            self.buttons.accepted.connect(self.accept)
            self.buttons.rejected.connect(self.reject)
            self.layout.addWidget(self.buttons)
        except Exception as e:
            print(f"{e}")

    def select_file(self):
        # Открываем диалоговое окно для сохранения файла
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл начальных условий",
            "",  # Начальная директория
            "Json Files (*.json)"  # Фильтры файлов
        )

        if file_path:
            self.file_path = file_path
            self.file_button.setText(file_path)  # Показываем выбранный путь на кнопке

    def getProperties(self):
        return (self.file_path, self.toch_label_checkbox.isChecked(), self.toch_x.text(),
                self.toch_y.text(), self.c.text(), self.const_checkbox.isChecked(),
                self.repeat_freq.text())

    def checkbox(self):
        if self.toch_label_checkbox.isChecked():
            self.h_layout_3.addWidget(self.toch_x)
            self.h_layout_3.addWidget(self.toch_y)
            self.h_layout_3.addWidget(self.c)
            self.h_layout_4.addWidget(self.const_checkbox_label)
            self.h_layout_4.addWidget(self.const_checkbox)
            self.h_layout_5.addWidget(self.repeat_label)
            self.h_layout_5.addWidget(self.repeat_freq)
        else:
            self.toch_x.setParent(None)
            self.toch_y.setParent(None)
            self.c.setParent(None)
            self.const_checkbox_label.setParent(None)
            self.const_checkbox.setParent(None)
            self.repeat_label.setParent(None)
            self.repeat_freq.setParent(None)
