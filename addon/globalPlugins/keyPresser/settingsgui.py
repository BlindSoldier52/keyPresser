import copy

import addonHandler
import gui
import ui
import wx
from gui import guiHelper
from gui.settingsDialogs import SettingsPanel

from . import keymap
from .store import (
	MODE_VALUES, MOUSE_BUTTON_VALUES, SEND_METHOD_VALUES,
	getStore, newProfile, newSequence,
)

try:
	addonHandler.initTranslation()
except Exception:
	pass

NOTICE_TITLE = _("Warning")

NOTICE_TEXT = _("This add-on was written for experiments only. I don't encourage cheating with this.")

MODE_LABELS = (_("Keys and text"), _("Mouse button"))
METHOD_VALUES = SEND_METHOD_VALUES
METHOD_LABELS = (
	_("Scan codes, best for games, SDL and DirectInput"),
	_("Virtual key codes, best for standard windows"),
)
BUTTON_VALUES = MOUSE_BUTTON_VALUES
BUTTON_LABELS = (
	_("Left"), _("Right"), _("Middle"), _("Fourth, X1"), _("Fifth, X2"),
	_("Wheel up"), _("Wheel down"),
)


RAW_CATEGORY = _("Raw code")


def indexOf(values, value):
	try:
		return values.index(value)
	except ValueError:
		return 0


