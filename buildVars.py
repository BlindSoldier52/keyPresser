addon_info = {
	"addon_name": "keyPresser",
	"addon_summary": "Key Presser",
	"addon_description": "Sends keystrokes, typed text or mouse clicks repeatedly at a configurable interval.",
	"addon_version": "1.0",
	"addon_author": "BlindSoldier52",
	"addon_url": "https://github.com/BlindSoldier52/keyPresser",
	"addon_docFileName": "readme.html",
	"addon_minimumNVDAVersion": "2019.3",
	"addon_lastTestedNVDAVersion": "2026.1",
	"addon_updateChannel": None,
}

pythonSources = ["addon/globalPlugins/keyPresser/*.py"]
i18nSources = pythonSources + ["buildVars.py"]
excludedFiles = []
