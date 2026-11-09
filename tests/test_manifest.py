#!/usr/bin/env python3
"""Manifest check for SKILL.md.

This is stricter than the old name/description/version check: it verifies the
frontmatter fields the loader/host may rely on. It still does not replace a
real DSH loader test.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
skill = root / "SKILL.md"
text = skill.read_text(encoding="utf-8")
if not text.startswith("---\n"):
    raise SystemExit("SKILL.md: missing frontmatter")
end = text.find("\n---\n", 4)
if end == -1:
    raise SystemExit("SKILL.md: unclosed frontmatter")
frontmatter = text[4:end]
fields: dict[str, str] = {}
for line in frontmatter.splitlines():
    if ":" in line and not line.startswith((" ", "\t")):
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()

required = ("name", "description", "version", "allowed-tools", "triggers", "metadata")
missing = [key for key in required if key not in fields]
if missing:
    raise SystemExit(f"SKILL.md: missing fields {missing}")
if fields["name"] != root.name:
    raise SystemExit(f"SKILL.md: name={fields['name']} does not match folder={root.name}")
version = fields["version"].strip('"\'')
if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version):
    raise SystemExit(f"SKILL.md: version is not semver-like: {fields['version']}")
if "license:" not in frontmatter:
    raise SystemExit("SKILL.md: metadata.license missing")
if "requires:" not in frontmatter:
    raise SystemExit("SKILL.md: metadata.requires missing")
if not re.search(r"^triggers:\s*$", frontmatter, re.MULTILINE):
    raise SystemExit("SKILL.md: triggers must be a block list")
if not re.search(r"^  - .+", frontmatter, re.MULTILINE):
    raise SystemExit("SKILL.md: no list items found (allowed-tools/triggers)")

print(f"manifest ok: {fields['name']} {fields['version']}")
print("note: this checks the manifest, not the DSH loader")
