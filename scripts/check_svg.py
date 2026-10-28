#!/usr/bin/env python3
"""Validate local SVG assets and README image references using only stdlib."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
README = ROOT / "README.md"
MAX_BYTES = 120 * 1024


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def validate_svg(path: Path) -> list[str]:
    errors: list[str] = []
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    if len(raw) >= MAX_BYTES:
        errors.append(f"{path}: {len(raw)} bytes (must be < {MAX_BYTES})")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        return [f"{path}: XML parse error: {exc}"]
    if "viewBox" not in root.attrib:
        errors.append(f"{path}: missing viewBox")
    if root.attrib.get("role") != "img":
        errors.append(f'{path}: missing role="img"')
    if not root.attrib.get("aria-label"):
        errors.append(f"{path}: missing aria-label")
    for node in root.iter():
        name = local_name(node.tag)
        if name == "script":
            errors.append(f"{path}: contains <script>")
        if name == "foreignobject":
            errors.append(f"{path}: contains <foreignObject>")
        for key, value in node.attrib.items():
            if local_name(key) == "href" and re.match(r"\s*(?:https?:|data:)", value, re.I):
                errors.append(f"{path}: external or data href: {value[:60]}")
    if re.search(r"@import|url\(\s*['\"]?https?", text, re.I):
        errors.append(f"{path}: contains prohibited CSS import/URL")
    return errors


def readme_images() -> list[str]:
    text = README.read_text(encoding="utf-8")
    refs = re.findall(r"(?:src|srcset)=[\"']([^\"']+)[\"']", text, re.I)
    return sorted({ref for ref in refs if not re.match(r"https?://", ref, re.I)})


def main() -> int:
    errors: list[str] = []
    svgs = sorted(ASSETS.glob("*.svg"))
    if not svgs:
        errors.append("assets/: no SVG files found")
    for svg in svgs:
        errors.extend(validate_svg(svg))
    for ref in readme_images():
        target = (ROOT / ref).resolve()
        if not target.is_file():
            errors.append(f"README.md: missing image path {ref}")
    if errors:
        print("SVG validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OK: {len(svgs)} SVG files valid; all README image paths exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
