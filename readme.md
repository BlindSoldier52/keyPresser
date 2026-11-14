# Key Presser, an add-on for NVDA

## 1. What it is

Key Presser presses things for you, over and over, at an interval that you choose. It can press a single key, play a whole sequence of keys, type a piece of text, or click a mouse button.

I wrote it so that it also works in games. Many games ignore the normal way of faking a key press, because they read the keyboard at a lower level, so the add-on sends hardware scan codes by default. This reaches games built on SDL, DirectInput and Unity, and it still works in ordinary Windows programs and browsers.

Everything the add-on says and shows is in English.

## 2. Warning

This add-on was written for experiments only. I don't encourage cheating with this.

You will see the same warning in a small window the first time the add-on runs. Once you close it with OK or Escape, it never comes back by itself. If you want to read it again, there is a button for that in the settings, and a command you can give a gesture to.

The window does not block NVDA while it is open, so you can keep using the NVDA menu, the settings and NVDA Remote even if you have not closed it yet.

## 3. Installing

Press Enter on `keyPresser-1.0.nvda-addon`, confirm the question, then restart NVDA when it offers to. Alternatively, open the NVDA menu, go to Tools, then Add-on store, choose Install from external source, and pick the file.

The add-on needs NVDA 2019.3 or newer. It is meant to work on every version from there up, which is why it avoids anything that only exists in recent releases.

## 4. Using it

Out of the box, the add-on presses the space bar once a second, after a spoken countdown of three seconds. The countdown is there so that you have time to move to the window you want the keys to go to.

There are four commands that work straight away, so I will just list them.

- NVDA+y: Opens the Key Presser settings.
- NVDA+j: Starts the presser with the active profile, or stops it if it is already running.
- NVDA+z: Stops the presser immediately, from anywhere, even in the middle of a long key hold.
- NVDA+alt+z: Switches to the next profile.

The following commands have no gesture until you give them one. To do that, open the NVDA menu, go to Preferences, then Input gestures, and look under the Key Presser category.

- Report status: Tells you whether the presser is running, which profile is active, and how many actions were sent.
- Increase interval and Decrease interval: Change the interval of the active profile by 50 milliseconds. These work while the presser is running, so you can speed it up or slow it down live.
- Lock to the foreground program: Makes the active profile run only in the program you are in right now.
- Remove the program restriction: Lets the active profile run in any program again.
- Show the warning: Opens the warning window again.

## 5. What it can do

This section is a short tour. The full manual, with every setting explained, is in `addon/doc/en/readme.html`, and you can also open it from the Add-on store with the Help button.

### 5.1 Profiles

A profile is a complete set of options saved under a name. You can create, duplicate, rename and delete profiles in the settings, then switch between them with NVDA+alt+z without opening the settings at all.

### 5.2 Sequences and steps

A profile holds as many named sequences as you like, and each one has a tick box. Only the ticked sequences run, one after another, and the others stay stored for later. This is how you can keep an Attack sequence and a Chat sequence side by side and turn one off without losing it.

A sequence is made of steps, and there are four kinds of step.

- Key: One key, or a combination such as Control+A. You pick it from a chooser with 124 keys in 10 categories, so nothing has to be typed by hand.
- Text: A piece of text that is typed out for you. It is sent as Unicode, so the keyboard layout does not matter, and each line break becomes a real Enter press.
- Random: One step with several options, where one is picked at random every time the step runs. This keeps a repeated message from being identical every cycle.
- Pause: A wait of as many milliseconds as you like before the next step.

If a game wants an exact hardware code, the chooser has a Raw code category that accepts `vk:0x41` for a virtual key code or `sc:0x1E` for a scan code.

If you would rather write a sequence out by hand, the "Type the sequence" button accepts the steps separated by commas, for example `ctrl+a, text:hello, wait:500, f5`. Inside a text step, a comma is written `\,`, a line break `\n`, a backslash `\\`, and a space at the very end of the text `\s`.

### 5.3 Mouse

Instead of keys, a profile can click a mouse button. The choices are left, right, middle, the fourth and fifth buttons, and the wheel up or down.

### 5.4 Timing

The interval can be anything from 1 millisecond to one hour. The add-on schedules each press against the clock rather than against the previous press, so it does not drift during long runs.

You can also add a random variation to the interval, choose how long each key is held down, set the pause between the steps of a sequence, and set the typing speed of text steps. Some games ignore very short presses, so if a game does not react, raise the hold time to 30 or 50 milliseconds.

### 5.5 Limits and safety

The presser can stop by itself after a number of actions or after a number of seconds. It can also be told to run only while certain programs are in the foreground, in which case it pauses when you switch away and resumes when you come back.

NVDA+z always stops it, and any key that was still held down is released at once.

### 5.6 Feedback

The add-on can beep when it starts, pauses, resumes and stops, speak status messages, and announce the action count every so many actions. It can also silence NVDA's typed character and command key announcements while it runs, so NVDA does not read every pressed key back to you. Your previous settings are put back when it stops.

## 6. Things to know

Some things may not work as you expect, so here they are.

- The keys go to whichever window has the focus. Make sure the right window is in front before the countdown ends, or use the program restriction.
- A program that runs as administrator only accepts the keys if NVDA is also running as administrator.
- The add-on does nothing on secure screens, such as the Windows logon screen and User Account Control prompts.
- The option that silences typed characters changes NVDA's own keyboard settings while the presser runs. If NVDA is closed by force during a run, those settings can stay off, and you will have to turn them on again in NVDA's keyboard settings.

## 7. Where the settings are kept

The settings are saved in `%APPDATA%\nvda\keyPresser\settings.json`. They live outside the add-on's own folder, so they survive updating or reinstalling it.

## 8. Building from source

You need Python 3. Run this in the project folder:

```
python build.py
```

This creates `keyPresser-<version>.nvda-addon` next to the script. The version is read from `addon/manifest.ini`.

If you also want an archive to hand to other people, run `python release.py`. It builds the add-on and then packs it together with the manual and `install.txt` into `keyPresser-<version>-release.zip`.

For quick testing without building, you can copy the folder `addon/globalPlugins/keyPresser` into `%APPDATA%\nvda\globalPlugins`.

## 9. How the source is organized

The code is in `addon/globalPlugins/keyPresser`, and each file has one job.

- `__init__.py`: The plugin itself. It defines the commands and their gestures.
- `engine.py`: The loop that does the pressing. It handles the timing, pausing, limits and stopping.
- `keymap.py`: Turns key names such as `ctrl+a` into codes, and describes steps in words for the settings.
- `sendinput.py`: Talks to Windows to send the keys, text and mouse clicks.
- `settingsgui.py`: The settings panel, its small dialogs, and the warning window.
- `store.py`: Loads and saves the profiles.

Outside that folder, `addon/manifest.ini` describes the add-on to NVDA, `addon/doc/en/readme.html` is the manual, and `changelog.md` lists what changed between builds.

The built `.nvda-addon` file and the release archive are not kept in the repository, because they are produced from the source. If you only want to install the add-on, look for the ready-made file on the Releases page of the project.

## 10. License

Key Presser is free software, released under the GNU General Public License, version 2. This is the same license NVDA itself uses, and add-ons have to follow it because they run inside NVDA. The full text is in the `LICENSE` file.
