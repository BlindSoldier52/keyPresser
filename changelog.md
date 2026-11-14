# Key Presser changelog

This file lists what changed in the add-on, with the newest changes first. The version number is still 1.0, so the first section describes the fixes made to 1.0 after its first build.

## 1. Version 1.0, fixes from 15 November 2026

### 1.1 The warning no longer gets in the way of NVDA Remote

The warning used to be a message box that demanded an answer. While it was open, NVDA refused to open its menu, its settings, or to exit. If the box appeared on a computer you were controlling through NVDA Remote and it did not come to the front, the session became unusable.

The warning is now an ordinary small window that does not block anything. You can leave it open and keep working, and you close it with OK or Escape. It is also only remembered as seen once you actually close it, not the moment it appears, so you cannot miss it by accident.

### 1.2 Other fixes

- Secure screens: The add-on now does nothing on the Windows logon screen and on User Account Control prompts. Before, the warning could appear there if the add-on had been copied to the system configuration.
- Settings on older NVDA: NVDA+y now opens the settings on older NVDA versions too. It used to rely on a function that only newer versions have.
- Stopping during a long hold: NVDA+z now stops the presser at once, even if a key is being held down for a long time. Before, it announced that it had stopped but the key stayed down until the hold time ran out.
- Two runs at the same time: Starting again right after stopping can no longer leave the old run pressing keys alongside the new one.
- A finished run and a new one: A run that ended by itself, for example because it reached its repetition limit, can no longer mark a newer run as stopped.
- Spaces at the end of text: A text step such as "hello " now keeps its last space when it is saved. In the "Type the sequence" box, such a space is shown as `\s`. Text steps saved by earlier builds are read exactly as before.
- Spaces around the plus sign: A combination typed with spaces, such as `ctrl + ;`, is now accepted. It used to be rejected as an unknown key.

### 1.3 Documentation

The readme was rewritten in plain language, and this changelog was added.
