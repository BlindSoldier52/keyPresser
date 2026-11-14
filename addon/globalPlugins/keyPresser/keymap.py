import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.VkKeyScanW.argtypes = (wintypes.WCHAR,)
user32.VkKeyScanW.restype = ctypes.c_short

VK_ALIASES = {
	"backspace": 0x08, "back": 0x08,
	"tab": 0x09,
	"clear": 0x0C,
	"enter": 0x0D, "return": 0x0D,
	"pause": 0x13, "break": 0x13,
	"capslock": 0x14,
	"escape": 0x1B, "esc": 0x1B,
	"space": 0x20, "spacebar": 0x20,
	"pageup": 0x21, "prior": 0x21,
	"pagedown": 0x22, "next": 0x22,
	"end": 0x23,
	"home": 0x24,
	"left": 0x25, "leftarrow": 0x25,
	"up": 0x26, "uparrow": 0x26,
	"right": 0x27, "rightarrow": 0x27,
	"down": 0x28, "downarrow": 0x28,
	"printscreen": 0x2C, "prtsc": 0x2C,
	"insert": 0x2D, "ins": 0x2D,
	"delete": 0x2E, "del": 0x2E,
	"leftwindows": 0x5B, "lwin": 0x5B, "win": 0x5B, "windows": 0x5B,
	"rightwindows": 0x5C, "rwin": 0x5C,
	"applications": 0x5D, "apps": 0x5D, "contextmenu": 0x5D,
	"numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63,
	"numpad4": 0x64, "numpad5": 0x65, "numpad6": 0x66, "numpad7": 0x67,
	"numpad8": 0x68, "numpad9": 0x69,
	"numpadmultiply": 0x6A, "numpadplus": 0x6B, "numpadadd": 0x6B,
	"numpadseparator": 0x6C, "numpadminus": 0x6D, "numpadsubtract": 0x6D,
	"numpaddecimal": 0x6E, "numpaddelete": 0x6E, "numpaddivide": 0x6F,
	"numlock": 0x90, "scrolllock": 0x91,
	"leftshift": 0xA0, "lshift": 0xA0,
	"rightshift": 0xA1, "rshift": 0xA1,
	"leftcontrol": 0xA2, "lcontrol": 0xA2, "lctrl": 0xA2,
	"rightcontrol": 0xA3, "rcontrol": 0xA3, "rctrl": 0xA3,
	"leftalt": 0xA4, "lalt": 0xA4,
	"rightalt": 0xA5, "ralt": 0xA5, "altgr": 0xA5,
	"volumemute": 0xAD, "volumedown": 0xAE, "volumeup": 0xAF,
	"medianexttrack": 0xB0, "mediaprevtrack": 0xB1,
	"mediastop": 0xB2, "mediaplaypause": 0xB3,
	"semicolon": 0xBA, "equals": 0xBB, "comma": 0xBC,
	"dash": 0xBD, "minus": 0xBD, "period": 0xBE, "dot": 0xBE,
	"slash": 0xBF, "graveaccent": 0xC0, "backquote": 0xC0,
	"openbracket": 0xDB, "leftbracket": 0xDB,
	"backslash": 0xDC,
	"closebracket": 0xDD, "rightbracket": 0xDD,
	"quote": 0xDE, "apostrophe": 0xDE,
}

for _i in range(10):
	VK_ALIASES[str(_i)] = 0x30 + _i
for _i in range(26):
	VK_ALIASES[chr(ord("a") + _i)] = 0x41 + _i
for _i in range(1, 25):
	VK_ALIASES["f%d" % _i] = 0x6F + _i

MODIFIER_ALIASES = {
	"ctrl": 0xA2, "control": 0xA2,
	"shift": 0xA0,
	"alt": 0xA4,
}

EXTENDED_VKS = frozenset({
	0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
	0x2C, 0x2D, 0x2E, 0x5B, 0x5C, 0x5D, 0x6F, 0x90,
	0xA3, 0xA5, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3,
})

VK_SHIFT = 0xA0
VK_CONTROL = 0xA2
VK_ALT = 0xA4


def isExtended(vk):
	return vk in EXTENDED_VKS


