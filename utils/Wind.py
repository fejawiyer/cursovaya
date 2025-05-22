from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QSpacerItem, QTabWidget,
                             QSizePolicy, QMessageBox, QSpinBox, QWidget)
from PyQt5.QtCore import Qt
import json
import os


class WindRulesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wind Rules Editor (X/Y Components)")
        self.setMinimumSize(700, 500)
        self.wind_json_path = "wind.json"  # Path to the wind rules file

        # Try to load existing rules
        self.wind_x = {}  # {time_sec: wind_value}
        self.wind_y = {}  # {time_sec: wind_value}
        self.load_rules()

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Create tab widget for X and Y components
        self.tabs = QTabWidget()

        # Tab for X component
        self.tab_x = QWidget()
        self.initComponentTab(self.tab_x, 'X')
        self.tabs.addTab(self.tab_x, "X Component")

        # Tab for Y component
        self.tab_y = QWidget()
        self.initComponentTab(self.tab_y, 'Y')
        self.tabs.addTab(self.tab_y, "Y Component")

        layout.addWidget(self.tabs)

        # Common buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_accept)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Update tables with loaded data
        self.update_component_table('X')
        self.update_component_table('Y')

    def initComponentTab(self, tab, component):
        layout = QVBoxLayout(tab)

        # Table for current rules
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Time (seconds)", f"Wind {component} Value"])
        table.horizontalHeader().setStretchLastSection(True)

        # Store reference to the table
        setattr(self, f'table_{component.lower()}', table)
        layout.addWidget(table)

        # Form to add new rules
        form_layout = QHBoxLayout()

        time_edit = QSpinBox()
        time_edit.setMinimum(0)
        time_edit.setMaximum(86400)
        time_edit.setValue(0)
        form_layout.addWidget(QLabel("Time (sec):"))
        form_layout.addWidget(time_edit)
        setattr(self, f'time_edit_{component.lower()}', time_edit)

        wind_edit = QLineEdit()
        wind_edit.setPlaceholderText(f"Enter wind {component} value")
        form_layout.addWidget(QLabel(f"Wind {component} Value:"))
        form_layout.addWidget(wind_edit)
        setattr(self, f'wind_edit_{component.lower()}', wind_edit)

        add_button = QPushButton(f"Add {component} Rule")
        add_button.clicked.connect(lambda: self.add_rule(component))
        form_layout.addWidget(add_button)

        clear_button = QPushButton(f"Clear {component} Rules")
        clear_button.clicked.connect(lambda: self.clear_component_rules(component))
        form_layout.addWidget(clear_button)

        layout.addLayout(form_layout)

    def add_rule(self, component):
        time_sec = getattr(self, f'time_edit_{component.lower()}').value()
        wind_value = getattr(self, f'wind_edit_{component.lower()}').text()

        if not wind_value:
            QMessageBox.warning(self, "Warning", f"Please enter a wind {component} value")
            return

        # Add to appropriate dictionary
        getattr(self, f'wind_{component.lower()}')[time_sec] = wind_value

        # Update table
        self.update_component_table(component)

        # Clear input field
        getattr(self, f'wind_edit_{component.lower()}').clear()

    def update_component_table(self, component):
        table = getattr(self, f'table_{component.lower()}')
        rules = getattr(self, f'wind_{component.lower()}')

        table.setRowCount(len(rules))
        sorted_times = sorted(rules.keys())
        for row, time_sec in enumerate(sorted_times):
            table.setItem(row, 0, QTableWidgetItem(str(time_sec)))
            table.setItem(row, 1, QTableWidgetItem(rules[time_sec]))

    def clear_component_rules(self, component):
        setattr(self, f'wind_{component.lower()}', {})
        self.update_component_table(component)

    def load_rules(self):
        """Load wind rules from JSON file if it exists"""
        if os.path.exists(self.wind_json_path):
            try:
                with open(self.wind_json_path, 'r') as f:
                    data = json.load(f)

                    # Convert string keys to integers for both components
                    self.wind_x = {int(k): str(v) for k, v in data.get('wind_x', {}).items()}
                    self.wind_y = {int(k): str(v) for k, v in data.get('wind_y', {}).items()}

            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Failed to load wind rules: {str(e)}")

    def save_rules(self):
        """Save current wind rules to JSON file"""
        try:
            with open(self.wind_json_path, 'w') as f:
                # Create a custom encoder to handle the dictionary with integer keys
                class CustomEncoder(json.JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, dict):
                            return {str(k): v for k, v in obj.items()}
                        return super().default(obj)

                json.dump({
                    'wind_x': self.wind_x,
                    'wind_y': self.wind_y
                }, f, indent=4, cls=CustomEncoder)
            return True
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save wind rules: {str(e)}")
            return False

    def save_and_accept(self):
        """Save rules and close dialog if save was successful"""
        if self.save_rules():
            self.accept()

    def get_rules(self):
        return {
            'wind_x': self.wind_x.copy(),
            'wind_y': self.wind_y.copy()
        }