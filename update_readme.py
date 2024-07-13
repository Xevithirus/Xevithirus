# update_readme.py

import re
import subprocess

# Run github-contributions-calculator.py and capture its output
result = subprocess.run(['python', 'github-contributions-calculator.py'], capture_output=True, text=True)

# Check if github-contributions-calculator.py executed successfully
if result.returncode == 0:
    # Split captured output into lines and parse values
    output_lines = result.stdout.strip().split('\n')
    level = int(output_lines[0])
    current_exp = int(output_lines[1])
    required_exp = int(output_lines[2])

    # Read the existing README.md content
    with open('README.md', 'r') as file:
        readme_content = file.read()

    # Update the placeholders in README.md with the calculated values
    readme_content = re.sub(r'{level}', str(level), readme_content)
    readme_content = re.sub(r'{current_exp}', f'{current_exp}/{required_exp}', readme_content)

    # Write the updated content back to README.md
    with open('README.md', 'w') as file:
        file.write(readme_content)

    print("README.md updated successfully.")
else:
    print("Failed to run github-contributions-calculator.py.")