def resolveToken(token):
	token = token.strip()
	low = token.lower()
	if not low:
		raise ValueError("Empty key name.")
	if low.startswith("vk:"):
		return [("vk", _parseNumber(low[3:]))]
	if low.startswith("sc:"):
		return [("sc", _parseNumber(low[3:]))]
	if low in MODIFIER_ALIASES:
		return [("vk", MODIFIER_ALIASES[low])]
	if low in VK_ALIASES:
		return [("vk", VK_ALIASES[low])]
	if len(token) == 1:
		result = user32.VkKeyScanW(token)
		vk = result & 0xFF
		if result != -1 and vk:
			state = (result >> 8) & 0xFF
			keys = []
			if state & 1:
				keys.append(("vk", VK_SHIFT))
			if state & 2:
				keys.append(("vk", VK_CONTROL))
			if state & 4:
				keys.append(("vk", VK_ALT))
			keys.append(("vk", vk))
			return keys
	raise ValueError("Unknown key: %s" % token)


def _parseNumber(text):
	text = text.strip()
	try:
		value = int(text, 0)
	except ValueError:
		raise ValueError("Invalid numeric code: %s" % text)
	if not 0 <= value <= 0xFFFF:
		raise ValueError("Code out of range: %s" % text)
	return value


TEXT_PREFIX = "text:"


def escapeText(value):
	escaped = value.replace("\\", "\\\\").replace(",", "\\,").replace("|", "\\|")
	escaped = escaped.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
	body = escaped.rstrip(" ")
	return body + "\\s" * (len(escaped) - len(body))


def unescapeText(value):
	result = []
	pending = False
	for character in value:
		if pending:
			result.append({"n": "\n", "s": " "}.get(character, character))
			pending = False
		elif character == "\\":
			pending = True
		else:
			result.append(character)
	if pending:
		result.append("\\")
	return "".join(result)


def buildTextStep(value):
	return TEXT_PREFIX + escapeText(value)


def isTextStep(step):
	return step.strip().lower().startswith(TEXT_PREFIX)


def stepText(step):
	return unescapeText(step.strip()[len(TEXT_PREFIX):])


RANDOM_PREFIX = "random:"


def buildRandomStep(alternatives):
	return RANDOM_PREFIX + "|".join(alternatives)


def isRandomStep(step):
	return step.strip().lower().startswith(RANDOM_PREFIX)


def randomAlternatives(step):
	body = step.strip()[len(RANDOM_PREFIX):]
	return [part for part in splitEscaped(body, "|") if part]


def parseStep(part, allowRandom=True):
	low = part.lower()
	if low.startswith(RANDOM_PREFIX):
		if not allowRandom:
			raise ValueError("A random step cannot contain another random step.")
		alternatives = randomAlternatives(part)
		if len(alternatives) < 2:
			raise ValueError("A random step needs at least two options.")
		return ("random", [parseStep(alternative, False) for alternative in alternatives])
	if low.startswith(TEXT_PREFIX):
		value = stepText(part)
		if not value:
			raise ValueError("A text step is empty.")
		return ("text", value)
	if low.startswith("wait:"):
		try:
			milliseconds = int(low[5:].strip())
		except ValueError:
			raise ValueError("Invalid wait value: %s" % part)
		if milliseconds < 0:
			raise ValueError("Wait value cannot be negative.")
		return ("wait", milliseconds)
	keys = []
	for token in part.split("+"):
		if not token.strip():
			raise ValueError("Malformed key combination: %s" % part)
		keys.extend(resolveToken(token))
	seen = []
	for key in keys:
		if key not in seen:
			seen.append(key)
	return ("chord", seen)


def parseSpec(spec):
	steps = [parseStep(part) for part in splitSpec(spec)]
	if not steps:
		raise ValueError("No keys have been specified.")
	if not any(step[0] in ("chord", "text", "random") for step in steps):
		raise ValueError("The sequence contains only pauses.")
	return steps


def describeSpec(spec):
	steps = parseSpec(spec)
	presses = sum(1 for step in steps if step[0] in ("chord", "text", "random"))
	pauses = sum(1 for step in steps if step[0] == "wait")
	return presses, pauses


