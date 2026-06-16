import sys

from PyQt6.QtWidgets import QApplication

from erm import audio, database
from erm.dashboard import MainDashboardWindow


def main() -> None:
    database.init_db()
    audio.ensure_alert_sound()

    app = QApplication(sys.argv)
    window = MainDashboardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    