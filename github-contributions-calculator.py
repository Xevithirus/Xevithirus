import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

# -----------------------------------------------------------
#  Files
# -----------------------------------------------------------
DATA_FILE_PATH    = "total_exp.json"        # stores last_scraped + total_exp
BACKUP_FILE_PATH  = "total_exp_backup.json"
LOG_FILE_PATH     = "log.txt"

# -----------------------------------------------------------
#  Persistence helpers
# -----------------------------------------------------------
def load_data() -> dict:
    if os.path.exists(DATA_FILE_PATH):
        with open(DATA_FILE_PATH, "r") as f:
            raw = json.load(f)
            return {
                "total_exp":   int(raw.get("total_exp", 0)),
                "last_scraped": int(raw.get("last_scraped", 0)),
            }
    return {"total_exp": 0, "last_scraped": 0}


def save_data(data: dict) -> None:
    with open(DATA_FILE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def backup_exp(total_exp: int) -> None:
    with open(BACKUP_FILE_PATH, "w") as f:
        json.dump({"backup_exp": total_exp}, f, indent=2)

# -----------------------------------------------------------
#  Scrape helpers
# -----------------------------------------------------------
def fetch_yearly_contributions(user: str, headers: dict) -> int:
    """
    Return the integer '1234' from
      '1,234 contributions in the last year'
    raising RuntimeError if not found on either page.
    """
    for url in (
        f"https://github.com/users/{user}/contributions",
        f"https://github.com/{user}",
    ):
        r = requests.get(url, headers=headers, timeout=10)
        if not r.ok:  # pragma: no cover – network failure already fatal
            continue
        match = re.search(
            r"(\d[\d,]*)\s+contributions?\s+in\s+the\s+last\s+year",
            r.text,
            flags=re.I,
        )
        if match:
            return int(match.group(1).replace(",", ""))
    raise RuntimeError("Contribution count not found on either page")

# -----------------------------------------------------------
#  Levelling rules
# -----------------------------------------------------------
class Player:
    def __init__(self, total_exp: int) -> None:
        self.total_exp      = total_exp
        self.level          = 1
        self.required_exp   = 100   # threshold for level‑up from Lv 1
        self.prev_threshold = 0
        self.current_exp    = 0
        self._update_levels()

    def _update_levels(self) -> None:
        growth = 1.75                     # multiply the gap, not the total
        gap    = self.required_exp        # first gap = 100
        while self.total_exp >= self.required_exp:
            self.level         += 1
            self.prev_threshold = self.required_exp
            gap                = round(gap * growth)   # next gap
            self.required_exp  += gap                  # new threshold
        self.current_exp = self.total_exp - self.prev_threshold

    def to_dict(self) -> dict:
        return {
            "level":    self.level,
            "current":  self.current_exp,
            "required": self.required_exp,
            "total":    self.total_exp,
        }

# -----------------------------------------------------------
#  Main
# -----------------------------------------------------------
if __name__ == "__main__":
    USERNAME = "Xevithirus"

    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126.0.0.0 Safari/537.36"),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;"
                  "q=0.9,image/webp,*/*;q=0.8",
    }
    cookie = os.getenv("COOKIE")
    if cookie:
        headers["Cookie"] = cookie

    try:
        scraped = fetch_yearly_contributions(USERNAME, headers)
    except Exception as exc:
        print(f"Error: {exc}")
        exit(1)

    # -----------------------------------------------------------------
    #  EXP calculation with rollover + sanity checks
    # -----------------------------------------------------------------
    data          = load_data()
    delta         = scraped - data["last_scraped"]

    if delta < 0:                # New contribution year started
        delta = scraped
    if delta > 500:              # Safety net – avoid runaway commit loops
        print(f"Warning: suspicious EXP delta ({delta}); proceeding.")
        

    data["total_exp"]   += delta
    data["last_scraped"] = scraped
    save_data(data)
    backup_exp(data["total_exp"])   # always keep a fresh backup

    # -----------------------------------------------------------------
    #  Build player summary & log
    # -----------------------------------------------------------------
    player = Player(total_exp=data["total_exp"])
    with open(LOG_FILE_PATH, "a") as log:
        log.write(f"{datetime.utcnow().isoformat()}  "
                  f"scraped={scraped}  delta={delta}  "
                  f"total={player.total_exp}\n")

    # Print JSON for the caller
    print(json.dumps(player.to_dict()))
