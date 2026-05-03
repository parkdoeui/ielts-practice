import bs4
import re
import json

with open("../scratch.html", "r") as f:
    soup = bs4.BeautifulSoup(f.read(), "html.parser")

entry_content = soup.find('div', class_='entry-content')

passages = []
questions_data = [] # List of dicts
answers = {}

current_passage_text = []
current_passage_title = ""
passage_count = 1

current_q_group = None
state = "PASSAGE" # PASSAGE or QUESTIONS

def flush_passage():
    global current_passage_text, current_passage_title, passage_count
    if current_passage_text:
        passages.append({
            "id": f"passage-{passage_count}",
            "title": current_passage_title or f"Passage {passage_count}",
            "text": "\n".join(current_passage_text)
        })
        current_passage_text = []
        current_passage_title = ""
        passage_count += 1

def parse_node(node):
    global state, current_q_group
    
    if node.name is None:
        return
        
    text = node.get_text(separator="\n", strip=True)
    if not text:
        return
        
    # Check if this node is the answers section
    if "Show Answers" in text and node.name in ['p', 'strong', 'h2', 'h3']:
        return # Skip it
        
    # Is it the actual answers list?
    if re.search(r'1\.\s+(yes|true|a|b|c|d|not given|false|no|.*)', text, re.IGNORECASE) and '2.' in text and '3.' in text:
        # It's the answers block!
        for br in node.find_all('br'):
            br.replace_with('\n')
        ans_text = node.get_text(separator="\n", strip=True)
        for line in ans_text.split('\n'):
            line = line.strip()
            match = re.match(r'^(\d+)\.\s+(.*)', line)
            if match:
                q_num = int(match.group(1))
                answers[q_num] = match.group(2).strip()
        return

    # Check for question block header
    q_match = re.search(r'(?i)Questions\s+(\d+)-(\d+)', text)
    if q_match:
        state = "QUESTIONS"
        current_q_group = {
            "start": int(q_match.group(1)),
            "end": int(q_match.group(2)),
            "instruction": text,
            "items": [],
            "passage_id": f"passage-{passage_count if not current_passage_text else passage_count + 1}"
        }
        # If we hit a question block, we flush the current passage if we were in PASSAGE state
        if current_passage_text:
            flush_passage()
            # The next passage_id will be passage_count
            current_q_group["passage_id"] = f"passage-{passage_count}"
        elif len(passages) > 0:
            current_q_group["passage_id"] = f"passage-{passage_count-1}"
            
        questions_data.append(current_q_group)
        return

    # Check for passage title (h1-h6) or explicitly "Reading Passage X"
    if node.name in ['h2', 'h3', 'h4', 'h5', 'h6'] or ("Reading Passage" in text and len(text) < 50):
        # We might be starting a new passage
        if state == "QUESTIONS":
            # Just transition back
            state = "PASSAGE"
        if current_passage_text:
            flush_passage()
        current_passage_title = text
        state = "PASSAGE"
        return

    if state == "PASSAGE":
        if node.name == 'p':
            current_passage_text.append(text)

    elif state == "QUESTIONS" and current_q_group:
        # Try to find questions in this text
        # Splitting by newline in case multiple questions are in one p tag
        for br in node.find_all('br'):
            br.replace_with('\n')
        
        lines = node.get_text(separator="\n", strip=True).split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Question item starts with digit(s) and a space or dot
            if re.match(r'^\d+[\s\.]', line):
                current_q_group["items"].append(line)
            else:
                # Might be an option, heading list, or extra instruction
                # We'll just append it to the last item or to instruction
                if current_q_group["items"]:
                    current_q_group["items"][-1] += "\n" + line
                else:
                    current_q_group["instruction"] += "\n" + line

for child in entry_content.children:
    parse_node(child)

if current_passage_text:
    flush_passage()

print(f"Parsed {len(passages)} passages.")
for p in passages:
    print(f"- {p['id']}: {p['title']} ({len(p['text'])} chars)")

print(f"\nParsed {len(questions_data)} question groups.")
total_qs = 0
for g in questions_data:
    print(f"- Q {g['start']}-{g['end']} [Passage {g['passage_id']}] ({len(g['items'])} items extracted)")
    for item in g['items'][:2]:
        print(f"    {item[:40]}...")
    total_qs += len(g['items'])
print(f"Total question items extracted: {total_qs}")
print(f"Total answers extracted: {len(answers)}")

