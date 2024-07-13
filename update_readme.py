# update_readme.py

import re

# Read the existing README.md content
with open('README.md', 'r', encoding='utf-8') as file:
    readme_content = file.read()

# Parse the calculated stats from a file or subprocess output
with open('calculated_stats.txt', 'r') as stats_file:
    output_lines = stats_file.readlines()
    level = int(output_lines[0].strip())
    current_exp, required_exp = map(int, output_lines[1].strip().split('/'))

# Update the placeholders in README.md with the calculated values
readme_content = re.sub(r'{{level}}', str(level), readme_content)
readme_content = re.sub(r'{{current_exp}}', f'{current_exp}/{required_exp}', readme_content)

# Write the updated content back to README.md
with open('README.md', 'w', encoding='utf-8') as file:
    file.write(readme_content)

print("README.md updated successfully.")