KEY_CATEGORIES = (
	("Letters", tuple((chr(ord("A") + index), chr(ord("a") + index)) for index in range(26))),
	("Digits", tuple((str(digit), str(digit)) for digit in range(10))),
	("Function keys", tuple(("F%d" % number, "f%d" % number) for number in range(1, 25))),
	("Navigation", (
		("Up arrow", "up"), ("Down arrow", "down"), ("Left arrow", "left"), ("Right arrow", "right"),
		("Home", "home"), ("End", "end"), ("Page up", "pageup"), ("Page down", "pagedown"),
	)),
	("Editing", (
		("Space", "space"), ("Enter", "enter"), ("Tab", "tab"), ("Escape", "escape"),
		("Backspace", "backspace"), ("Delete", "delete"), ("Insert", "insert"),
	)),
	("Numpad", (
		("Numpad 0", "numpad0"), ("Numpad 1", "numpad1"), ("Numpad 2", "numpad2"),
		("Numpad 3", "numpad3"), ("Numpad 4", "numpad4"), ("Numpad 5", "numpad5"),
		("Numpad 6", "numpad6"), ("Numpad 7", "numpad7"), ("Numpad 8", "numpad8"),
		("Numpad 9", "numpad9"), ("Numpad plus", "numpadplus"), ("Numpad minus", "numpadminus"),
		("Numpad multiply", "numpadmultiply"), ("Numpad divide", "numpaddivide"),
		("Numpad decimal", "numpaddecimal"),
	)),
	("Modifier keys", (
		("Shift", "shift"), ("Control", "ctrl"), ("Alt", "alt"), ("Windows", "win"),
		("Left shift", "leftshift"), ("Right shift", "rightshift"),
		("Left control", "leftcontrol"), ("Right control", "rightcontrol"),
		("Left alt", "leftalt"), ("Right alt or AltGr", "altgr"),
		("Applications", "applications"),
	)),
	("Locks and system", (
		("Caps lock", "capslock"), ("Num lock", "numlock"), ("Scroll lock", "scrolllock"),
		("Print screen", "printscreen"), ("Pause", "pause"),
	)),
	("Media", (
		("Mute", "volumemute"), ("Volume down", "volumedown"), ("Volume up", "volumeup"),
		("Next track", "medianexttrack"), ("Previous track", "mediaprevtrack"),
		("Stop", "mediastop"), ("Play or pause", "mediaplaypause"),
	)),
	("Punctuation", (
		("Semicolon", "semicolon"), ("Equals", "equals"), ("Comma", "comma"),
		("Minus", "dash"), ("Period", "period"), ("Slash", "slash"),
		("Grave accent", "graveaccent"), ("Opening bracket", "openbracket"),
		("Backslash", "backslash"), ("Closing bracket", "closebracket"), ("Quote", "quote"),
	)),
)

MODIFIER_ORDER = ("ctrl", "shift", "alt", "win")
MODIFIER_TOKENS = {"ctrl", "control", "shift", "alt", "win", "windows"}

DISPLAY_NAMES = {}
for _category, _entries in KEY_CATEGORIES:
	for _label, _spec in _entries:
		DISPLAY_NAMES.setdefault(_spec, _label)


def splitEscaped(text, separator):
	parts = []
	current = []
	escaped = False
	for character in text:
		if escaped:
			current.append(character)
			escaped = False
			continue
		if character == "\\":
			current.append(character)
			escaped = True
			continue
		if character == separator:
			parts.append("".join(current).strip())
			current = []
			continue
		current.append(character)
	parts.append("".join(current).strip())
	return [part for part in parts if part]


def splitSpec(spec):
	return splitEscaped(spec, ",")


def joinSteps(steps):
	return ", ".join(steps)


def describeToken(token):
	low = token.strip().lower()
	if low in DISPLAY_NAMES:
		return DISPLAY_NAMES[low]
	if low in ("control",):
		return "Control"
	if low in ("windows",):
		return "Windows"
	return token.strip()


def describeStep(step):
	low = step.strip().lower()
	if low.startswith("wait:"):
		return "Pause %s ms" % low[5:].strip()
	if low.startswith(TEXT_PREFIX):
		value = stepText(step).replace("\n", " / ")
		if len(value) > 60:
			value = value[:57] + "..."
		return "Type: %s" % value
	if low.startswith(RANDOM_PREFIX):
		alternatives = randomAlternatives(step)
		shown = "; ".join(describeStep(alternative) for alternative in alternatives)
		if len(shown) > 70:
			shown = shown[:67] + "..."
		return "Random, %d options: %s" % (len(alternatives), shown)
	return " plus ".join(describeToken(token) for token in step.split("+"))


def splitStep(step):
	modifiers = []
	base = ""
	for token in step.split("+"):
		token = token.strip()
		if token.lower() in MODIFIER_TOKENS and token != step.strip():
			modifiers.append(token.lower())
		else:
			base = token
	if not base and modifiers:
		base = modifiers.pop()
	return modifiers, base


def buildStep(modifiers, base):
	ordered = [name for name in MODIFIER_ORDER if name in modifiers]
	return "+".join(ordered + [base])


def findCategory(base):
	low = base.strip().lower()
	for index, (category, entries) in enumerate(KEY_CATEGORIES):
		for position, (label, spec) in enumerate(entries):
			if spec == low:
				return index, position
	return -1, -1
