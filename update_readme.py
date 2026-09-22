import json
import re
import subprocess
import sys
from pathlib import Path


# -----------------------------------------------------------
# Paths / configuration
# -----------------------------------------------------------

SCRAPER = [
    sys.executable,
    "github-contributions-calculator.py",
]

README_PATH = Path("README.md")
EXP_BAR_PATH = Path("images/exp-bar.svg")


# -----------------------------------------------------------
# EXP bar
# -----------------------------------------------------------

def make_exp_bar(current: int, required: int) -> str:
    """
    Generate the RPG EXP progress bar as an SVG file and return
    the HTML that should appear inside the README marker.
    """

    required = max(required, 1)

    progress = max(
        0.0,
        min(current / required, 1.0),
    )

    percent = progress * 100

    width = 220
    height = 18
    border = 2

    inner_width = width - (border * 2)
    inner_height = height - (border * 2)

    fill_width = round(inner_width * progress)

    # Make sure the images directory exists.
    EXP_BAR_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Build the SVG without triple-quoted strings.
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" '
        f'height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'

        f'  <rect '
        f'x="0" '
        f'y="0" '
        f'width="{width}" '
        f'height="{height}" '
        f'rx="2" '
        f'fill="#161b22" '
        f'stroke="#8b949e" '
        f'stroke-width="2" />\n'

        f'  <rect '
        f'x="{border}" '
        f'y="{border}" '
        f'width="{fill_width}" '
        f'height="{inner_height}" '
        f'rx="1" '
        f'fill="#58a6ff" />\n'

        f'  <line '
        f'x1="55" '
        f'y1="2" '
        f'x2="55" '
        f'y2="16" '
        f'stroke="#30363d" '
        f'stroke-width="1" />\n'

        f'  <line '
        f'x1="110" '
        f'y1="2" '
        f'x2="110" '
        f'y2="16" '
        f'stroke="#30363d" '
        f'stroke-width="1" />\n'

        f'  <line '
        f'x1="165" '
        f'y1="2" '
        f'x2="165" '
        f'y2="16" '
        f'stroke="#30363d" '
        f'stroke-width="1" />\n'

        f'</svg>\n'
    )

    EXP_BAR_PATH.write_text(
        svg,
        encoding="utf-8",
    )

    return (
        '<img src="./images/exp-bar.svg" '
        'alt="EXP Progress" height="18"> '
        f'{percent:.1f}%'
    )


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------

def main() -> None:
    # Run the contribution calculator.
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
            print(
                proc.stdout,
                file=sys.stderr,
            )

        if proc.stderr:
            print(
                proc.stderr,
                file=sys.stderr,
            )

        sys.exit(proc.returncode)

    # Parse calculator output.
    try:
        stats = json.loads(
            proc.stdout.strip()
        )

    except json.JSONDecodeError as exc:
        print(
            "Unexpected calculator output:",
            proc.stdout,
            file=sys.stderr,
        )

        raise RuntimeError(
            "Contribution calculator did not return valid JSON"
        ) from exc

    # Ensure all required values were returned.
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

    # -------------------------------------------------------
    # Generate current EXP bar
    # -------------------------------------------------------

    current_exp = int(stats["current"])
    required_exp = int(stats["required"])

    exp_bar_html = make_exp_bar(
        current_exp,
        required_exp,
    )

    # -------------------------------------------------------
    # Load README
    # -------------------------------------------------------

    content = README_PATH.read_text(
        encoding="utf-8",
    )

    # -------------------------------------------------------
    # Define automatic replacements
    # -------------------------------------------------------

    replacements = {
        r"<!--level-->.*?<!--/level-->":
            (
                f"<!--level-->"
                f"{stats['level']}"
                f"<!--/level-->"
            ),

        r"<!--total_exp-->.*?<!--/total_exp-->":
            (
                f"<!--total_exp-->"
                f"{stats['total']}"
                f"<!--/total_exp-->"
            ),

        r"<!--to_next_level-->.*?<!--/to_next_level-->":
            (
                f"<!--to_next_level-->"
                f"{exp_bar_html}"
                f"<!--/to_next_level-->"
            ),
    }

    # -------------------------------------------------------
    # Apply replacements
    # -------------------------------------------------------

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
                "Expected exactly one README marker "
                f"matching: {pattern}. Found {count}."
            )

    # -------------------------------------------------------
    # Save README
    # -------------------------------------------------------

    README_PATH.write_text(
        content,
        encoding="utf-8",
    )

    progress_percent = (
        current_exp
        / max(required_exp, 1)
        * 100
    )

    print(
        f"README updated: "
        f"Level {stats['level']}, "
        f"EXP {current_exp}/{required_exp} "
        f"({progress_percent:.1f}%), "
        f"Total {stats['total']}"
    )


if __name__ == "__main__":
    main()
