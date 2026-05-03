import bs4

with open("../scratch.html", "r") as f:
    soup = bs4.BeautifulSoup(f.read(), "html.parser")

entry_content = soup.find('div', class_='entry-content')
if entry_content:
    for child in list(entry_content.children)[:30]:
        if child.name is None:
            continue
        print(f"<{child.name} class='{child.get('class', [])}'> {child.text.strip()[:60]}")
