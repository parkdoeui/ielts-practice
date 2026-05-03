import bs4
import re

with open("../scratch.html", "r") as f:
    soup = bs4.BeautifulSoup(f.read(), "html.parser")

entry_content = soup.find('div', class_='entry-content')
if entry_content:
    print("Found entry-content")
    for child in entry_content.children:
        if child.name is None:
            continue
        text = child.get_text(strip=True)
        if text.startswith("Questions"):
            print("--- Question block ---")
            print(child.name, child.get('class', []), text[:100])
        elif child.name == 'p' and "Reading Passage" in text:
            print("--- Reading Passage block ---")
            print(child.name, child.get('class', []), text[:100])
        elif re.match(r'^\d+\s', text):
            print("--- Possible question item ---")
            print(child.name, child.get('class', []), text[:100])
        elif child.name == 'div' and child.get('id') == 'collapse1':
            print("--- Found Answers ---")
            print(child.text[:200])
