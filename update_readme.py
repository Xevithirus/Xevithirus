"""
Runs the GitHub contribution calculator and updates only these README markers:

    <!--level-->...<!--/level-->
    <!--total_exp-->...<!--/total_exp-->
    <!--to_next_level-->...<!--/to_next_level-->

No other README content is modified.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


SCRAPER = [
    sys.executable,
    "github-contributions-calculator.py",
]

README_PATH = Path("README.md")


def main() -> None:
    proc = subprocess.run(
        SCRAPER,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        print(
            "github-contributions-calculator.py failed:",
            file=sys.stderr,
        )

        if proc.stdout:
            print(proc.stdout, file=sys.stderr)

        if proc.stderr:
            print(proc.stderr, file=sys.stderr)

        sys.exit(proc.returncode)


    try:
        stats = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as exc:
        print(
            "Unexpected calculator output:",
            proc.stdout,
            file=sys.stderr,
        )
        raise RuntimeError(
            "Contribution calculator did not return valid JSON"
        ) from exc


    required_keys = {
        "level",
        "current",
        "required",
        "total",
    }

    missing = required_keys - stats.keys()

    if missing:
        raise RuntimeError(
            f"Calculator output is missing: {sorted(missing)}"
        )


    content = README_PATH.read_text(encoding="utf-8")


    replacements = {
        r"<!--level-->.*?<!--/level-->":
            f"<!--level-->{stats['level']}<!--/level-->",

        r"<!--total_exp-->.*?<!--/total_exp-->":
            (
                f"<!--total_exp-->"
                f"{stats['total']}"
                f"<!--/total_exp-->"
            ),

        r"<!--to_next_level-->.*?<!--/to_next_level-->":
            (
                f"<!--to_next_level-->"
                f"{stats['current']}/{stats['required']}"
                f"<!--/to_next_level-->"
            ),
    }


    for pattern, replacement in replacements.items():
        content, count = re.subn(
            pattern,
            replacement,
            content,
            count=1,
            flags=re.S,
        )

        if count != 1:
            raise RuntimeError(
                f"Expected exactly one README marker matching: {pattern}. "
                f"Found {count}."
            )


    README_PATH.write_text(
        content,
        encoding="utf-8",
    )

    print(
        f"README updated: "
        f"Level {stats['level']}, "
        f"EXP {stats['current']}/{stats['required']}, "
        f"Total {stats['total']}"
    )


if __name__ == "__main__":
    main()
