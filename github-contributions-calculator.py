import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re    

EXP_FILE_PATH = 'total_exp.json'
BACKUP_EXP_FILE_PATH = 'total_exp_backup.json'
LOG_FILE_PATH = 'log.txt'

def load_saved_exp():
    if os.path.exists(EXP_FILE_PATH):
        with open(EXP_FILE_PATH, 'r') as f:
            return json.load(f).get('total_exp', 0)
    return 0

def save_total_exp(exp):
    with open(EXP_FILE_PATH, 'w') as f:
        json.dump({"total_exp": exp}, f)

def backup_exp(exp):
    with open(BACKUP_EXP_FILE_PATH, 'w') as f:
        json.dump({"backup_exp": exp}, f)

class Player:
    def __init__(self, total_exp=0):
        self.level = 1
        self.total_exp = total_exp
        self.current_exp = 0
        self.required_exp = 100
        self.prev_required_exp = 0

    def update_experience(self, new_total_exp):
        self.total_exp = int(new_total_exp)
        self.calculate_experience()

    def calculate_experience(self):
        while self.total_exp >= self.required_exp:
            self.level_up()
        self.current_exp = self.total_exp - self.prev_required_exp

    def level_up(self):
        self.level += 1
        self.prev_required_exp = self.required_exp
        self.required_exp += round(self.required_exp * 0.75)
        self.current_exp = 0

    def __str__(self):
        return (f"Level: {self.level}, Total EXP: {self.total_exp}, "
                f"Current EXP: {self.current_exp}, Required EXP: {self.required_exp}")

# -----------------------------------------------------------
# Request headers (add cookie only if provided by env)
# -----------------------------------------------------------
username = "Xevithirus"
url       = f"https://github.com/{username}"
alt_url   = f"https://github.com/users/{username}/contributions"   # fallback page

headers = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': url,
    'X-Requested-With': 'XMLHttpRequest',
}
cookie_env = os.getenv("COOKIE")
if cookie_env:
    headers['Cookie'] = cookie_env

# -----------------------------------------------------------
# Try profile page first
# -----------------------------------------------------------
response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    contributions = soup.find(
        'h2',
        string=re.compile(r'\d[\d,]* contribution[s]?', flags=re.I)
    )

    # ----------------- Fallback to contributions page -----------------
    if contributions is None:
        alt_resp = requests.get(alt_url, headers=headers)
        if alt_resp.status_code == 200:
            alt_soup = BeautifulSoup(alt_resp.text, 'html.parser')
            contributions = alt_soup.find(
                'h2',
                string=re.compile(r'\d[\d,]* contribution[s]?', flags=re.I)
            )
    # -----------------------------------------------------------------

    if contributions:
        contributions_text = contributions.text.strip()
        try:
            raw = contributions_text.split()[0].replace(',', '')  # remove commas
            contribution_number = int(raw)
        except (IndexError, ValueError):
            print("Error: Unable to parse contribution number.")
            exit(1)

        # Log the current contribution number
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(f"{datetime.utcnow().isoformat()} - Scraped Contribution Count: {contribution_number}\n")

        saved_total_exp = load_saved_exp()
        today = datetime.utcnow()

        if today.month == 1 and contribution_number < saved_total_exp:
            exp_to_add = contribution_number
        else:
            exp_to_add = contribution_number - saved_total_exp

        if exp_to_add < 0:
            print("Warning: Negative EXP delta detected. No EXP will be added.")
            exp_to_add = 0
        elif exp_to_add > 200:
            print(f"Warning: Suspiciously high EXP delta ({exp_to_add}) detected. Aborting update.")
            exit(1)

        new_total_exp = saved_total_exp + exp_to_add
        save_total_exp(new_total_exp)
        
        if 0 <= exp_to_add <= 200:
            backup_exp(new_total_exp)

        player = Player(total_exp=new_total_exp)
        player.update_experience(new_total_exp)

        print(player.level)
        print(player.current_exp)
        print(player.required_exp)
        print(player.total_exp)
    else:
        print("Contributions data not found.")
        exit(1)
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")
    exit(1)
