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
    total_exp = int(output_lines[3])

    # Read the existing README.md content
    with open('README.md', 'r') as file:
        readme_content = file.read()

    # Update the values in README.md using the markers
    readme_content = re.sub(r'<!--level-->.*?<!--/level-->', f'<!--level-->{level}<!--/level-->', readme_content)
    readme_content = re.sub(r'<!--total_exp-->.*?<!--/total_exp-->', f'<!--total_exp-->{total_exp}<!--/total_exp-->', readme_content)
    readme_content = re.sub(r'<!--to_next_level-->.*?<!--/to_next_level-->', f'<!--to_next_level-->{current_exp}/{required_exp}<!--/to_next_level-->', readme_content)


    # Write the updated content back to README.md
    with open('README.md', 'w') as file:
        file.write(readme_content)

    print("README.md updated successfully.")
else:
    print("Failed to run github-contributions-calculator.py.")
