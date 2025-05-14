import json
import os
import numpy as np
import sys
import logging
from PyQt5.QtWidgets import (QWidget, QLabel, QApplication, QMenuBar, QDesktopWidget, QAction, QDialog, QGridLayout,
                             QVBoxLayout, QLineEdit, QPushButton, QFileDialog, QProgressBar, QComboBox, QCheckBox)
from utils.Conditions import NewConditions
from utils.Model import Model
from utils.Render_tools import SaveMPCAnimation, SaveDefaultAnimation
from utils.Plotting import MPCPlot, DefaultPlot
from tkinter.messagebox import showerror


class App(QWidget):
    def __init__(self):
        super().__init__()

        try:
            self.load_stylesheet("style.qss")
        except FileNotFoundError:
            showerror("Ошибка", "Файл style.qss не найден.")
            logging.error("style.qss is not found")

        self.resize(1280, 720)
        self.center()
        self.setWindowTitle("Application")

        self.menuBar = QMenuBar(self)

        self.projectMenu = self.menuBar.addMenu('&Модель')
        createNewFileAction = QAction("Новая...", self)
        openFileAction = QAction("Открыть...", self)
        saveFileAction = QAction("Сохранить", self)

        self.c_start = self.menuBar.addMenu('&Начальные условия')
        createNewCStart = QAction("Новые...", self)

        createNewFileAction.triggered.connect(self.newFileDialog)
        openFileAction.triggered.connect(self.openFileDialog)
        saveFileAction.triggered.connect(self.saveFile)

        createNewCStart.triggered.connect(self.createNewConditions)

        self.projectMenu.addAction(createNewFileAction)
        self.projectMenu.addAction(openFileAction)
        self.projectMenu.addAction(saveFileAction)

        self.c_start.addAction(createNewCStart)

        self.main_layout = QVBoxLayout()
        self.main_layout.setMenuBar(self.menuBar)
        self.grid_layout = QGridLayout()

        self.x_size_label = QLabel("Введите размеры области в ширину (м)")
        self.x_size_input = QLineEdit()

        self.y_size_label = QLabel("Введите размеры области в длину (м)")
        self.y_size_input = QLineEdit()

        self.t_label = QLabel("Введите длительность моделирования (с)")
        self.t_input = QLineEdit()

        self.x_step_label = QLabel("Введите шаг по X (м)")
        self.x_step_input = QLineEdit()

        self.y_step_label = QLabel("Введите шаг по Y (м)")
        self.y_step_input = QLineEdit()

        self.t_step_label = QLabel("Введите шаг по времени (с)")
        self.t_step_input = QLineEdit()

        self.dx_label = QLabel("Введите коэф. диффузии вдоль X")
        self.dx_input = QLineEdit()

        self.dy_label = QLabel("Введите коэф. диффузии вдоль Y")
        self.dy_input = QLineEdit()

        self.wind_u_label = QLabel("Введите средний ветер вдоль X")
        self.wind_u_input = QLineEdit()

        self.wind_v_label = QLabel("Введите средний ветер вдоль Y")
        self.wind_v_input = QLineEdit()

        self.int_label = QLabel("Введите интервал анимации (мс)")
        self.int_input = QLineEdit()

        self.save_label = QLabel("Введите частоту сохранения")
        self.save_input = QLineEdit()

        self.initial_conditions_file = QPushButton("Выберите файл с начальными условиями")

        self.iterate_button = QPushButton("Моделирование")

        self.ok_button = QPushButton("Просмотр")

        self.save_button = QPushButton("Сохранить")

        self.update_c_label = QLabel("Обновлять шкалы ветра и концентрации")
        self.update_c_radio = QCheckBox()

        self.use_mpc = QLabel("Использовать ПДК")
        self.use_mpc_check = QCheckBox()
        self.use_mpc_check.stateChanged.connect(self.mpc_check)

        self.work_zone = QLabel("Рабочая зона")
        self.work_zone_check = QCheckBox()

        self.work_zone.hide()
        self.work_zone_check.hide()

        self.substances_data = []
        self.substance_names = []
        self.load_substances()
        self.pdk_values = {sub['name']: sub['pdk'] for sub in self.substances_data}
        self.pdk_work_values = {sub['name']: sub['pdk_work'] for sub in self.substances_data}

        self.select_substance = QComboBox()

        if hasattr(self, 'substance_names') and self.substance_names:
            self.select_substance.addItems(self.substance_names)
        else:
            self.select_substance.addItems(["Аммиак"])

        self.substance_label = QLabel("Вещество")

        self.save_list = QComboBox()
        self.save_list.addItems([".gif", ".html"])

        self.interpolation_method = QComboBox()
        self.interpolation_method.addItems(["Ступенчатая интерполяция", "Билинейная интерполяция"])

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.grid_layout.addWidget(self.x_size_label, 2, 2)
        self.grid_layout.addWidget(self.x_size_input, 2, 3)
        self.grid_layout.addWidget(self.y_size_label, 2, 4)
        self.grid_layout.addWidget(self.y_size_input, 2, 5)
        self.grid_layout.addWidget(self.t_label, 2, 6)
        self.grid_layout.addWidget(self.t_input, 2, 7)

        self.grid_layout.addWidget(self.x_step_label, 3, 2)
        self.grid_layout.addWidget(self.x_step_input, 3, 3)
        self.grid_layout.addWidget(self.y_step_label, 3, 4)
        self.grid_layout.addWidget(self.y_step_input, 3, 5)
        self.grid_layout.addWidget(self.t_step_label, 3, 6)
        self.grid_layout.addWidget(self.t_step_input, 3, 7)

        self.grid_layout.addWidget(self.wind_u_label, 4, 2)
        self.grid_layout.addWidget(self.wind_u_input, 4, 3)
        self.grid_layout.addWidget(self.wind_v_label, 4, 4)
        self.grid_layout.addWidget(self.wind_v_input, 4, 5)
        self.grid_layout.addWidget(self.int_label, 4, 6)
        self.grid_layout.addWidget(self.int_input, 4, 7)

        self.grid_layout.addWidget(self.dx_label, 5, 2)
        self.grid_layout.addWidget(self.dx_input, 5, 3)
        self.grid_layout.addWidget(self.dy_label, 5, 4)
        self.grid_layout.addWidget(self.dy_input, 5, 5)
        self.grid_layout.addWidget(self.save_label, 5, 6)
        self.grid_layout.addWidget(self.save_input, 5, 7)

        self.grid_layout.addWidget(self.initial_conditions_file, 6, 2)
        self.grid_layout.addWidget(self.interpolation_method, 6, 4)

        self.grid_layout.addWidget(self.iterate_button, 7, 2)
        self.grid_layout.addWidget(self.use_mpc, 7, 4)
        self.grid_layout.addWidget(self.use_mpc_check, 7, 5)

        self.grid_layout.addWidget(self.ok_button, 8, 2)
        self.grid_layout.addWidget(self.substance_label, 8, 4)
        self.grid_layout.addWidget(self.select_substance, 8, 5)
        self.grid_layout.addWidget(self.update_c_label, 8, 4)
        self.grid_layout.addWidget(self.update_c_radio, 8, 5)

        self.grid_layout.addWidget(self.save_list, 9, 2)
        self.grid_layout.addWidget(self.work_zone, 9, 4)
        self.grid_layout.addWidget(self.work_zone_check, 9, 5)

        self.select_substance.hide()
        self.substance_label.hide()

        self.grid_layout.addWidget(self.save_button, 10, 2)

        self.grid_layout.addWidget(self.progress_bar, 11, 2)

        self.initial_conditions_file.clicked.connect(self.select_conditions)
        self.iterate_button.clicked.connect(self.iterate)
        self.ok_button.clicked.connect(self.show_it)
        self.save_button.clicked.connect(self.save_it)

        self.x_size = self.y_size = self.x_step = self.y_step = self.Dx = self.Dy = self.u = self.v = self.t \
            = self.t_step = self.anim_int = self.freq = self.x = self.y = self.c = self.is_const_generation \
            = self.repeat_freq = self.condit_start = self.update_conc = None

        self.npz_exists = os.path.isfile("model.npz")

        self.mpc_use = False

        self.setLayout(self.main_layout)
        self.show()

    def mpc_check(self):
        if self.use_mpc_check.isChecked():
            self.mpc_use = True
            self.substance_label.show()
            self.select_substance.show()
            self.work_zone_check.show()
            self.work_zone.show()
            self.update_c_label.hide()
            self.update_c_radio.hide()
        else:
            self.mpc_use = False
            self.substance_label.hide()
            self.select_substance.hide()
            self.work_zone.hide()
            self.work_zone_check.hide()
            self.update_c_label.show()
            self.update_c_radio.show()

    def get_current_pdk(self):
        current_substance = self.select_substance.currentText()
        if self.work_zone_check.isChecked():
            return self.pdk_work_values.get(current_substance, 0.0)
        return self.pdk_values.get(current_substance, 0.0)

    def load_substances(self):
        try:
            with open('substances.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.substances_data = data['substances']
                self.substance_names = [sub['name'] for sub in self.substances_data]
        except FileNotFoundError:
            print("Файл substances.json не найден")
            self.substances_data = []
            self.substance_names = ["Ртуть"]

    def get_params(self):
        try:
            self.x_size = float(self.x_size_input.text())
            self.y_size = float(self.y_size_input.text())
            self.x_step = float(self.x_step_input.text())
            self.y_step = float(self.y_step_input.text())
            self.Dx = float(self.dx_input.text())
            self.Dy = float(self.dy_input.text())
            self.u = float(self.wind_u_input.text())
            self.v = float(self.wind_v_input.text())
            self.t = float(self.t_input.text())
            self.t_step = float(self.t_step_input.text())
            self.anim_int = int(self.int_input.text())
            self.freq = int(self.save_input.text())
            c_start_file = str(self.initial_conditions_file.text())
            with open(c_start_file.replace("/", "\\"), "r") as config:
                config_data = json.load(config)
                if "x" in config_data:
                    self.x = float(config_data["x"])
                if "y" in config_data:
                    self.y = float(config_data["y"])
                if "c" in config_data:
                    self.c = float(config_data["c"])
                if "is_const_generation":
                    self.is_const_generation = bool(config_data["is_const_generation"])
                if "repeat_freq":
                    self.repeat_freq = int(config_data["repeat_freq"])
            self.condit_start = np.zeros((int(self.x_size), int(self.y_size)))
            self.condit_start[int(self.x)][int(self.y)] = self.c
            self.update_conc = self.update_c_radio.isChecked()
        except Exception as e:
            logging.error(f"{e}")

    def select_conditions(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл начальных условий",
            "",  # Начальная директория
            "JSON Files (*.json)"  # Фильтры файлов
        )
        if file_path:
            self.initial_conditions_file.setText(file_path)

    def load_stylesheet(self, filepath):
        try:
            with open(filepath, "r") as f:
                stylesheet = f.read()
                self.setStyleSheet(stylesheet)
        except Exception as e:
            logging.error(f"Error loading stylesheet: {e}")

    def center(self):
        qr = self.frameGeometry()
        centralPoint = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(centralPoint)
        self.move(qr.topLeft())

    def clear_layout(self, layout):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is not None:
                if isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(False)
                elif isinstance(widget, QComboBox):
                    widget.setCurrentIndex(0)
            else:
                nested_layout = layout.itemAt(i).layout()
                if nested_layout is not None:
                    self.clear_layout(nested_layout)

    def newFileDialog(self):
        self.clear_layout(self.grid_layout)
        self.main_layout.addLayout(self.grid_layout)

    def createNewConditions(self):
        dialog = NewConditions(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                parameters = dialog.getProperties()
                config_data = {
                    "is_const_source": bool(parameters[1]),
                    "x": str(parameters[2]),
                    "y": str(parameters[3]),
                    "c": str(parameters[4]),
                    "is_const_generation": bool(parameters[5]),
                    "repeat_freq": str(parameters[6])
                }
                with open(str(parameters[0]).replace("/", "\\"), "w") as config:
                    json.dump(config_data, config, indent=4)
            except Exception as e:
                logging.error(f"{e}")

    def saveFile(self):
        data = {
            "x_size": self.x_size_input.text(),
            "y_size": self.y_size_input.text(),
            "t": self.t_input.text(),
            "x_step": self.x_step_input.text(),
            "y_step": self.y_step_input.text(),
            "t_step": self.t_step_input.text(),
            "dx": self.dx_input.text(),
            "wind_v": self.wind_v_input.text(),
            "intensity": self.int_input.text(),
            "wind_u": self.wind_u_input.text(),
            "dy": self.dy_input.text(),
            "save_name": self.save_input.text(),
            "initial_conditions": self.initial_conditions_file.text(),
            "update_conc": self.update_c_radio.isChecked(),
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)

    def openFileDialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                self.x_size_input.setText(str(data.get("x_size", "")))
                self.y_size_input.setText(str(data.get("y_size", "")))
                self.t_input.setText(str(data.get("t", "")))
                self.x_step_input.setText(str(data.get("x_step", "")))
                self.y_step_input.setText(str(data.get("y_step", "")))
                self.t_step_input.setText(str(data.get("t_step", "")))
                self.dx_input.setText(str(data.get("dx", "")))
                self.wind_v_input.setText(str(data.get("wind_v", "")))
                self.int_input.setText(str(data.get("intensity", "")))
                self.wind_u_input.setText(str(data.get("wind_u", "")))
                self.dy_input.setText(str(data.get("dy", "")))
                self.save_input.setText(str(data.get("save_name", "")))
                self.initial_conditions_file.setText(str(data.get("initial_conditions", "")))
                self.update_c_radio.setChecked(bool(data.get("update_conc")))

                if self.grid_layout not in self.main_layout.children():
                    self.main_layout.addLayout(self.grid_layout)

            except Exception as e:
                showerror("Error", f"Failed to load file:\n{str(e)}")

    def iterate(self):
        self.get_params()
        try:
            model = Model(self.condit_start, self.x_size, self.y_size, int(self.x_size), int(self.y_size), int(self.t),
                          self.Dx, self.Dy, self.x_step, self.y_step, self.t_step, int(self.u), int(self.v), self.freq,
                          self.anim_int, repeat_freq=self.repeat_freq, repeat_start_conditions=self.is_const_generation)
            model.iterate()
            res = model.c_list
            np.savez("model.npz", res=res)

        except Exception as e:
            logging.error(f"{e}")

    def show_it(self):
        if self.npz_exists is False:
            self.iterate()
        self.get_params()
        try:
            zoning = True if self.interpolation_method.currentText() == "Билинейная интерполяция" else False
            if self.mpc_use:
                plot = MPCPlot(self.anim_int, self.is_const_generation, self.x_size, self.y_size,
                               self.get_current_pdk(), zoning=zoning)
                plot.draw()
            else:
                plot = DefaultPlot(self.anim_int, self.is_const_generation, self.x_size, self.y_size,
                                   update_conc=self.update_conc, zoning=zoning)
                plot.draw()
        except Exception as e:
            logging.error(f"{e}")

    def save_it(self):
        self.get_params()
        output = "anime" + self.save_list.currentText()
        try:
            zoning = True if self.interpolation_method.currentText() == "Билинейная интерполяция" else False
            if self.mpc_use:
                saver = SaveMPCAnimation(anim_int=self.anim_int, repeat=self.is_const_generation, x_size=self.x_size,
                                         y_size=self.y_size, mpc=self.get_current_pdk(), output_file=output,
                                         zoning=zoning, progress_bar=self.progress_bar)
                saver.save()
            else:
                saver = SaveDefaultAnimation(anim_int=self.anim_int, repeat=self.is_const_generation,
                                             x_size=self.x_size, y_size=self.y_size, output_file=output,
                                             zoning=zoning, progress_bar=self.progress_bar)
                saver.save()
        except Exception as e:
            logging.error(f"{e}")


if __name__ == '__main__':
    logging.basicConfig(filename='app.log',
                        level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    QApp = QApplication(sys.argv)
    app = App()
    sys.exit(QApp.exec_())
