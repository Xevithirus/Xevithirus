import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# -----------------------------------------------------------
# Configuration
# -----------------------------------------------------------

USERNAME = "Xevithirus"

GRAPHQL_URL = "https://api.github.com/graphql"

DATA_FILE_PATH = Path("total_exp.json")
BACKUP_FILE_PATH = Path("total_exp_backup.json")
LOG_FILE_PATH = Path("log.txt")

BASE_EXP = 100
EXP_GROWTH = 1.75


# -----------------------------------------------------------
# GitHub API helpers
# -----------------------------------------------------------

def create_session(token: str) -> requests.Session:
    """
    Create a requests session with automatic retries for temporary
    GitHub/network failures.
    """

    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["POST"]),
    )

    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))

    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-exp-calculator",
    })

    return session


def graphql_request(
    session: requests.Session,
    query: str,
    variables: dict,
) -> dict:
    response = session.post(
        GRAPHQL_URL,
        json={
            "query": query,
            "variables": variables,
        },
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    if payload.get("errors"):
        raise RuntimeError(
            "GitHub GraphQL error: "
            + json.dumps(payload["errors"])
        )

    if "data" not in payload:
        raise RuntimeError("GitHub GraphQL response contained no data")

    return payload["data"]


def fetch_contribution_years(
    session: requests.Session,
    username: str,
) -> list[int]:
    """
    Ask GitHub which years contain contributions for this user.
    """

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionYears
        }
      }
    }
    """

    data = graphql_request(
        session,
        query,
        {"login": username},
    )

    user = data.get("user")

    if user is None:
        raise RuntimeError(f"GitHub user '{username}' was not found")

    years = user["contributionsCollection"]["contributionYears"]

    # Always include the current year even if there have not yet
    # been any contributions in it.
    current_year = datetime.now(timezone.utc).year

    years = set(int(year) for year in years)
    years.add(current_year)

    return sorted(years)


def fetch_year_contributions(
    session: requests.Session,
    username: str,
    year: int,
) -> int:
    """
    Return GitHub's contribution-calendar total for one calendar year.
    """

    now = datetime.now(timezone.utc)

    start = f"{year}-01-01T00:00:00Z"

    if year == now.year:
        end = now.isoformat().replace("+00:00", "Z")
    else:
        end = f"{year}-12-31T23:59:59Z"

    query = """
    query(
      $login: String!,
      $from: DateTime!,
      $to: DateTime!
    ) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """

    data = graphql_request(
        session,
        query,
        {
            "login": username,
            "from": start,
            "to": end,
        },
    )

    user = data.get("user")

    if user is None:
        raise RuntimeError(f"GitHub user '{username}' was not found")

    return int(
        user["contributionsCollection"]
        ["contributionCalendar"]
        ["totalContributions"]
    )


def fetch_lifetime_contributions(
    session: requests.Session,
    username: str,
) -> tuple[int, dict[str, int]]:
    """
    Recalculate lifetime contributions from every GitHub contribution year.

    Nothing is inferred from yesterday's value, so:
      - missed workflow runs do not matter
      - rolling 12-month expiry does not matter
      - year changes do not matter
    """

    years = fetch_contribution_years(session, username)

    yearly = {}

    for year in years:
        yearly[str(year)] = fetch_year_contributions(
            session,
            username,
            year,
        )

    lifetime_total = sum(yearly.values())

    return lifetime_total, yearly


# -----------------------------------------------------------
# Persistence helpers
# -----------------------------------------------------------

def load_existing_data() -> dict:
    if not DATA_FILE_PATH.exists():
        return {}

    try:
        return json.loads(
            DATA_FILE_PATH.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(
            f"Could not read {DATA_FILE_PATH}: {exc}"
        ) from exc


def write_json(path: Path, data: dict) -> None:
    """
    Write JSON through a temporary file so a partial write cannot
    corrupt the state file.
    """

    temp_path = Path(str(path) + ".tmp")

    temp_path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    temp_path.replace(path)


# -----------------------------------------------------------
# RPG levelling
# -----------------------------------------------------------

class Player:
    def __init__(self, total_exp: int) -> None:
        if total_exp < 0:
            raise ValueError("total_exp cannot be negative")

        self.total_exp = total_exp

        self.level = 1
        self.current_exp = 0
        self.required_exp = BASE_EXP
        self.remaining_exp = BASE_EXP
        self.next_threshold = BASE_EXP

        self._calculate_level()


    def _calculate_level(self) -> None:
        """
        Level curve:

        Level 1 -> 2 : 100 EXP
        Level 2 -> 3 : 175 EXP
        Level 3 -> 4 : 306 EXP
        Level 4 -> 5 : 536 EXP
        Level 5 -> 6 : 938 EXP
        ...

        Each level requires approximately 1.75x the previous level's EXP.
        """

        level = 1
        level_start = 0
        gap = BASE_EXP
        next_threshold = gap

        while self.total_exp >= next_threshold:
            level += 1

            level_start = next_threshold

            gap = round(gap * EXP_GROWTH)

            next_threshold = level_start + gap

        self.level = level
        self.current_exp = self.total_exp - level_start

        # EXP required within THIS level, rather than the
        # lifetime cumulative threshold.
        self.required_exp = gap

        self.remaining_exp = gap - self.current_exp

        self.next_threshold = next_threshold


    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "current": self.current_exp,
            "required": self.required_exp,
            "remaining": self.remaining_exp,
            "next_threshold": self.next_threshold,
            "total": self.total_exp,
        }


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------

def main() -> None:
    # Optional PROFILE_TOKEN can be supplied if you want private/internal
    # contribution counts. Otherwise use GitHub Actions' automatic token.
    token = (
        os.getenv("PROFILE_TOKEN")
        or os.getenv("GITHUB_TOKEN")
    )

    if not token:
        raise RuntimeError(
            "No GitHub API token available. "
            "Expected PROFILE_TOKEN or GITHUB_TOKEN."
        )

    session = create_session(token)

    lifetime_total, yearly = fetch_lifetime_contributions(
        session,
        USERNAME,
    )

    now = datetime.now(timezone.utc)
    timestamp = now.isoformat().replace("+00:00", "Z")

    # Keep yesterday's total as a meaningful backup.
    old_data = load_existing_data()

    if old_data:
        write_json(
            BACKUP_FILE_PATH,
            {
                "backup_exp": int(
                    old_data.get("total_exp", 0)
                ),
                "backed_up_at": timestamp,
            },
        )
    else:
        write_json(
            BACKUP_FILE_PATH,
            {
                "backup_exp": lifetime_total,
                "backed_up_at": timestamp,
            },
        )

    # last_scraped is retained for backwards compatibility,
    # but is no longer used in calculations.
    current_year = str(now.year)

    new_data = {
        "schema_version": 2,
        "total_exp": lifetime_total,
        "last_scraped": yearly.get(current_year, 0),
        "yearly_contributions": yearly,
        "updated_at": timestamp,
    }

    write_json(DATA_FILE_PATH, new_data)

    player = Player(lifetime_total)

    # Append a heartbeat every run. This also gives the profile repo
    # daily commit activity when the workflow commits the log.
    with LOG_FILE_PATH.open(
        "a",
        encoding="utf-8",
    ) as log:
        log.write(
            f"{timestamp}  "
            f"lifetime={lifetime_total}  "
            f"level={player.level}  "
            f"current={player.current_exp}  "
            f"required={player.required_exp}  "
            f"remaining={player.remaining_exp}  "
            f"yearly={json.dumps(yearly, sort_keys=True)}\n"
        )

    # IMPORTANT: stdout contains only JSON because update_readme.py
    # consumes this programmatically.
    print(json.dumps(player.to_dict()))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"github-contributions-calculator.py failed: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
