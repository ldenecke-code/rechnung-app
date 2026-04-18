"""
Desktop entry point: startet Flask im Hintergrund und öffnet ein natives Fenster.
Wird von PyInstaller als main-Skript verwendet.
"""
import threading
import time
import sys
import webview
from app import app as flask_app

PORT = 5000


def run_flask() -> None:
    flask_app.run(port=PORT, debug=False, use_reloader=False)


def main() -> None:
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    # Kurz warten, bis Flask bereit ist
    time.sleep(0.9)
    webview.create_window(
        "Cleancare Rechnung",
        f"http://localhost:{PORT}",
        width=980,
        height=860,
        resizable=True,
        min_size=(640, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
