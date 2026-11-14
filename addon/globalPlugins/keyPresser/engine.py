import copy
import random
import threading
import time

import config
import queueHandler
import tones
import ui
from logHandler import log

from . import keymap
from . import sendinput

SPEECH_KEYS = ("speakTypedCharacters", "speakTypedWords", "speakCommandKeys")

SPIN_MARGIN = 0.002
APP_CHECK_CACHE = 0.2
THREAD_JOIN_TIMEOUT = 0.5


def waitUntil(stopEvent, deadline):
	while True:
		remaining = deadline - time.perf_counter()
		if remaining <= 0:
			return stopEvent.is_set()
		if remaining > SPIN_MARGIN:
			if stopEvent.wait(remaining - SPIN_MARGIN):
				return True
			continue
		if stopEvent.is_set():
			return True
		time.sleep(0)


def waitFor(stopEvent, seconds):
	if seconds <= 0:
		return stopEvent.is_set()
	return waitUntil(stopEvent, time.perf_counter() + seconds)


class PressEngine:

	def __init__(self):
		self._thread = None
		self._stopEvent = threading.Event()
		self._running = False
		self._profile = None
		self._savedSpeech = None
		self._count = 0
		self._startedAt = 0.0
		self._lastReason = ""

	@property
	def running(self):
		return self._running

	@property
	def count(self):
		return self._count

	@property
	def profileName(self):
		return self._profile["name"] if self._profile else ""

	def collectSteps(self, profile):
		steps = []
		for sequence in profile["sequences"]:
			if not sequence.get("enabled", True):
				continue
			steps.extend(keymap.parseSpec(sequence["steps"]))
		if not steps:
			raise ValueError("No sequence is ticked to run.")
		return steps

	def validate(self, profile):
		if profile["mode"] == "keys":
			self.collectSteps(profile)
		return True

	def start(self, profile):
		if self._running:
			return False
		steps = None
		if profile["mode"] == "keys":
			steps = self.collectSteps(profile)
		self._stopEvent.set()
		self._joinThread()
		profile = copy.deepcopy(profile)
		stop = threading.Event()
		self._profile = profile
		self._count = 0
		self._lastReason = ""
		self._stopEvent = stop
		self._running = True
		self._startedAt = time.time()
		self._muteSpeech(profile)
		sendinput.beginHighResolutionTimers()
		if profile["beep"]:
			tones.beep(660, 60)
		self._message("Key presser activated, profile %s." % profile["name"], force=True)
		self._thread = threading.Thread(target=self._run, args=(profile, steps, stop), daemon=True)
		self._thread.name = "keyPresser"
		self._thread.start()
		return True

	def stop(self, announce=True):
		if not self._running:
			return False
		self._running = False
		self._stopEvent.set()
		self._joinThread()
		self._finalize()
		if announce:
			if self._profile and self._profile["beep"]:
				tones.beep(330, 90)
			self._message("Key presser stopped after %d actions." % self._count, force=True)
		return True

	def setInterval(self, milliseconds):
		if self._profile is not None:
			self._profile["intervalMs"] = milliseconds

	def toggle(self, profile):
		if self._running:
			self.stop()
			return False
		self.start(profile)
		return True

	def terminate(self):
		self._running = False
		self._stopEvent.set()
		self._joinThread()
		self._finalize()

	def _joinThread(self):
		thread = self._thread
		if thread is None or thread is threading.current_thread():
			return
		self._thread = None
		if thread.is_alive():
			thread.join(THREAD_JOIN_TIMEOUT)

	def _finalize(self):
		sendinput.endHighResolutionTimers()
		self._restoreSpeech()

	def _muteSpeech(self, profile):
		if not profile["muteTypedCharacters"]:
			return
		try:
			self._savedSpeech = {key: config.conf["keyboard"][key] for key in SPEECH_KEYS}
			for key in SPEECH_KEYS:
				config.conf["keyboard"][key] = False
		except Exception:
			log.exception("Key Presser could not silence the typed character announcements")
			self._savedSpeech = None

	def _restoreSpeech(self):
		if not self._savedSpeech:
			return
		try:
			for key, value in self._savedSpeech.items():
				config.conf["keyboard"][key] = value
		except Exception:
			log.exception("Key Presser could not restore the typed character announcements")
		self._savedSpeech = None

	def _message(self, text, force=False):
		if not force and self._profile and not self._profile["speak"]:
			return
		queueHandler.queueFunction(queueHandler.eventQueue, ui.message, text)

	def _appAllowed(self, profile):
		wanted = profile["appFilter"].strip()
		if not wanted:
			return True
		current = sendinput.getForegroundExecutable(APP_CHECK_CACHE).lower()
		if not current:
			return False
		for candidate in wanted.split(";"):
			candidate = candidate.strip().lower()
			if not candidate:
				continue
			if not candidate.endswith(".exe"):
				candidate += ".exe"
			if candidate == current:
				return True
		return False

	def _waitStart(self, profile, stop):
		delay = profile["startDelayMs"] / 1000.0
		if delay <= 0:
			return True
		if profile["countdown"] and delay >= 1:
			remaining = int(delay)
			fraction = delay - remaining
			while remaining > 0:
				self._message("%d" % remaining)
				if profile["beep"]:
					tones.beep(880, 40)
				if stop.wait(1.0):
					return False
				remaining -= 1
			if fraction > 0 and waitFor(stop, fraction):
				return False
		elif stop.wait(delay):
			return False
		return not stop.is_set()

	def _performOnce(self, profile, steps, stop):
		hold = profile["holdMs"] / 1000.0
		useScancode = profile["sendMethod"] == "scancode"
		if profile["mode"] == "mouse":
			sendinput.sendMouse(profile["mouseButton"], hold, lambda seconds: waitFor(stop, seconds))
			return
		stepDelay = profile["stepDelayMs"] / 1000.0
		lastIndex = len(steps) - 1
		for index, step in enumerate(steps):
			if stop.is_set():
				return
			self._sendStep(step, profile, hold, useScancode, stop)
			if index < lastIndex and stepDelay > 0:
				waitFor(stop, stepDelay)

	def _sendStep(self, step, profile, hold, useScancode, stop):
		kind, payload = step
		if kind == "random":
			self._sendStep(random.choice(payload), profile, hold, useScancode, stop)
			return
		if kind == "wait":
			waitFor(stop, payload / 1000.0)
			return
		sleep = lambda seconds: waitFor(stop, seconds)
		if kind == "text":
			sendinput.sendText(payload, profile["typingDelayMs"] / 1000.0, stop.is_set, sleep)
			return
		sendinput.sendChord(payload, hold, useScancode, sleep)

	def _blockedReason(self, code):
		if code == sendinput.ERROR_ACCESS_DENIED:
			return ("stopped, the target program refuses input from NVDA, "
				"it probably runs as administrator while NVDA does not")
		return "stopped, Windows refused the input"

	def _nextInterval(self, profile):
		interval = profile["intervalMs"] / 1000.0
		jitter = profile["jitterMs"] / 1000.0
		if jitter > 0:
			interval += random.uniform(-jitter, jitter)
		return max(0.0, interval)

	def _run(self, profile, steps, stop):
		reason = None
		try:
			if not self._waitStart(profile, stop):
				return
			if profile["beep"]:
				tones.beep(1000, 60)
			self._message("Running.")
			deadline = None
			if profile["maxRuntimeSec"] > 0:
				deadline = time.perf_counter() + profile["maxRuntimeSec"]
			nextTime = time.perf_counter()
			paused = False
			while not stop.is_set():
				if deadline is not None and time.perf_counter() >= deadline:
					reason = "stopped, the time limit was reached"
					break
				if not self._appAllowed(profile):
					if not paused:
						paused = True
						if profile["beep"]:
							tones.beep(280, 60)
						self._message("Paused, waiting for the target application.")
					if stop.wait(0.25):
						break
					nextTime = time.perf_counter()
					continue
				if paused:
					paused = False
					if profile["beep"]:
						tones.beep(720, 60)
					self._message("Resumed.")
				self._performOnce(profile, steps, stop)
				if stop.is_set():
					return
				self._count += 1
				announceEvery = profile["announceProgress"]
				if announceEvery > 0 and self._count % announceEvery == 0:
					self._message("%d" % self._count)
				if profile["repetitions"] > 0 and self._count >= profile["repetitions"]:
					reason = "stopped, all repetitions were completed"
					break
				nextTime += self._nextInterval(profile)
				now = time.perf_counter()
				if nextTime <= now:
					nextTime = now
					time.sleep(0)
					continue
				if waitUntil(stop, nextTime):
					break
		except sendinput.InputBlockedError as error:
			log.error("Key Presser could not send input, Windows error %d" % error.code)
			reason = self._blockedReason(error.code)
		except Exception:
			log.exception("Key Presser stopped because of an error")
			reason = "stopped because of an error"
		if reason is None:
			return
		queueHandler.queueFunction(queueHandler.eventQueue, self._completed, reason, stop)

	def _completed(self, reason, stop):
		if stop is not self._stopEvent or not self._running:
			return
		self._running = False
		stop.set()
		self._lastReason = reason
		self._finalize()
		if self._profile and self._profile["beep"]:
			tones.beep(440, 90)
		self._message("Key presser %s, %d actions sent." % (reason, self._count), force=True)
