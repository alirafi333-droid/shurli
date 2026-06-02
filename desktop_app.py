import sys
import threading
import time
import logging

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon

import gravity_poker

# Suppress Flask server output in the terminal
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def start_flask_server():
    """Run the Flask server on a dedicated port for the desktop app."""
    # Temporarily disable opening the default web browser 
    import webbrowser
    webbrowser.open = lambda *args, **kwargs: None
    
    gravity_poker.run_web_server(port=5055)

class DesktopPokerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gravity Flip Poker - Desktop Edition")
        self.setGeometry(100, 100, 1280, 800)
        self.setStyleSheet("background-color: #070913;")
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Embedded Chromium Web Engine
        self.browser = QWebEngineView()
        
        # Display a sleek loading message instantly
        self.browser.setHtml("<body style='background-color:#070913; color:#fcfcfd; font-family:sans-serif; text-align:center; padding-top:20vh;'><h2>Loading Casino Engine...</h2><p>Spinning up provably fair database and AI systems...</p></body>")
        
        from PyQt5.QtCore import QTimer
        import urllib.request
        import urllib.error
        
        def check_server():
            try:
                # Check if Flask has fully bound to the port
                urllib.request.urlopen("http://127.0.0.1:5055", timeout=1)
                self.browser.setUrl(QUrl("http://127.0.0.1:5055"))
            except Exception:
                # Try again in 500ms if not ready
                QTimer.singleShot(500, check_server)
                
        # Start the polling process
        QTimer.singleShot(500, check_server)
        
        layout.addWidget(self.browser)

if __name__ == "__main__":
    # 1. Start the Flask server in a daemon thread
    server_thread = threading.Thread(target=start_flask_server, daemon=True)
    server_thread.start()
    
    # 2. Launch the native PyQt5 Desktop Window INSTANTLY
    app = QApplication(sys.argv)
    window = DesktopPokerApp()
    window.show()
    sys.exit(app.exec_())
