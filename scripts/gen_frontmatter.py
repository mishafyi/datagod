#!/usr/bin/env python3
"""Add/refresh the skill-style YAML frontmatter on the hand-written per-source docs
(EDGAR, Nasdaq, yfinance, NARA, NSArchive, Smithsonian, Wilson, House FD, JEFS).

Run from the project root:

    .venv/bin/python -m scripts.gen_frontmatter

Idempotent: replaces an existing frontmatter block or prepends a new one, leaving
the hand-written body untouched. name/description/keywords come from the shared
SOURCE_DESC / SOURCE_KEYWORDS in gen_api_guide; routes come from the live schema.
"""

from pathlib import Path

from scripts.gen_api_guide import SOURCE_DESC, SOURCE_KEYWORDS, _grouped

# tag -> existing hand-written doc filename.
SOURCE_FILE = {
    "EDGAR": "EDGAR_API.md",
    "Nasdaq": "NASDAQ_API.md",
    "yfinance": "YFINANCE_API.md",
    "NARA": "NARA_API.md",
    "NSArchive": "NSARCHIVE_API.md",
    "Smithsonian": "SMITHSONIAN_API.md",
    "Wilson Center": "WILSON_DIGITAL_ARCHIVE_API.md",
    "House Disclosures": "HOUSE_FD_API.md",
    "JEFS": "JEFS_API.md",
}


def frontmatter(tag: str, paths: list[str]) -> str:
    name = tag.lower().replace(" ", "-")
    return (
        "---\n"
        f"name: {name}\n"
        f'description: "{SOURCE_DESC.get(tag, "")}"\n'
        f'keywords: "{SOURCE_KEYWORDS.get(tag, "")}"\n'
        f'routes: "{", ".join(sorted(paths))}"\n'
        "---\n"
    )


def main() -> None:
    docs = Path(__file__).parent.parent / "docs"
    _order, _tag_desc, grouped = _grouped()
    for tag, filename in SOURCE_FILE.items():
        path = docs / filename
        if not path.exists():
            print(f"skip {filename} (missing)")
            continue
        body = path.read_text()
        if body.startswith("---\n"):
            end = body.find("\n---\n", 4)
            if end != -1:
                body = body[end + 5:].lstrip("\n")
        paths = [route for _m, route, _op in grouped.get(tag, [])]
        path.write_text(frontmatter(tag, paths) + "\n" + body.lstrip("\n"))
        print(f"frontmatter -> {filename}")


if __name__ == "__main__":
    main()
