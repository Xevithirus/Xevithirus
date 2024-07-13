import requests
from bs4 import BeautifulSoup

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

        # Initialize the player with the extracted contributions as total experience
        player = Player(total_exp=int(contribution_number))
        player.update_experience(contribution_number)

        print(player)
    else:
        print("Contributions data not found.")
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")


