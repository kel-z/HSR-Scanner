import win32gui
import keyboard
import mouse
import pyautogui
import time

class Navigation:

    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.x, self.y = win32gui.GetClientRect(self.hwnd)[2:]
        self.left, self.top = win32gui.ClientToScreen(self.hwnd, (0, 0))

    def bring_window_to_foreground(self):
        win32gui.ShowWindow(self.hwnd, 5)
        win32gui.SetForegroundWindow(self.hwnd)

    def move_cursor_to(self, x_percent, y_percent):
        x = self.left + int(self.x * x_percent)
        y = self.top + int(self.y * y_percent)

        mouse.move(x, y)

    def send_key_press(self, key):
        keyboard.press_and_release(key)

    def click(self):
        mouse.click()

    def drag_scroll(self, x, start_y, end_y):
        x = self.left + int(self.x * x)
        start_y = self.top + int(self.y * start_y)
        end_y = self.top + int(self.y * end_y)

        pyautogui.moveTo(x, start_y)
        pyautogui.mouseDown()
        pyautogui.dragTo(x, end_y, duration=1, mouseDownUp=False)
        time.sleep(0.5)
        pyautogui.mouseUp()


    def print_mouse_position(self):
        x_percent, y_percent = self.get_mouse_position()

        print("x: " + str(x_percent) + ", y: " + str(y_percent))

    def get_mouse_position(self):
        mouse_x, mouse_y = mouse.get_position()
        right, bottom = win32gui.ClientToScreen(self.hwnd, (self.x, self.y))

        x_percent = (mouse_x - self.left) / (right - self.left)
        y_percent = (mouse_y - self.top) / (bottom - self.top)

        return x_percent, y_percent

    def get_aspect_ratio(self):
        x, y = win32gui.GetClientRect(self.hwnd)[2:]
        gcd = self.gcd(x, y)
        return f"{x // gcd}:{y // gcd}"

    def gcd(self, a, b):
        while b:
            a, b = b, a % b
        return a
