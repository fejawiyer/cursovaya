from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QMessageBox
from PyQt5.QtCore import QFile, QTextStream, QIODevice


class LogViewerDialog(QDialog):
    def __init__(self, logs_dir, parent=None):
        super().__init__(parent)
        self.logs_dir = logs_dir
        self.setWindowTitle("Просмотр логов")
        self.resize(800, 600)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        self.load_default_log()

    def load_default_log(self):
        log_file = QFile(str(self.logs_dir))
        if log_file.exists():
            if log_file.open(QIODevice.ReadOnly | QIODevice.Text):
                stream = QTextStream(log_file)
                self.text_edit.setPlainText(stream.readAll())
                log_file.close()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось открыть файл app.log")
