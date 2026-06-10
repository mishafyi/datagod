#!/usr/bin/env python3
"""Regenerate the endpoint section of docs/REFERENCE.md from the OpenAPI schema.

Run from the project root after adding or changing routes:

    .venv/bin/python -m scripts.gen_reference_doc

Only the block between the BEGIN/END markers is rewritten; the hand-written prose
(architecture, how-it-works, etc.) is preserved. The interactive Swagger UI at
/docs remains the source of truth.
"""

import re
from pathlib import Path

from app.main import app

BEGIN = "<!-- BEGIN GENERATED ENDPOINTS -->"
END = "<!-- END GENERATED ENDPOINTS -->"
_HTTP_METHODS = ("get", "post", "put", "delete", "patch")


def _type(schema: dict) -> str:
    if not schema:
        return ""
    if "type" in schema:
        if schema["type"] == "array":
            item = (schema.get("items") or {}).get("type", "")
            return f"array[{item}]" if item else "array"
        return schema["type"]
    if "anyOf" in schema:
        types = [s.get("type") for s in schema["anyOf"] if s.get("type") and s.get("type") != "null"]
        return " \\| ".join(dict.fromkeys(types))
    return ""


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def render_endpoints() -> str:
    schema = app.openapi()
    tags = schema.get("tags", [])
    order = [tag["name"] for tag in tags]
    descriptions = {tag["name"]: tag.get("description", "") for tag in tags}

    grouped: dict[str, list[tuple[str, str, dict]]] = {}
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in _HTTP_METHODS:
                continue
            tag = (operation.get("tags") or ["(untagged)"])[0]
            grouped.setdefault(tag, []).append((method.upper(), path, operation))

    lines: list[str] = []
    for tag in order:
        rows = grouped.get(tag)
        if not rows:
            continue
        lines.append(f"### {tag}")
        if descriptions.get(tag):
            lines += ["", f"_{descriptions[tag]}_"]
        lines.append("")
        for method, path, op in sorted(rows, key=lambda row: row[1]):
            lines.append(f"#### `{method} {path}`")
            lines.append("")
            if op.get("summary"):
                lines.append(f"**{op['summary']}**")
                lines.append("")
            desc = (op.get("description") or "").strip()
            if desc and desc != op.get("summary", ""):
                lines.append(desc)
                lines.append("")
            params = op.get("parameters", [])
            if params:
                lines.append("| Parameter | In | Type | Required | Default | Description |")
                lines.append("|-----------|----|------|----------|---------|-------------|")
                for p in params:
                    sch = p.get("schema", {}) or {}
                    default = sch.get("default", "")
                    lines.append(
                        f"| `{p['name']}` | {p.get('in', '')} | {_type(sch)} | "
                        f"{'yes' if p.get('required') else 'no'} | "
                        f"{_cell(default) if default != '' else ''} | "
                        f"{_cell(p.get('description', ''))} |"
                    )
            else:
                lines.append("_No parameters._")
            lines.append("")
    return "\n".join(lines).rstrip()


def main() -> None:
    ref = Path(__file__).parent.parent / "docs" / "REFERENCE.md"
    text = ref.read_text()
    block = f"{BEGIN}\n\n{render_endpoints()}\n\n{END}"
    new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _m: block, text, count=1, flags=re.S)
    if new == text and BEGIN not in text:
        raise SystemExit("markers not found in docs/REFERENCE.md")
    ref.write_text(new)
    print(f"updated endpoint section in {ref}")


if __name__ == "__main__":
    main()
