"""Attach source-aware hooks without replacing the upstream package recipe."""
from pathlib import Path
import re
import shutil
import sys

INCLUDE = "include $(CURDIR)/miniupnpd-backports/hooks.mk"


def install(package):
    makefile = package / "Makefile"
    text = makefile.read_text(encoding="utf-8")
    target = re.search(r"^\$\(eval \$\(call BuildPackage,miniupnpd-[^)]+\)\)", text, re.M)
    if not target:
        raise ValueError("MiniUPnP BuildPackage entry not found; review upstream recipe")
    if INCLUDE not in text:
        text = text[:target.start()] + INCLUDE + "\n\n" + text[target.start():]
    elif text.count(INCLUDE) != 1 or text.index(INCLUDE) > target.start():
        raise ValueError("MiniUPnP hook include is duplicated or too late")
    source = Path(__file__).resolve().parent
    shutil.copytree(source, package / "miniupnpd-backports", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "install.py"))
    makefile.write_text(text, encoding="utf-8", newline="\n")
    print(f"Installed upgrade-aware MiniUPnP hooks in {package}")


if __name__ == "__main__":
    try:
        install(Path(sys.argv[1]))
    except (OSError, ValueError, IndexError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
