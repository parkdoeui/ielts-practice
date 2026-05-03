import bs4
import re

with open("../scratch.html", "r") as f:
    soup = bs4.BeautifulSoup(f.read(), "html.parser")

entry_content = soup.find('div', class_='entry-content')

passages = []
current_passage = None
current_question_set = None

state = "PASSAGE" # PASSAGE, QUESTIONS

for child in entry_content.children:
    if child.name is None:
        continue
    
    text = child.get_text(strip=True)
    if not text:
        continue

    # Look for passage title
    if child.name in ['h2', 'h3', 'h4', 'h5', 'h6'] and not re.search(r'Questions \d+', text):
        state = "PASSAGE"
        current_passage = {"title": text, "text": []}
        passages.append(current_passage)
        print(f"NEW PASSAGE: {text}")
        continue
    
    # Question set boundary
    q_match = re.search(r'(?i)Questions\s+(\d+)-(\d+)', text)
    if q_match:
        state = "QUESTIONS"
        print(f"QUESTION SET: {q_match.group(1)} to {q_match.group(2)}")
        print(f"  Description: {text}")
        continue
    
    if state == "PASSAGE" and current_passage is not None:
        if child.name == 'p':
            current_passage["text"].append(text)
            print(f"  P: {text[:30]}...")

    if state == "QUESTIONS":
        if re.match(r'^\d+\s', text) or re.match(r'^\d+\.', text):
            print(f"  Q: {text[:50]}...")
        else:
            if "Reading Passage" in text and "Questions" not in text:
                print(f"  Other: {text[:50]}...")
                
# Find answers
answers_div = soup.find(lambda tag: tag.name == "div" and tag.get('class') and 'su-spoiler-content' in tag.get('class', []))
if answers_div:
    print("Found Answers div via su-spoiler-content")
    print(answers_div.text[:100])
else:
    # try looking for a table with answers
    tables = soup.find_all('table')
    for t in tables:
        if '1' in t.text and '2' in t.text:
            print("Found a table that might be answers")
            rows = t.find_all('tr')
            for r in rows[:5]:
                print("Row:", [td.text.strip() for td in r.find_all('td')])
