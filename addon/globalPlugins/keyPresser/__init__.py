import addonHandler
import core
import globalPluginHandler
import globalVars
import gui
import ui
import wx
from scriptHandler import script

from . import sendinput
from .engine import PressEngine
from .settingsgui import KeyPresserPanel, closeNotice, showNotice, showNoticeIfNeeded
from .store import getStore

try:
	addonHandler.initTranslation()
except Exception:
	pass

INTERVAL_STEP = 50
NOTICE_DELAY = 4000


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	scriptCategory = _("Key Presser")

	def __init__(self):
		super().__init__()
		self.store = getStore()
		self.engine = PressEngine()
		self._noticeTimer = None
		if KeyPresserPanel not in gui.settingsDialogs.NVDASettingsDialog.categoryClasses:
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(KeyPresserPanel)
		if not self.store.warningAccepted:
			self._noticeTimer = core.callLater(NOTICE_DELAY, self._openNotice)

	def _openNotice(self):
		self._noticeTimer = None
		wx.CallAfter(showNoticeIfNeeded)

	def _cancelNotice(self):
		if self._noticeTimer is None:
			return
		try:
			self._noticeTimer.Stop()
		except Exception:
			pass
		self._noticeTimer = None

	def terminate(self):
		self._cancelNotice()
		closeNotice()
		self.engine.terminate()
		try:
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(KeyPresserPanel)
		except ValueError:
			pass
		super().terminate()

	def openSettings(self):
		popup = getattr(gui.mainFrame, "popupSettingsDialog", None) or gui.mainFrame._popupSettingsDialog
		popup(gui.settingsDialogs.NVDASettingsDialog, KeyPresserPanel)

	@script(
		description=_("Opens the Key Presser settings"),
		gesture="kb:NVDA+y",
	)
	def script_openSettings(self, gesture):
		wx.CallAfter(self.openSettings)

	@script(
		description=_("Stops the Key Presser immediately"),
		gesture="kb:NVDA+z",
	)
	def script_stop(self, gesture):
		if not self.engine.stop():
			ui.message(_("Key presser is not running"))

	@script(
		description=_("Starts or stops the Key Presser with the active profile"),
		gesture="kb:NVDA+j",
	)
	def script_toggle(self, gesture):
		if self.engine.running:
			self.engine.stop()
			return
		profile = self.store.activeProfile
		try:
			self.engine.start(profile)
		except ValueError as error:
			ui.message(_("Cannot start: {reason}").format(reason=str(error)))

	@script(
		description=_("Switches to the next Key Presser profile"),
		gesture="kb:NVDA+alt+z",
	)
	def script_nextProfile(self, gesture):
		if self.engine.running:
			ui.message(_("Stop the key presser before switching profiles"))
			return
		profile = self.store.selectNextProfile()
		ui.message(_("Profile {name}, every {interval} milliseconds").format(
			name=profile["name"], interval=profile["intervalMs"]
		))

	@script(description=_("Reports the Key Presser status"))
	def script_reportStatus(self, gesture):
		profile = self.store.activeProfile
		if self.engine.running:
			ui.message(_("Running, profile {name}, {count} actions sent").format(
				name=self.engine.profileName, count=self.engine.count
			))
			return
		ui.message(_("Stopped, profile {name}, every {interval} milliseconds").format(
			name=profile["name"], interval=profile["intervalMs"]
		))

	@script(description=_("Increases the interval of the active profile"))
	def script_increaseInterval(self, gesture):
		self._changeInterval(INTERVAL_STEP)

	@script(description=_("Decreases the interval of the active profile"))
	def script_decreaseInterval(self, gesture):
		self._changeInterval(-INTERVAL_STEP)

	def _changeInterval(self, delta):
		profile = self.store.activeProfile
		value = max(1, min(3600000, profile["intervalMs"] + delta))
		profile["intervalMs"] = value
		self.store.save()
		self.engine.setInterval(value)
		ui.message(_("{interval} milliseconds").format(interval=value))

	@script(description=_("Locks the active profile to the program that is currently in the foreground"))
	def script_captureApplication(self, gesture):
		profile = self.store.activeProfile
		executable = sendinput.getForegroundExecutable()
		if not executable:
			ui.message(_("The foreground program could not be identified"))
			return
		profile["appFilter"] = executable
		self.store.save()
		ui.message(_("Restricted to {program}").format(program=executable))

	@script(description=_("Removes the program restriction from the active profile"))
	def script_clearApplication(self, gesture):
		profile = self.store.activeProfile
		profile["appFilter"] = ""
		self.store.save()
		ui.message(_("The program restriction has been removed"))

	@script(description=_("Shows the Key Presser warning"))
	def script_showNotice(self, gesture):
		wx.CallAfter(showNotice)


if globalVars.appArgs.secure:
	GlobalPlugin = globalPluginHandler.GlobalPlugin
