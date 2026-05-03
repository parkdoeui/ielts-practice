import bs4

with open("../scratch.html", "r") as f:
    soup = bs4.BeautifulSoup(f.read(), "html.parser")

show_answers = soup.find(lambda tag: tag.name == 'p' and 'Show Answers' in tag.text)
if show_answers:
    for sibling in show_answers.find_next_siblings()[:2]:
        print(sibling.name, sibling.get('class', []))
        print(sibling.encode_contents().decode('utf-8')[:500])

