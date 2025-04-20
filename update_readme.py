"""
Runs the scraper, then patches the README placeholders:

   <!--level-->{num}<!--/level-->
   <!--total_exp-->{num}<!--/total_exp-->
   <!--to_next_level-->{x}/{y}<!--/to_next_level-->

Aborts loudly on any error so the GitHub Action surfaces it.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

SCRAPER = ["python", "github-contributions-calculator.py"]

proc = subprocess.run(SCRAPER, capture_output=True, text=True)

if proc.returncode != 0:
    print("github-contributions-calculator.py failed:\n", proc.stdout, proc.stderr)
    sys.exit(1)

try:
    stats = json.loads(proc.stdout)
except json.JSONDecodeError:
    print("Unexpected scraper output:\n", proc.stdout)
    sys.exit(1)

readme_path  = Path("README.md")
content      = readme_path.read_text(encoding="utf-8")

replacements = {
    r"<!--level-->.*?<!--/level-->":
        f"<!--level-->{stats['level']}<!--/level-->",
    r"<!--total_exp-->.*?<!--/total_exp-->":
        f"<!--total_exp-->{stats['total']}<!--/total_exp-->",
    r"<!--to_next_level-->.*?<!--/to_next_level-->":
        (f"<!--to_next_level-->"
         f"{stats['current']}/{stats['required']}"
         f"<!--/to_next_level-->"),
}

for pattern, repl in replacements.items():
    content = re.sub(pattern, repl, content, flags=re.S)

readme_path.write_text(content, encoding="utf-8")
print("README.md updated successfully.")
