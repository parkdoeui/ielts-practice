import bs4

with open("../scratch.html", "r") as f:
    soup = bs4.BeautifulSoup(f.read(), "html.parser")

answers_div = soup.find('div', class_='su-spoiler-content')
if answers_div:
    print(answers_div.prettify()[:1000])
else:
    # See if "Show Answers" is followed by a container
    show_answers = soup.find(lambda tag: tag.name == 'p' and 'Show Answers' in tag.text)
    if show_answers:
        for sibling in show_answers.find_next_siblings()[:5]:
            print(sibling.name, sibling.get('class', []), sibling.text[:200])

