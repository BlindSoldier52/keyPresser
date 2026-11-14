import ctypes
import os
import time
from ctypes import wintypes

from . import keymap

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
winmm = ctypes.WinDLL("winmm")

ULONG_PTR = wintypes.WPARAM

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000

XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
WHEEL_DELTA = 120

MAPVK_VK_TO_VSC = 0
VK_RETURN = 0x0D
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

SIGNATURE = 0x4B505253

SPIN_MARGIN = 0.002
PATH_LENGTH = 512
MAX_PATH_LENGTH = 32768

ERROR_ACCESS_DENIED = 5


class InputBlockedError(Exception):

	def __init__(self, code):
		super().__init__("SendInput was refused, Windows error %d" % code)
		self.code = code


class MOUSEINPUT(ctypes.Structure):
	_fields_ = (
		("dx", wintypes.LONG),
		("dy", wintypes.LONG),
		("mouseData", wintypes.DWORD),
		("dwFlags", wintypes.DWORD),
		("time", wintypes.DWORD),
		("dwExtraInfo", ULONG_PTR),
	)


class KEYBDINPUT(ctypes.Structure):
	_fields_ = (
		("wVk", wintypes.WORD),
		("wScan", wintypes.WORD),
		("dwFlags", wintypes.DWORD),
		("time", wintypes.DWORD),
		("dwExtraInfo", ULONG_PTR),
	)


class HARDWAREINPUT(ctypes.Structure):
	_fields_ = (
		("uMsg", wintypes.DWORD),
		("wParamL", wintypes.WORD),
		("wParamH", wintypes.WORD),
	)


class _InputUnion(ctypes.Union):
	_fields_ = (("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT))


class INPUT(ctypes.Structure):
	_anonymous_ = ("u",)
	_fields_ = (("type", wintypes.DWORD), ("u", _InputUnion))


user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.GetForegroundWindow.argtypes = ()
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (
	wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
)
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
winmm.timeBeginPeriod.argtypes = (wintypes.UINT,)
winmm.timeBeginPeriod.restype = wintypes.UINT
winmm.timeEndPeriod.argtypes = (wintypes.UINT,)
winmm.timeEndPeriod.restype = wintypes.UINT

_timerDepth = 0


def beginHighResolutionTimers():
	global _timerDepth
	if _timerDepth == 0:
		try:
			winmm.timeBeginPeriod(1)
		except Exception:
			return
	_timerDepth += 1


def endHighResolutionTimers():
	global _timerDepth
	if _timerDepth <= 0:
		return
	_timerDepth -= 1
	if _timerDepth > 0:
		return
	try:
		winmm.timeEndPeriod(1)
	except Exception:
		pass


def preciseSleep(seconds):
	if seconds <= 0:
		return
	deadline = time.perf_counter() + seconds
	remaining = seconds
	while remaining > 0:
		if remaining > SPIN_MARGIN:
			time.sleep(remaining - SPIN_MARGIN)
		else:
			time.sleep(0)
		remaining = deadline - time.perf_counter()


def _sendAll(inputs):
	if not inputs:
		return 0
	array = (INPUT * len(inputs))(*inputs)
	ctypes.set_last_error(0)
	sent = user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT))
	if sent < len(inputs):
		raise InputBlockedError(ctypes.get_last_error())
	return sent


def _release(inputs):
	try:
		_sendAll(inputs)
	except InputBlockedError:
		pass


def _keyInput(kind, code, keyUp, useScancode):
	entry = INPUT(type=INPUT_KEYBOARD)
	entry.ki.time = 0
	entry.ki.dwExtraInfo = SIGNATURE
	flags = KEYEVENTF_KEYUP if keyUp else 0
	if kind == "sc":
		entry.ki.wVk = 0
		entry.ki.wScan = code & 0xFF
		flags |= KEYEVENTF_SCANCODE
		if code > 0xFF:
			flags |= KEYEVENTF_EXTENDEDKEY
	else:
		scan = user32.MapVirtualKeyW(code, MAPVK_VK_TO_VSC)
		if keymap.isExtended(code):
			flags |= KEYEVENTF_EXTENDEDKEY
		if useScancode and scan:
			entry.ki.wVk = 0
			entry.ki.wScan = scan
			flags |= KEYEVENTF_SCANCODE
		else:
			entry.ki.wVk = code
			entry.ki.wScan = scan
	entry.ki.dwFlags = flags
	return entry


