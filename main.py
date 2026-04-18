"""
Desktop entry point: startet Flask im Hintergrund und öffnet ein natives Fenster.
Wird von PyInstaller als main-Skript verwendet.
"""
import base64
import os
import threading
import time
import webview
from app import app as flask_app

PORT = 5000


class Api:
    """Wird als window.pywebview.api in JavaScript verfügbar."""

    def save_pdf(self, b64data: str, default_filename: str) -> dict:
        """Zeigt einen nativen Speichern-Dialog und schreibt das PDF."""
        result = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=default_filename,
            file_types=("PDF Datei (*.pdf)",),
        )
        if not result:
            return {"success": False, "cancelled": True}
        filepath = result[0]
        if not filepath.lower().endswith(".pdf"):
            filepath += ".pdf"
        with open(filepath, "wb") as fh:
            fh.write(base64.b64decode(b64data))
        return {"success": True, "filename": os.path.basename(filepath), "path": filepath}


def run_flask() -> None:
    flask_app.run(port=PORT, debug=False, use_reloader=False)


def main() -> None:
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    time.sleep(0.9)
    webview.create_window(
        "Cleancare Rechnung",
        f"http://localhost:{PORT}",
        width=980,
        height=860,
        resizable=True,
        min_size=(640, 600),
        js_api=Api(),
    )
    webview.start()


if __name__ == "__main__":
    main()
