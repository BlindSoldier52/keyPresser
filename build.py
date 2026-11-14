import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ROOT, "addon")
SKIPPED_DIRECTORIES = {"__pycache__", ".git"}
SKIPPED_EXTENSIONS = {".pyc", ".pyo"}


def readVersion():
	manifest = os.path.join(SOURCE, "manifest.ini")
	with open(manifest, encoding="utf-8") as source:
		for line in source:
			if line.strip().startswith("version"):
				return line.split("=", 1)[1].strip()
	return "1.0"


def build():
	version = readVersion()
	target = os.path.join(ROOT, "keyPresser-%s.nvda-addon" % version)
	if os.path.exists(target):
		os.remove(target)
	with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
		for folder, directories, files in os.walk(SOURCE):
			directories[:] = [name for name in directories if name not in SKIPPED_DIRECTORIES]
			for name in files:
				if os.path.splitext(name)[1].lower() in SKIPPED_EXTENSIONS:
					continue
				path = os.path.join(folder, name)
				archive.write(path, os.path.relpath(path, SOURCE).replace(os.sep, "/"))
	print(target)
	return target


if __name__ == "__main__":
	sys.exit(0 if build() else 1)
