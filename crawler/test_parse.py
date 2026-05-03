import bs4

with open("../scratch.html", "r") as f:
    soup = bs4.BeautifulSoup(f.read(), "html.parser")

# Let's find "Reading Passage 1"
# We can search for the text.
passages = soup.find_all(lambda tag: tag.name in ["h2", "h3", "p", "div"] and "Reading Passage 1" in tag.text)
for p in passages:
    print(p.name, p.get('class', []), p.text.strip()[:50])

print("---")
# Look for questions 1-4 or something similar
questions = soup.find_all(lambda tag: tag.name in ["h2", "h3", "p", "strong"] and "Questions" in tag.text)
for q in questions[:5]:
    print(q.name, q.get('class', []), q.text.strip()[:50])

print("---")
# Find answers, maybe "Answers" or a specific table or div
answers = soup.find_all(lambda tag: tag.name in ["h2", "h3", "h4", "p", "strong"] and "Answer" in tag.text)
for a in answers[:5]:
    print(a.name, a.get('class', []), a.text.strip()[:50])
