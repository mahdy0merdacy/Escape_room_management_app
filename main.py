import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from erm import audio, database
from erm.dashboard import MainDashboardWindow


def main() -> None:
    database.init_db()
    audio.ensure_alert_sound()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # cross-platform style that respects custom CSS on Windows
    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainDashboardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    