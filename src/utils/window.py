import win32con
import win32gui


def flash_window(hwnd):
    """
    Flashes the taskbar icon of the specified window

    :param hwnd: Handle to the window to be flashed.
    """
    dwFlags = win32con.FLASHW_ALL | win32con.FLASHW_TIMERNOFG
    win32gui.FlashWindowEx(hwnd, dwFlags, 0, 0)


def bring_window_to_foreground(hwnd, cmd_show=win32con.SW_SHOW):
    """Bring the window to the foreground

    :param hwnd: Handle to the window.
    :param cmd_show: The command to show the window, defaults to win32con.SW_SHOW.
    """
    # certain UI states can cause this to fail, so catch the exception (i'm too lazy to figure this out atm)
    # e.g. start scan and then immediately cancel it
    try:
        win32gui.ShowWindow(hwnd, cmd_show)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
