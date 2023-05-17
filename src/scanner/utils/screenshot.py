import pyautogui
import win32gui


class Screenshot:

    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.x, self.y = win32gui.GetClientRect(self.hwnd)[2:]
        self.left, self.top = win32gui.ClientToScreen(self.hwnd, (0, 0))
        print(self.x, self.y, self.left, self.top)

    def screenshot_light_cone(self):
        return self.take_screenshot(0.11, 0.72, 0.25, 0.41)

    def take_screenshot(self, top, left, width, height):
        x = self.left + int(self.x * left)
        y = self.top + int(self.y * top)
        width = int(self.x * width)
        height = int(self.y * height)

        screenshot = pyautogui.screenshot(region=(x, y, width, height))

        return screenshot
