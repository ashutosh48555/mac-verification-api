import sys
import requests
import json
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLabel, QMessageBox
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from pynput import keyboard
import google.generativeai as genai
import time
import win32gui
import win32con
import win32api
import psutil
import logging
from retry import retry

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Server URL
SERVER_URL = "https://mac-verification-api.vercel.app/api/verify"

def get_mac_addresses():
    mac_addresses = set()
    for _, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                mac = addr.address.replace(":", "-").upper()
                mac_addresses.add(mac)
    logging.debug("Retrieved MAC addresses: %s", mac_addresses)
    return mac_addresses

def verify_with_server():
    system_macs = get_mac_addresses()
    for mac in system_macs:
        try:
            response = requests.post(SERVER_URL, json={"mac_address": mac}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    return data["api_key"]
        except requests.RequestException as e:
            logging.error("Server verification failed: %s", e)
    return None

# Access control
api_key = verify_with_server()
if not api_key:
    logging.error("Access denied: Server verification failed")
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Access Denied", "This application cannot be run due to verification failure.")
    sys.exit(1)

def send_keys(hwnd, text):
    for char in text:
        win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
        time.sleep(0.05)

def auto_typer(text):
    hwnd = win32gui.GetForegroundWindow()
    if hwnd:
        lines = [line for line in text.split("\n") if line.strip()]
        if len(lines) <= 2:
            return
        for i in range(1, len(lines) - 1):
            current_line = lines[i].lstrip()
            send_keys(hwnd, current_line)
            time.sleep(0.05)
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
            time.sleep(0.05)
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
            time.sleep(0.05)
            current_indent = len(lines[i]) - len(lines[i].lstrip())
            next_indent = len(lines[i + 1]) - len(lines[i + 1].lstrip())
            if i + 1 < len(lines) - 1:
                current_line = lines[i + 1].lstrip()
                if not current_line.startswith(("else", "elif", "finally")):
                    backspaces = (max(0, current_indent - next_indent)) // 4
                    for _ in range(backspaces):
                        time.sleep(0.05)
                        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_BACK, 0)
                        time.sleep(0.05)
                        win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_BACK, 0)
                        time.sleep(0.05)

class ChatbotThread(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, prompt, api_key):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    @retry(tries=3, delay=1, backoff=2, logger=logging)
    def generate_response(self):
        return self.model.generate_content(
            self.prompt + "\nCheck if MCQ then provide only the correct answer from the available options. "
            "Respond strictly in the format: option label (answer), e.g., c (4/3). If options are unlabeled, "
            "assign labels sequentially: (a) for the first option, (b) for the second, and so on. "
            "Display the correct option along with its corresponding value. Do not provide any explanations—"
            "only the final answer in the specified format. Else it is problem statement with test cases then "
            "Generate a Python program While typing the program strictly do not add any white lines. "
            "It should handles all the shown and hidden test cases successfully. The program should include "
            "both input and output statements, ensuring correct functionality for all test cases. "
            "Keep the code simple and do not add any comments"
        )

    def run(self):
        try:
            response = self.generate_response()
            self.response_ready.emit(response.text.strip() if response else "No response received.")
        except Exception as e:
            logging.error("Error generating response: %s", e)
            self.response_ready.emit(f"Error: {e}")

class ChatbotUI(QWidget):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
        self.setWindowTitle("ExamHelper")
        self.setGeometry(100, 100, 400, 300)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("QMainWindow { color: white; }")
        self.is_stealth = False
        self.is_hidden = False
        self.generated_code = ""
        self.listener = None
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("white"))
        palette.setColor(QPalette.ColorRole.Base, QColor("white"))
        palette.setColor(QPalette.ColorRole.Text, QColor("black"))
        self.setPalette(palette)
        self.setStyleSheet("background-color: white; border: none;")
        self.layout = QVBoxLayout()
        self.label = QLabel("Press F2 to toggle visibility, F3 to toggle stealth mode, F4 to start typing.", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: black; font-size: 9px;")
        self.label.setWordWrap(True)
        self.layout.addWidget(self.label)
        self.text_input = QTextEdit(self)
        self.text_input.setStyleSheet("background-color: white; color: black; border: 1px solid gray; font-size: 14px;")
        self.text_input.setPlaceholderText("Drag and drop the question here\nYour buddy Exam helper helps you to solve the question\nall the best..\nTeam EncryptedX\nTelegram: EncryptedX1")
        self.layout.addWidget(self.text_input)
        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setStyleSheet("background-color: white; color: black; border: 1px solid gray; font-size: 14px;")
        self.layout.addWidget(self.output)
        self.setLayout(self.layout)
        self.send_timer = QTimer(self)
        self.send_timer.setSingleShot(True)
        self.send_timer.timeout.connect(self.get_response)
        self.text_input.textChanged.connect(self.start_send_timer)
        self.start_global_key_listener()

    def start_send_timer(self):
        self.send_timer.start(2000)

    def start_global_key_listener(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f2:
                    self.toggle_visibility()
                elif key == keyboard.Key.f3:
                    self.toggle_stealth_mode()
                elif key == keyboard.Key.f4:
                    self.start_typing()
            except AttributeError:
                pass
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()

    def toggle_visibility(self):
        if self.is_hidden:
            self.show()
            self.is_hidden = False
        else:
            self.hide()
            self.is_hidden = True

    def toggle_stealth_mode(self):
        self.setWindowOpacity(0.2 if not self.is_stealth else 1.0)
        self.is_stealth = not self.is_stealth

    def get_response(self):
        user_input = self.text_input.toPlainText().strip()
        if user_input:
            self.worker = ChatbotThread(user_input, self.api_key)
            self.worker.response_ready.connect(self.display_response)
            self.worker.start()
            self.output.setText("Thinking...")
            self.text_input.setDisabled(True)

    def display_response(self, response):
        self.output.setText(response)
        self.text_input.clear()
        self.text_input.setDisabled(False)
        self.generated_code = response

    def start_typing(self):
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            logging.error("No active window found for typing")
            self.output.setText("Error: No active window found for typing")
            return
        self.hide()
        auto_typer(self.generated_code)
        self.show()

    def closeEvent(self, event):
        if self.listener:
            self.listener.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotUI(api_key)
    window.show()
    sys.exit(app.exec())