def sendChord(keys, holdSeconds, useScancode=True, sleep=preciseSleep):
	downs = [_keyInput(kind, code, False, useScancode) for kind, code in keys]
	ups = [_keyInput(kind, code, True, useScancode) for kind, code in reversed(keys)]
	try:
		_sendAll(downs)
		sleep(holdSeconds)
	finally:
		_release(ups)


def _unicodeInput(codeUnit, keyUp):
	entry = INPUT(type=INPUT_KEYBOARD)
	entry.ki.wVk = 0
	entry.ki.wScan = codeUnit
	entry.ki.time = 0
	entry.ki.dwExtraInfo = SIGNATURE
	entry.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if keyUp else 0)
	return entry


def sendText(text, delaySeconds=0.0, shouldStop=None, sleep=preciseSleep):
	for character in text:
		if shouldStop is not None and shouldStop():
			return
		if character == "\r":
			continue
		if character == "\n":
			sendChord([("vk", VK_RETURN)], 0.0)
			sleep(delaySeconds)
			continue
		units = []
		codePoint = ord(character)
		if codePoint > 0xFFFF:
			codePoint -= 0x10000
			units.append(0xD800 + (codePoint >> 10))
			units.append(0xDC00 + (codePoint & 0x3FF))
		else:
			units.append(codePoint)
		inputs = []
		for unit in units:
			inputs.append(_unicodeInput(unit, False))
		for unit in units:
			inputs.append(_unicodeInput(unit, True))
		_sendAll(inputs)
		sleep(delaySeconds)


MOUSE_BUTTONS = {
	"left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP, 0),
	"right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, 0),
	"middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP, 0),
	"x1": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON1),
	"x2": (MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, XBUTTON2),
}


def _mouseInput(flags, data=0):
	entry = INPUT(type=INPUT_MOUSE)
	entry.mi.dx = 0
	entry.mi.dy = 0
	entry.mi.mouseData = data
	entry.mi.dwFlags = flags
	entry.mi.time = 0
	entry.mi.dwExtraInfo = SIGNATURE
	return entry


def sendMouse(button, holdSeconds, sleep=preciseSleep):
	if button == "wheelup":
		_sendAll([_mouseInput(MOUSEEVENTF_WHEEL, WHEEL_DELTA)])
		return
	if button == "wheeldown":
		_sendAll([_mouseInput(MOUSEEVENTF_WHEEL, ctypes.c_uint32(-WHEEL_DELTA).value)])
		return
	down, up, data = MOUSE_BUTTONS.get(button, MOUSE_BUTTONS["left"])
	try:
		_sendAll([_mouseInput(down, data)])
		sleep(holdSeconds)
	finally:
		_release([_mouseInput(up, data)])


_foregroundCache = (None, "", 0.0)


def _queryExecutable(window):
	processId = wintypes.DWORD()
	user32.GetWindowThreadProcessId(window, ctypes.byref(processId))
	if not processId.value:
		return ""
	process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, processId.value)
	if not process:
		return ""
	try:
		for length in (PATH_LENGTH, MAX_PATH_LENGTH):
			size = wintypes.DWORD(length)
			buffer = ctypes.create_unicode_buffer(length)
			if kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
				return os.path.basename(buffer.value)
	finally:
		kernel32.CloseHandle(process)
	return ""


def getForegroundExecutable(maxAgeSeconds=0.0):
	global _foregroundCache
	window = user32.GetForegroundWindow()
	if not window:
		return ""
	cachedWindow, cachedName, cachedAt = _foregroundCache
	now = time.perf_counter()
	if cachedWindow == window and maxAgeSeconds > 0 and now - cachedAt < maxAgeSeconds:
		return cachedName
	name = _queryExecutable(window)
	_foregroundCache = (window, name, now)
	return name
