from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton
)
from PyQt5.QtCore import QTimer
import sys
from add_album import add_album

class AlbumWindow(QWidget):

    def __init__(self):

        super().__init__()
        self.setWindowTitle("Add Album URL")
        self.setGeometry(100, 100, 400, 150)
        self.setup_ui()

    def setup_ui(self):

        layout = QVBoxLayout()
        self.label = QLabel("Enter your album URL here:")
        layout.addWidget(self.label)

        self.url_input = QLineEdit()
        layout.addWidget(self.url_input)

        self.add_button = QPushButton("Add Album")
        self.add_button.clicked.connect(self.handle_add_album)
        layout.addWidget(self.add_button)
        self.setLayout(layout)

    def handle_add_album(self):
        
        album_url = self.url_input.text()
        
        if album_url:
            album_added = add_album(url = album_url)

            if album_added:
                self.label.setText("Album added successfully!")

            else:
                self.label.setText("Invalid album url")
            QTimer.singleShot(3000, lambda: self.label.setText("Enter your album URL here:"))
            QTimer.singleShot(3000, lambda: self.url_input.clear())
        else:
            self.label.setText("No album entered. Please enter a URL.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlbumWindow()
    window.show()
    sys.exit(app.exec_())