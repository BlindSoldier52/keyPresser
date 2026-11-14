import os
import sys
import zipfile

import build

ROOT = os.path.dirname(os.path.abspath(__file__))


def release():
	bundle = build.build()
	version = build.readVersion()
	name = "keyPresser-%s" % version
	target = os.path.join(ROOT, "%s-release.zip" % name)
	if os.path.exists(target):
		os.remove(target)
	contents = (
		(bundle, os.path.basename(bundle)),
		(os.path.join(ROOT, "addon", "doc", "en", "readme.html"), "documentation.html"),
		(os.path.join(ROOT, "install.txt"), "install.txt"),
	)
	with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
		for path, inside in contents:
			archive.write(path, "%s/%s" % (name, inside))
	print(target)
	return target


if __name__ == "__main__":
	sys.exit(0 if release() else 1)