class KeyPickerDialog(wx.Dialog):

	def __init__(self, parent, step=None):
		super().__init__(parent, title=_("Choose a key"))
		self.step = ""
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		helper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		categories = [_(name) for name, entries in keymap.KEY_CATEGORIES] + [RAW_CATEGORY]
		self.categoryChoice = helper.addLabeledControl(_("&Category:"), wx.Choice, choices=categories)
		self.categoryChoice.Bind(wx.EVT_CHOICE, self.onCategoryChanged)
		self.keyList = helper.addLabeledControl(
			_("&Key:"), wx.ListBox, size=(320, 220), style=wx.LB_SINGLE
		)
		self.rawEdit = helper.addLabeledControl(
			_("&Raw code, for example vk:0x41 or sc:0x1E:"), wx.TextCtrl
		)
		modifierBox = wx.StaticBox(self, label=_("Modifiers"))
		modifierHelper = helper.addItem(
			guiHelper.BoxSizerHelper(modifierBox, sizer=wx.StaticBoxSizer(modifierBox, wx.VERTICAL))
		)
		self.modifierChecks = {}
		for name, label in (
			("ctrl", _("C&ontrol")), ("shift", _("&Shift")),
			("alt", _("&Alt")), ("win", _("&Windows")),
		):
			check = modifierHelper.addItem(wx.CheckBox(modifierBox, label=label))
			self.modifierChecks[name] = check
		helper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		mainSizer.Add(helper.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.CentreOnScreen()
		self._prepare(step)

	def _prepare(self, step):
		categoryIndex, keyIndex = 0, 0
		if step:
			modifiers, base = keymap.splitStep(step)
			for name, check in self.modifierChecks.items():
				check.Value = name in modifiers
			found, position = keymap.findCategory(base)
			if found >= 0:
				categoryIndex, keyIndex = found, position
			else:
				categoryIndex = len(keymap.KEY_CATEGORIES)
				self.rawEdit.Value = base
		self.categoryChoice.Selection = categoryIndex
		self._fillKeys(keyIndex)
		self.categoryChoice.SetFocus()

	def _fillKeys(self, selection=0):
		index = self.categoryChoice.Selection
		isRaw = index >= len(keymap.KEY_CATEGORIES)
		if isRaw:
			self.keyList.Set([])
		else:
			self.keyList.Set([_(label) for label, spec in keymap.KEY_CATEGORIES[index][1]])
			if self.keyList.GetCount():
				self.keyList.Selection = min(selection, self.keyList.GetCount() - 1)
		self.keyList.Enable(not isRaw)
		self.rawEdit.Enable(isRaw)

	def onCategoryChanged(self, event):
		self._fillKeys()

	def onOk(self, event):
		index = self.categoryChoice.Selection
		if index >= len(keymap.KEY_CATEGORIES):
			base = self.rawEdit.Value.strip()
		elif self.keyList.Selection < 0:
			base = ""
		else:
			base = keymap.KEY_CATEGORIES[index][1][self.keyList.Selection][1]
		if not base:
			gui.messageBox(_("Please choose a key."), _("Key Presser"), wx.OK | wx.ICON_ERROR, self)
			return
		modifiers = [name for name, check in self.modifierChecks.items() if check.Value]
		step = keymap.buildStep(modifiers, base)
		try:
			keymap.parseSpec(step)
		except ValueError as error:
			gui.messageBox(str(error), _("Key Presser"), wx.OK | wx.ICON_ERROR, self)
			return
		self.step = step
		event.Skip()


class TextStepDialog(wx.Dialog):

	def __init__(self, parent, value=""):
		super().__init__(parent, title=_("Text to type"))
		self.value = ""
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		helper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		self.textEdit = helper.addLabeledControl(
			_("&Text, line breaks are sent as Enter:"),
			wx.TextCtrl, size=(420, 140), style=wx.TE_MULTILINE, value=value
		)
		helper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		mainSizer.Add(helper.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.CentreOnScreen()
		self.textEdit.SetFocus()

	def onOk(self, event):
		if not self.textEdit.Value:
			gui.messageBox(_("Please enter some text."), _("Key Presser"), wx.OK | wx.ICON_ERROR, self)
			return
		self.value = self.textEdit.Value
		event.Skip()


RANDOM_KINDS = ("texts", "keys")
RANDOM_KIND_LABELS = (_("Plain texts"), _("Keys or key combinations"))


class RandomStepDialog(wx.Dialog):

	def __init__(self, parent, alternatives=None):
		super().__init__(parent, title=_("Random step"))
		self.alternatives = []
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		helper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		self.kindChoice = helper.addLabeledControl(
			_("The options are:"), wx.Choice, choices=list(RANDOM_KIND_LABELS)
		)
		self.optionsEdit = helper.addLabeledControl(
			_("&One option per line, one of them is picked at random every time:"),
			wx.TextCtrl, size=(420, 160), style=wx.TE_MULTILINE
		)
		helper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		mainSizer.Add(helper.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.CentreOnScreen()
		self._prepare(alternatives)

	def _prepare(self, alternatives):
		self.kindChoice.Selection = 0
		if alternatives:
			if all(keymap.isTextStep(item) for item in alternatives):
				lines = [keymap.stepText(item).replace("\n", " ") for item in alternatives]
			else:
				self.kindChoice.Selection = 1
				lines = list(alternatives)
			self.optionsEdit.Value = "\r\n".join(lines)
		self.optionsEdit.SetFocus()

	def onOk(self, event):
		lines = [line.strip() for line in self.optionsEdit.Value.splitlines()]
		lines = [line for line in lines if line]
		if len(lines) < 2:
			gui.messageBox(
				_("Please enter at least two options, one per line."),
				_("Key Presser"), wx.OK | wx.ICON_ERROR, self
			)
			return
		asTexts = RANDOM_KINDS[self.kindChoice.Selection] == "texts"
		alternatives = [keymap.buildTextStep(line) if asTexts else line for line in lines]
		try:
			keymap.parseSpec(keymap.buildRandomStep(alternatives))
		except ValueError as error:
			gui.messageBox(str(error), _("Key Presser"), wx.OK | wx.ICON_ERROR, self)
			return
		self.alternatives = alternatives
		event.Skip()


class NoticeDialog(wx.Dialog):

	def __init__(self, parent):
		super().__init__(parent, title=NOTICE_TITLE)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		helper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		helper.addItem(wx.StaticText(self, label=NOTICE_TEXT))
		helper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK))
		self.Bind(wx.EVT_BUTTON, self.onButton)
		self.Bind(wx.EVT_CLOSE, self.onClose)
		mainSizer.Add(helper.sizer, border=guiHelper.BORDER_FOR_DIALOGS, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.CentreOnScreen()
		okButton = self.FindWindowById(wx.ID_OK)
		if okButton:
			okButton.SetFocus()

	def onButton(self, event):
		self.Close()

	def onClose(self, event):
		global _noticeDialog
		_noticeDialog = None
		store = getStore()
		if not store.warningAccepted:
			store.warningAccepted = True
			store.save()
		self.Destroy()


_noticeDialog = None


def showNotice():
	global _noticeDialog
	if not wx.IsMainThread():
		wx.CallAfter(showNotice)
		return
	if _noticeDialog is None:
		_noticeDialog = NoticeDialog(gui.mainFrame)
	gui.mainFrame.prePopup()
	_noticeDialog.Show()
	_noticeDialog.Raise()
	gui.mainFrame.postPopup()


def closeNotice():
	global _noticeDialog
	dialog = _noticeDialog
	_noticeDialog = None
	if dialog:
		dialog.Destroy()


def showNoticeIfNeeded():
	if getStore().warningAccepted:
		return
	showNotice()


class KeyPresserPanel(SettingsPanel):

	title = _("Key Presser")

	def makeSettings(self, settingsSizer):
		store = getStore()
		self._profiles = [copy.deepcopy(profile) for profile in store.profiles]
		self._index = store.activeProfileIndex
		if not 0 <= self._index < len(self._profiles):
			self._index = 0
		helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		profileBox = wx.StaticBox(self, label=_("Profiles"))
		profileHelper = helper.addItem(
			guiHelper.BoxSizerHelper(profileBox, sizer=wx.StaticBoxSizer(profileBox, wx.VERTICAL))
		)
		self.profileChoice = profileHelper.addLabeledControl(
			_("Active &profile:"), wx.Choice, choices=self._names()
		)
		self.profileChoice.Selection = self._index
		self.profileChoice.Bind(wx.EVT_CHOICE, self.onProfileChanged)
		buttonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
		self.newButton = buttonHelper.addButton(profileBox, label=_("&New..."))
		self.newButton.Bind(wx.EVT_BUTTON, self.onNewProfile)
		self.duplicateButton = buttonHelper.addButton(profileBox, label=_("D&uplicate..."))
		self.duplicateButton.Bind(wx.EVT_BUTTON, self.onDuplicateProfile)
		self.renameButton = buttonHelper.addButton(profileBox, label=_("&Rename..."))
		self.renameButton.Bind(wx.EVT_BUTTON, self.onRenameProfile)
		self.deleteButton = buttonHelper.addButton(profileBox, label=_("&Delete"))
		self.deleteButton.Bind(wx.EVT_BUTTON, self.onDeleteProfile)
		profileHelper.addItem(buttonHelper)

		actionBox = wx.StaticBox(self, label=_("What to send"))
		actionHelper = helper.addItem(
			guiHelper.BoxSizerHelper(actionBox, sizer=wx.StaticBoxSizer(actionBox, wx.VERTICAL))
		)
		self.modeChoice = actionHelper.addLabeledControl(_("&Mode:"), wx.Choice, choices=list(MODE_LABELS))
		self.modeChoice.Bind(wx.EVT_CHOICE, self.onModeChanged)
		self.keysGroup = guiHelper.BoxSizerHelper(actionBox, orientation=wx.VERTICAL)
		self.sequenceList = self.keysGroup.addLabeledControl(
			_("Se&quences, the ticked ones run, in this order:"),
			wx.CheckListBox, size=(360, 110)
		)
		self.sequenceList.Bind(wx.EVT_LISTBOX, self.onSequenceSelected)
		self.sequenceList.Bind(wx.EVT_CHECKLISTBOX, self.onSequenceChecked)
		sequenceButtonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
		self.newSequenceButton = sequenceButtonHelper.addButton(actionBox, label=_("Ne&w sequence..."))
		self.newSequenceButton.Bind(wx.EVT_BUTTON, self.onNewSequence)
		self.duplicateSequenceButton = sequenceButtonHelper.addButton(actionBox, label=_("Dup&licate sequence..."))
		self.duplicateSequenceButton.Bind(wx.EVT_BUTTON, self.onDuplicateSequence)
		self.renameSequenceButton = sequenceButtonHelper.addButton(actionBox, label=_("Rena&me sequence..."))
		self.renameSequenceButton.Bind(wx.EVT_BUTTON, self.onRenameSequence)
		self.deleteSequenceButton = sequenceButtonHelper.addButton(actionBox, label=_("De&lete sequence"))
		self.deleteSequenceButton.Bind(wx.EVT_BUTTON, self.onDeleteSequence)
		self.keysGroup.addItem(sequenceButtonHelper)
		self.keysList = self.keysGroup.addLabeledControl(
			_("&Steps of the selected sequence, played in order:"),
			wx.ListBox, size=(360, 130), style=wx.LB_SINGLE
		)
		keysButtonHelper = guiHelper.ButtonHelper(wx.HORIZONTAL)
		self.addKeyButton = keysButtonHelper.addButton(actionBox, label=_("A&dd key..."))
		self.addKeyButton.Bind(wx.EVT_BUTTON, self.onAddKey)
		self.addTextButton = keysButtonHelper.addButton(actionBox, label=_("Add te&xt..."))
		self.addTextButton.Bind(wx.EVT_BUTTON, self.onAddText)
		self.addRandomButton = keysButtonHelper.addButton(actionBox, label=_("Add ran&dom..."))
		self.addRandomButton.Bind(wx.EVT_BUTTON, self.onAddRandom)
		self.addPauseButton = keysButtonHelper.addButton(actionBox, label=_("Add pa&use..."))
		self.addPauseButton.Bind(wx.EVT_BUTTON, self.onAddPause)
		self.editKeyButton = keysButtonHelper.addButton(actionBox, label=_("Ed&it..."))
		self.editKeyButton.Bind(wx.EVT_BUTTON, self.onEditStep)
		self.removeKeyButton = keysButtonHelper.addButton(actionBox, label=_("Re&move"))
		self.removeKeyButton.Bind(wx.EVT_BUTTON, self.onRemoveStep)
		self.moveUpButton = keysButtonHelper.addButton(actionBox, label=_("Move u&p"))
		self.moveUpButton.Bind(wx.EVT_BUTTON, self.onMoveUp)
		self.moveDownButton = keysButtonHelper.addButton(actionBox, label=_("Move do&wn"))
		self.moveDownButton.Bind(wx.EVT_BUTTON, self.onMoveDown)
		self.advancedButton = keysButtonHelper.addButton(actionBox, label=_("T&ype the sequence..."))
		self.advancedButton.Bind(wx.EVT_BUTTON, self.onAdvanced)
		self.keysGroup.addItem(keysButtonHelper)
		self.methodChoice = self.keysGroup.addLabeledControl(
			_("Sending m&ethod:"), wx.Choice, choices=list(METHOD_LABELS)
		)
		actionHelper.addItem(self.keysGroup)

		self.mouseGroup = guiHelper.BoxSizerHelper(actionBox, orientation=wx.VERTICAL)
		self.buttonChoice = self.mouseGroup.addLabeledControl(
			_("Mouse &button:"), wx.Choice, choices=list(BUTTON_LABELS)
		)
		actionHelper.addItem(self.mouseGroup)

		timingBox = wx.StaticBox(self, label=_("Timing"))
		timingHelper = helper.addItem(
			guiHelper.BoxSizerHelper(timingBox, sizer=wx.StaticBoxSizer(timingBox, wx.VERTICAL))
		)
		self.intervalEdit = timingHelper.addLabeledControl(
			_("&Interval between actions, in milliseconds:"), wx.SpinCtrl, min=1, max=3600000
		)
		self.jitterEdit = timingHelper.addLabeledControl(
			_("Random &variation added to the interval, in milliseconds:"), wx.SpinCtrl, min=0, max=600000
		)
		self.holdEdit = timingHelper.addLabeledControl(
			_("&Hold each key or button down for, in milliseconds:"), wx.SpinCtrl, min=0, max=60000
		)
		self.stepEdit = timingHelper.addLabeledControl(
			_("Pause between the &steps of a sequence, in milliseconds:"), wx.SpinCtrl, min=0, max=600000
		)
		self.typingEdit = timingHelper.addLabeledControl(
			_("Milliseconds between the &characters of a text step:"), wx.SpinCtrl, min=0, max=60000
		)
		self.startDelayEdit = timingHelper.addLabeledControl(
			_("&Delay before the first action, in milliseconds:"), wx.SpinCtrl, min=0, max=600000
		)
		self.countdownCheck = timingHelper.addItem(
			wx.CheckBox(timingBox, label=_("Speak a &countdown during that delay"))
		)

		limitBox = wx.StaticBox(self, label=_("Limits and feedback"))
		limitHelper = helper.addItem(
			guiHelper.BoxSizerHelper(limitBox, sizer=wx.StaticBoxSizer(limitBox, wx.VERTICAL))
		)
		self.repetitionsEdit = limitHelper.addLabeledControl(
			_("Stop after this many &actions, 0 for unlimited:"), wx.SpinCtrl, min=0, max=1000000
		)
		self.runtimeEdit = limitHelper.addLabeledControl(
			_("Stop after this many &seconds, 0 for unlimited:"), wx.SpinCtrl, min=0, max=86400
		)
		self.appEdit = limitHelper.addLabeledControl(
			_("Only run while one of these pro&grams is in the foreground, separated by semicolons, empty for any:"),
			wx.TextCtrl,
		)
		self.progressEdit = limitHelper.addLabeledControl(
			_("Announce the action c&ount every this many actions, 0 to never announce:"),
			wx.SpinCtrl, min=0, max=1000000
		)
		self.beepCheck = limitHelper.addItem(
			wx.CheckBox(limitBox, label=_("Play &beeps when starting, pausing and stopping"))
		)
		self.speakCheck = limitHelper.addItem(
			wx.CheckBox(limitBox, label=_("Speak &status messages"))
		)
		self.muteCheck = limitHelper.addItem(
			wx.CheckBox(limitBox, label=_("Silence typed character and command key announcements &while running"))
		)
		self.noticeButton = limitHelper.addItem(wx.Button(limitBox, label=_("Show the &warning again")))
		self.noticeButton.Bind(wx.EVT_BUTTON, self.onShowNotice)

		self._loadProfile(self._index)

	def _names(self):
		return [profile["name"] for profile in self._profiles]

	def _refreshProfileChoice(self):
		self.profileChoice.Set(self._names())
		self.profileChoice.Selection = self._index

	def _refreshKeysList(self, selection=-1):
		self.keysList.Set([keymap.describeStep(step) for step in self._steps])
		if self._steps:
			if selection < 0:
				selection = len(self._steps) - 1
			self.keysList.Selection = max(0, min(selection, len(self._steps) - 1))

	def _selectedStep(self):
		index = self.keysList.Selection
		return index if 0 <= index < len(self._steps) else -1

	def _sequenceNames(self):
		return [sequence["name"] for sequence in self._sequences]

	def _sequenceLabel(self, sequence):
		return "%s (%s)" % (sequence["name"], _("on") if sequence["enabled"] else _("off"))

	def _refreshSequenceList(self, selection=-1):
		self.sequenceList.Set([self._sequenceLabel(sequence) for sequence in self._sequences])
		for position, sequence in enumerate(self._sequences):
			self.sequenceList.Check(position, sequence["enabled"])
		if self._sequences:
			if selection < 0:
				selection = self._sequenceIndex
			self._sequenceIndex = max(0, min(selection, len(self._sequences) - 1))
			self.sequenceList.Selection = self._sequenceIndex

	def _loadSequence(self, index):
		self._sequenceIndex = index
		self._steps = keymap.splitSpec(self._sequences[index]["steps"])
		self._refreshKeysList(0)

	def _collectSequence(self):
		if self._sequences:
			self._sequences[self._sequenceIndex]["steps"] = keymap.joinSteps(self._steps)

	def _loadProfile(self, index):
		profile = self._profiles[index]
		self.modeChoice.Selection = indexOf(MODE_VALUES, profile["mode"])
		self._sequences = copy.deepcopy(profile["sequences"])
		self._sequenceIndex = 0
		self._refreshSequenceList(0)
		self._loadSequence(0)
		self.buttonChoice.Selection = indexOf(BUTTON_VALUES, profile["mouseButton"])
		self.methodChoice.Selection = indexOf(METHOD_VALUES, profile["sendMethod"])
		self.intervalEdit.Value = profile["intervalMs"]
		self.jitterEdit.Value = profile["jitterMs"]
		self.holdEdit.Value = profile["holdMs"]
		self.stepEdit.Value = profile["stepDelayMs"]
		self.typingEdit.Value = profile["typingDelayMs"]
		self.startDelayEdit.Value = profile["startDelayMs"]
		self.countdownCheck.Value = profile["countdown"]
		self.repetitionsEdit.Value = profile["repetitions"]
		self.runtimeEdit.Value = profile["maxRuntimeSec"]
		self.appEdit.Value = profile["appFilter"]
		self.progressEdit.Value = profile["announceProgress"]
		self.beepCheck.Value = profile["beep"]
		self.speakCheck.Value = profile["speak"]
		self.muteCheck.Value = profile["muteTypedCharacters"]
		self._updateEnabledFields()

	def _collectProfile(self, index):
		profile = self._profiles[index]
		profile["mode"] = MODE_VALUES[self.modeChoice.Selection]
		self._collectSequence()
		profile["sequences"] = copy.deepcopy(self._sequences)
		profile["mouseButton"] = BUTTON_VALUES[self.buttonChoice.Selection]
		profile["sendMethod"] = METHOD_VALUES[self.methodChoice.Selection]
		profile["intervalMs"] = self.intervalEdit.Value
		profile["jitterMs"] = self.jitterEdit.Value
		profile["holdMs"] = self.holdEdit.Value
		profile["stepDelayMs"] = self.stepEdit.Value
		profile["typingDelayMs"] = self.typingEdit.Value
		profile["startDelayMs"] = self.startDelayEdit.Value
		profile["countdown"] = self.countdownCheck.Value
		profile["repetitions"] = self.repetitionsEdit.Value
		profile["maxRuntimeSec"] = self.runtimeEdit.Value
		profile["appFilter"] = self.appEdit.Value.strip()
		profile["announceProgress"] = self.progressEdit.Value
		profile["beep"] = self.beepCheck.Value
		profile["speak"] = self.speakCheck.Value
		profile["muteTypedCharacters"] = self.muteCheck.Value

	def _updateEnabledFields(self):
		mode = MODE_VALUES[self.modeChoice.Selection]
		self.keysGroup.sizer.ShowItems(mode == "keys")
		self.mouseGroup.sizer.ShowItems(mode == "mouse")
		self.stepEdit.Enable(mode != "mouse")
		self.typingEdit.Enable(mode != "mouse")
		self.Layout()

	def onModeChanged(self, event):
		self._updateEnabledFields()

	def onAddKey(self, event):
		with KeyPickerDialog(self) as dialog:
			if dialog.ShowModal() != wx.ID_OK or not dialog.step:
				return
			step = dialog.step
		self._insertStep(step)

	def onSequenceSelected(self, event):
		index = self.sequenceList.Selection
		if index < 0 or index == self._sequenceIndex:
			return
		if not self._validateCurrent():
			self.sequenceList.Selection = self._sequenceIndex
			return
		self._collectSequence()
		self._loadSequence(index)

	def onSequenceChecked(self, event):
		index = event.GetInt()
		if not 0 <= index < len(self._sequences):
			return
		checked = self.sequenceList.IsChecked(index)
		self._sequences[index]["enabled"] = checked
		selection = self.sequenceList.Selection
		self.sequenceList.SetString(index, self._sequenceLabel(self._sequences[index]))
		self.sequenceList.Check(index, checked)
		if selection >= 0:
			self.sequenceList.Selection = selection
		ui.message(_("on") if checked else _("off"))

	def _askSequenceName(self, title, initial=""):
		with wx.TextEntryDialog(self, _("Sequence name:"), title, value=initial) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			name = dialog.GetValue().strip()
		if not name:
			return None
		if name in self._sequenceNames():
			gui.messageBox(
				_("A sequence with that name already exists."),
				_("Key Presser"), wx.OK | wx.ICON_ERROR, self
			)
			return None
		return name

	def onNewSequence(self, event):
		if not self._validateCurrent():
			return
		name = self._askSequenceName(_("New sequence"))
		if not name:
			return
		self._collectSequence()
		self._sequences.append(newSequence(name))
		self._refreshSequenceList(len(self._sequences) - 1)
		self._loadSequence(self._sequenceIndex)
		self.sequenceList.SetFocus()

	def onDuplicateSequence(self, event):
		if not self._validateCurrent():
			return
		name = self._askSequenceName(
			_("Duplicate sequence"), self._sequences[self._sequenceIndex]["name"] + " copy"
		)
		if not name:
			return
		self._collectSequence()
		clone = copy.deepcopy(self._sequences[self._sequenceIndex])
		clone["name"] = name
		self._sequences.append(clone)
		self._refreshSequenceList(len(self._sequences) - 1)
		self._loadSequence(self._sequenceIndex)
		self.sequenceList.SetFocus()

	def onRenameSequence(self, event):
		name = self._askSequenceName(
			_("Rename sequence"), self._sequences[self._sequenceIndex]["name"]
		)
		if not name:
			return
		self._sequences[self._sequenceIndex]["name"] = name
		self._refreshSequenceList(self._sequenceIndex)
		self.sequenceList.SetFocus()

	def onDeleteSequence(self, event):
		if len(self._sequences) < 2:
			gui.messageBox(
				_("The last remaining sequence cannot be deleted."),
				_("Key Presser"), wx.OK | wx.ICON_ERROR, self
			)
			return
		name = self._sequences[self._sequenceIndex]["name"]
		answer = gui.messageBox(
			_("Delete the sequence {name}?").format(name=name),
			_("Key Presser"), wx.YES | wx.NO | wx.ICON_QUESTION, self
		)
		if answer != wx.YES:
			return
		del self._sequences[self._sequenceIndex]
		self._refreshSequenceList(max(0, self._sequenceIndex - 1))
		self._loadSequence(self._sequenceIndex)
		self.sequenceList.SetFocus()

	def onAddText(self, event):
		with TextStepDialog(self) as dialog:
			if dialog.ShowModal() != wx.ID_OK or not dialog.value:
				return
			step = keymap.buildTextStep(dialog.value)
		self._insertStep(step)

	def onAddRandom(self, event):
		with RandomStepDialog(self) as dialog:
			if dialog.ShowModal() != wx.ID_OK or not dialog.alternatives:
				return
			step = keymap.buildRandomStep(dialog.alternatives)
		self._insertStep(step)

	def _insertStep(self, step):
		index = self._selectedStep()
		position = index + 1 if index >= 0 else len(self._steps)
		self._steps.insert(position, step)
		self._refreshKeysList(position)
		self.keysList.SetFocus()

	def onAddPause(self, event):
		with wx.NumberEntryDialog(
			self, _("Length of the pause, in milliseconds:"), _("Milliseconds:"),
			_("Add pause"), 500, 0, 600000
		) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			milliseconds = dialog.GetValue()
		self._insertStep("wait:%d" % milliseconds)

	def onEditStep(self, event):
		index = self._selectedStep()
		if index < 0:
			return
		step = self._steps[index]
		if keymap.isRandomStep(step):
			with RandomStepDialog(self, keymap.randomAlternatives(step)) as dialog:
				if dialog.ShowModal() != wx.ID_OK or not dialog.alternatives:
					return
				self._steps[index] = keymap.buildRandomStep(dialog.alternatives)
		elif keymap.isTextStep(step):
			with TextStepDialog(self, keymap.stepText(step)) as dialog:
				if dialog.ShowModal() != wx.ID_OK or not dialog.value:
					return
				self._steps[index] = keymap.buildTextStep(dialog.value)
		elif step.lower().startswith("wait:"):
			current = int(step.split(":", 1)[1] or 0)
			with wx.NumberEntryDialog(
				self, _("Length of the pause, in milliseconds:"), _("Milliseconds:"),
				_("Edit pause"), current, 0, 600000
			) as dialog:
				if dialog.ShowModal() != wx.ID_OK:
					return
				self._steps[index] = "wait:%d" % dialog.GetValue()
		else:
			with KeyPickerDialog(self, step) as dialog:
				if dialog.ShowModal() != wx.ID_OK or not dialog.step:
					return
				self._steps[index] = dialog.step
		self._refreshKeysList(index)
		self.keysList.SetFocus()

	def onRemoveStep(self, event):
		index = self._selectedStep()
		if index < 0:
			return
		del self._steps[index]
		self._refreshKeysList(min(index, len(self._steps) - 1))
		self.keysList.SetFocus()

	def onMoveUp(self, event):
		self._moveStep(-1)

	def onMoveDown(self, event):
		self._moveStep(1)

	def _moveStep(self, offset):
		index = self._selectedStep()
		target = index + offset
		if index < 0 or not 0 <= target < len(self._steps):
			return
		self._steps[index], self._steps[target] = self._steps[target], self._steps[index]
		self._refreshKeysList(target)
		self.keysList.SetFocus()

	def onAdvanced(self, event):
		with wx.TextEntryDialog(
			self,
			_("Steps separated by commas, for example: ctrl+a, w, wait:500, f5, vk:0x41"),
			_("Type the sequence"),
			value=keymap.joinSteps(self._steps),
		) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			spec = dialog.GetValue()
		try:
			keymap.parseSpec(spec)
		except ValueError as error:
			gui.messageBox(str(error), _("Key Presser"), wx.OK | wx.ICON_ERROR, self)
			return
		self._steps = keymap.splitSpec(spec)
		self._refreshKeysList(0)
		self.keysList.SetFocus()

	def onProfileChanged(self, event):
		newIndex = self.profileChoice.Selection
		if newIndex == self._index:
			return
		if not self._validateCurrent():
			self.profileChoice.Selection = self._index
			return
		self._collectProfile(self._index)
		self._index = newIndex
		self._loadProfile(self._index)

	def _askName(self, title, initial=""):
		with wx.TextEntryDialog(self, _("Profile name:"), title, value=initial) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return None
			name = dialog.GetValue().strip()
		if not name:
			return None
		if name in self._names():
			gui.messageBox(
				_("A profile with that name already exists."),
				_("Key Presser"), wx.OK | wx.ICON_ERROR, self
			)
			return None
		return name

	def _appendProfile(self, profile):
		self._profiles.append(profile)
		self._index = len(self._profiles) - 1
		self._refreshProfileChoice()
		self._loadProfile(self._index)

	def onNewProfile(self, event):
		if not self._validateCurrent():
			return
		name = self._askName(_("New profile"))
		if not name:
			return
		self._collectProfile(self._index)
		self._appendProfile(newProfile(name))

	def onDuplicateProfile(self, event):
		if not self._validateCurrent():
			return
		name = self._askName(_("Duplicate profile"), self._profiles[self._index]["name"] + " copy")
		if not name:
			return
		self._collectProfile(self._index)
		clone = copy.deepcopy(self._profiles[self._index])
		clone["name"] = name
		self._appendProfile(clone)

	def onRenameProfile(self, event):
		name = self._askName(_("Rename profile"), self._profiles[self._index]["name"])
		if not name:
			return
		self._profiles[self._index]["name"] = name
		self._refreshProfileChoice()

	def onDeleteProfile(self, event):
		if len(self._profiles) < 2:
			gui.messageBox(
				_("The last remaining profile cannot be deleted."),
				_("Key Presser"), wx.OK | wx.ICON_ERROR, self
			)
			return
		name = self._profiles[self._index]["name"]
		answer = gui.messageBox(
			_("Delete the profile {name}?").format(name=name),
			_("Key Presser"), wx.YES | wx.NO | wx.ICON_QUESTION, self
		)
		if answer != wx.YES:
			return
		del self._profiles[self._index]
		self._index = max(0, self._index - 1)
		self._refreshProfileChoice()
		self._loadProfile(self._index)

	def onShowNotice(self, event):
		showNotice()

	def _validateCurrent(self):
		mode = MODE_VALUES[self.modeChoice.Selection]
		if mode == "keys":
			try:
				keymap.parseSpec(keymap.joinSteps(self._steps))
			except ValueError as error:
				gui.messageBox(str(error), _("Key Presser"), wx.OK | wx.ICON_ERROR, self)
				self.keysList.SetFocus()
				return False
		return True

	def isValid(self):
		return self._validateCurrent()

	def onSave(self):
		self._collectProfile(self._index)
		store = getStore()
		store.profiles = [copy.deepcopy(profile) for profile in self._profiles]
		store.activeProfileIndex = self._index
		store.save()
