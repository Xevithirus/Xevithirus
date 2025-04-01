import requests
from bs4 import BeautifulSoup
import json
import os

EXP_FILE_PATH = 'total_exp.json'
BACKUP_EXP_FILE_PATH = 'total_exp_backup.json'

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
        return f"Level: {self.level}, Total EXP: {self.total_exp}, Current EXP: {self.current_exp}, Required EXP: {self.required_exp}"

# Define the URL and parameters
url = 'https://github.com/Xevithirus'
params = {
    'action': 'show',
    'controller': 'profiles',
    'tab': 'contributions',
    'user_id': 'Xevithirus'
}

# Define the headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': 'https://github.com/Xevithirus',
    'X-Requested-With': 'XMLHttpRequest',
    'Cookie': '<Your-Cookie-Header-Value>'
}

# Send the GET request
response = requests.get(url, headers=headers, params=params)

# Check if the request was successful
if response.status_code == 200:
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the element containing the contributions
    contributions = soup.find('h2', class_='f4 text-normal mb-2')
    
    if contributions:
        # Extract the text and clean it up
        contributions_text = contributions.text.strip()

        # Split the string and get the first part (which should be the number)
        contribution_number = contributions_text.split()[0]

        # Convert extracted contribution string to int
        contribution_number = int(contribution_number)

        # Load saved EXP from file
        saved_total_exp = load_saved_exp()

        # Backup the previous EXP value
        backup_exp(saved_total_exp)

        # If the GitHub number reset, assume it's a new year and just add the new number
        if contribution_number < saved_total_exp:
            exp_to_add = contribution_number
        else:
            exp_to_add = contribution_number - saved_total_exp

        # Guard against negative values
        if exp_to_add < 0:
            print("Warning: Negative EXP delta detected. No EXP will be added.")
            exp_to_add = 0

        # Update and save the new running total EXP
        new_total_exp = saved_total_exp + exp_to_add
        save_total_exp(new_total_exp)

        # Initialize and update player with new total
        player = Player(total_exp=new_total_exp)
        player.update_experience(new_total_exp)

        # Print calculated stats to stdout
        print(player.level)
        print(player.current_exp)
        print(player.required_exp)
        print(player.total_exp)
    else:
        print("Contributions data not found.")
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")
