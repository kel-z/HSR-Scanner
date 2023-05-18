import pyautogui
import win32gui

coords = {
    "16:9": {
        "light_cone": {
            "stats": (0.11, 0.72, 0.25, 0.41),
            "quantity": (0.89, 0.46, 0.13, 0.04),
        }
    }
}


class Screenshot:

    def __init__(self, hwnd, aspect_ratio="16:9"):
        self.aspect_ratio = aspect_ratio

        self.x, self.y = win32gui.GetClientRect(hwnd)[2:]
        self.left, self.top = win32gui.ClientToScreen(hwnd, (0, 0))

    def screenshot_light_cone(self, key="stats"):
        return self._take_screenshot(*coords[self.aspect_ratio]["light_cone"][key])

    def _take_screenshot(self, top, left, width, height):
        x = self.left + int(self.x * left)
        y = self.top + int(self.y * top)
        width = int(self.x * width)
        height = int(self.y * height)

        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        return screenshot
