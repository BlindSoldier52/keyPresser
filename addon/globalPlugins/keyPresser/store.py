import copy
import json
import os

import globalVars
from logHandler import log

from . import keymap

CONFIG_FOLDER = "keyPresser"
CONFIG_FILE = "settings.json"

DEFAULT_SEQUENCE = {
	"name": "Sequence 1",
	"enabled": True,
	"steps": "space",
}

DEFAULT_PROFILE = {
	"name": "Default",
	"mode": "keys",
	"mouseButton": "left",
	"intervalMs": 1000,
	"jitterMs": 0,
	"holdMs": 30,
	"stepDelayMs": 60,
	"typingDelayMs": 20,
	"repetitions": 0,
	"startDelayMs": 3000,
	"countdown": True,
	"maxRuntimeSec": 0,
	"sendMethod": "scancode",
	"appFilter": "",
	"beep": True,
	"speak": True,
	"muteTypedCharacters": True,
	"announceProgress": 0,
}

INTEGER_FIELDS = (
	"intervalMs", "jitterMs", "holdMs", "stepDelayMs", "typingDelayMs", "repetitions",
	"startDelayMs", "maxRuntimeSec", "announceProgress",
)
BOOLEAN_FIELDS = ("countdown", "beep", "speak", "muteTypedCharacters")
TEXT_FIELDS = ("name", "mode", "mouseButton", "sendMethod", "appFilter")

MODE_VALUES = ("keys", "mouse")
MOUSE_BUTTON_VALUES = ("left", "right", "middle", "x1", "x2", "wheelup", "wheeldown")
SEND_METHOD_VALUES = ("scancode", "virtual")

LIMITS = {
	"intervalMs": (1, 3600000),
	"jitterMs": (0, 600000),
	"holdMs": (0, 60000),
	"stepDelayMs": (0, 600000),
	"typingDelayMs": (0, 60000),
	"repetitions": (0, 1000000),
	"startDelayMs": (0, 600000),
	"maxRuntimeSec": (0, 86400),
	"announceProgress": (0, 1000000),
}


def newProfile(name):
	profile = copy.deepcopy(DEFAULT_PROFILE)
	profile["name"] = name
	profile["sequences"] = [copy.deepcopy(DEFAULT_SEQUENCE)]
	return profile


def newSequence(name, steps=None):
	sequence = copy.deepcopy(DEFAULT_SEQUENCE)
	sequence["name"] = name
	if steps is not None:
		sequence["steps"] = steps
	return sequence


def sanitizeSequences(raw, legacySteps):
	sequences = []
	items = raw.get("sequences")
	if isinstance(items, list):
		for item in items:
			if not isinstance(item, dict):
				continue
			steps = item.get("steps")
			if not isinstance(steps, str) or not steps.strip():
				continue
			name = item.get("name")
			if not isinstance(name, str) or not name.strip():
				name = "Sequence %d" % (len(sequences) + 1)
			sequences.append({
				"name": name,
				"enabled": bool(item.get("enabled", True)),
				"steps": steps,
			})
	if not sequences:
		sequences.append(newSequence("Sequence 1", legacySteps or DEFAULT_SEQUENCE["steps"]))
	return sequences


def sanitizeProfile(raw):
	profile = copy.deepcopy(DEFAULT_PROFILE)
	if not isinstance(raw, dict):
		return profile
	for field in TEXT_FIELDS:
		value = raw.get(field)
		if isinstance(value, str):
			profile[field] = value
	for field in BOOLEAN_FIELDS:
		value = raw.get(field)
		if isinstance(value, bool):
			profile[field] = value
	for field in INTEGER_FIELDS:
		value = raw.get(field)
		try:
			value = int(value)
		except (TypeError, ValueError):
			continue
		low, high = LIMITS[field]
		profile[field] = max(low, min(high, value))
	legacySteps = raw.get("keys")
	if not isinstance(legacySteps, str):
		legacySteps = ""
	if profile["mode"] == "text":
		profile["mode"] = "keys"
		legacy = raw.get("text")
		if isinstance(legacy, str) and legacy:
			legacySteps = keymap.buildTextStep(legacy)
	if profile["mode"] not in MODE_VALUES:
		profile["mode"] = MODE_VALUES[0]
	profile["sequences"] = sanitizeSequences(raw, legacySteps)
	if profile["sendMethod"] not in SEND_METHOD_VALUES:
		profile["sendMethod"] = SEND_METHOD_VALUES[0]
	if profile["mouseButton"] not in MOUSE_BUTTON_VALUES:
		profile["mouseButton"] = MOUSE_BUTTON_VALUES[0]
	if not profile["name"].strip():
		profile["name"] = "Default"
	return profile


class SettingsStore:

	def __init__(self):
		self.folder = os.path.join(globalVars.appArgs.configPath, CONFIG_FOLDER)
		self.path = os.path.join(self.folder, CONFIG_FILE)
		self.warningAccepted = False
		self.activeProfileIndex = 0
		self.profiles = [newProfile("Default")]
		self.load()

	def load(self):
		try:
			with open(self.path, "r", encoding="utf-8") as source:
				data = json.load(source)
		except FileNotFoundError:
			return
		except (OSError, ValueError):
			log.error("Key Presser could not read %s, using the defaults" % self.path, exc_info=True)
			return
		if not isinstance(data, dict):
			return
		self.warningAccepted = bool(data.get("warningAccepted", False))
		profiles = data.get("profiles")
		if isinstance(profiles, list) and profiles:
			self.profiles = [sanitizeProfile(item) for item in profiles]
		self.setActiveByName(data.get("activeProfile", ""))

	def save(self):
		data = {
			"warningAccepted": self.warningAccepted,
			"activeProfile": self.activeProfile["name"],
			"profiles": self.profiles,
		}
		temporary = self.path + ".tmp"
		try:
			os.makedirs(self.folder, exist_ok=True)
			with open(temporary, "w", encoding="utf-8") as target:
				json.dump(data, target, indent="\t")
			os.replace(temporary, self.path)
		except OSError:
			log.error("Key Presser could not save %s" % self.path, exc_info=True)

	@property
	def activeProfile(self):
		if not self.profiles:
			self.profiles = [newProfile("Default")]
		if not 0 <= self.activeProfileIndex < len(self.profiles):
			self.activeProfileIndex = 0
		return self.profiles[self.activeProfileIndex]

	@property
	def profileNames(self):
		return [profile["name"] for profile in self.profiles]

	def setActiveByName(self, name):
		for index, profile in enumerate(self.profiles):
			if profile["name"] == name:
				self.activeProfileIndex = index
				return True
		return False

	def selectNextProfile(self):
		if len(self.profiles) < 2:
			return self.activeProfile
		self.activeProfileIndex = (self.activeProfileIndex + 1) % len(self.profiles)
		self.save()
		return self.activeProfile

	def uniqueName(self, wanted):
		existing = set(self.profileNames)
		if wanted not in existing:
			return wanted
		counter = 2
		while "%s %d" % (wanted, counter) in existing:
			counter += 1
		return "%s %d" % (wanted, counter)


_store = None


def getStore():
	global _store
	if _store is None:
		_store = SettingsStore()
	return _store
