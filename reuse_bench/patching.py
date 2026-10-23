"""Apply the single-file unified diffs that the builder stores as `task_patch`."""
from __future__ import annotations

import re

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


def apply_patch(source: str, patch: str) -> str:
    src = source.splitlines(keepends=True)
    lines = patch.splitlines(keepends=True)
    out: list[str] = []
    pos = i = 0
    while i < len(lines):
        match = HUNK.match(lines[i])
        i += 1
        if not match:
            continue    # file headers
        start = int(match.group(1)) - (0 if match.group(2) == "0" else 1)
        out += src[pos:start]
        pos = start
        while i < len(lines) and not lines[i].startswith("@@"):
            tag, text = lines[i][0], lines[i][1:]
            if tag in " -":
                if pos >= len(src) or src[pos] != text:
                    raise ValueError(f"patch does not apply at line {pos + 1}")
                pos += 1
            if tag in " +":
                out.append(text)
            i += 1
    return "".join(out + src[pos:])
