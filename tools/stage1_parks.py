"""Idempotent editorial postprocessing for exactly two stage-one park pages.

Run after the normal page/style generators: python tools/stage1_parks.py
Optional --slug selects one pilot; there is no mode that writes other parks.
Facts live in tools/data/stage1_parks.json. This script never invents entrances.
"""
import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tools/data/stage1_parks.json"
LABELS = {"sight": "Достопримечательность", "museum": "Музей", "view": "Смотровая",
          "art": "Скульптура", "food": "Кафе", "play": "Детская площадка",
          "wc": "Туалет", "water": "Питьевая вода"}


def esc(value):
    return html.escape(str(value), quote=True)


def marked(name, content):
    return f"<!-- STAGE1-PARK:{name}:START -->\n{content}\n<!-- STAGE1-PARK:{name}:END -->"


def strip_blocks(page):
    return re.sub(r"<!-- STAGE1-PARK:([\w-]+):START -->.*?<!-- STAGE1-PARK:\1:END -->\n?", "", page, flags=re.S)


def source_link(data, key, label="Источник"):
    return f'<a href="{esc(data["sources"][key]["url"])}">{esc(label)}</a>'


def inside_ring(lon, lat, ring):
    """Ray casting; relation is to the site's contour, not a legal boundary."""
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def cofix_description(data, park, source_park):
    cafe = park.get("cofix")
    if not cafe:
        return None
    relation = any(inside_ring(cafe["lon"], cafe["lat"], ring) for ring in source_park["p"])
    position = "Внутри контура парка на этой карте" if relation else "Рядом с парком, вне контура на этой карте"
    return (f'Кофейня. {position}. Адрес из каталога сети: {cafe["address"]}. '
            f'Каталог просмотрен {data["checked"]}.')


def before_map(data, park, center, records):
    features = "".join(f'<h3>{esc(item["title"])}</h3><p>{esc(item["text"])} '
                       f'{source_link(data, item["source"])}.</p>' for item in park["features"])
    # No entrance coordinates are inferred from center, boundary or metro.
    if park.get("entrance"):
        raise ValueError("A verified entrance requires explicit route implementation and source review")
    toilets = sum(row[2] == "wc" for row in records)
    wc = (f"В выгрузке OpenStreetMap — {toilets} записи; наличие и работа на месте не проверены."
          if toilets else "В выгрузке OpenStreetMap туалеты не найдены; наличие на месте не проверено.")
    location = f'https://www.openstreetmap.org/?mlat={center[1]}&mlon={center[0]}#map=16/{center[1]}/{center[0]}'
    return marked("visit", f'''<section class="stage1-park" aria-labelledby="stage1-why">
<h2 id="stage1-why">Зачем идти</h2><p>{esc(park["audience"])}</p>{features}
</section>
<section class="stage1-park" aria-labelledby="stage1-access">
<h2 id="stage1-access">Как попасть</h2><p>{esc(park["approach"])} {source_link(data, park["approach_source"])}.</p>
<p class="stage1-status">Вход и маршрут прогулки пока не проверены.</p>
<p><a href="{esc(location)}">Показать парк на карте ↗</a></p><p class="stage1-note">На карте — территория парка.</p>
</section>
<section class="stage1-park" aria-labelledby="stage1-before">
<h2 id="stage1-before">Перед посещением</h2>
<dl><dt>Вход и часы</dt><dd>Режим работы и условия входа уточняются.</dd>
<dt>С коляской</dt><dd>Доступность с коляской не проверена.</dd>
<dt>Туалеты</dt><dd>{esc(wc)}</dd></dl>
</section>''')


def reference(data, park, records, date, source_park):
    toilets = sum(row[2] == "wc" for row in records)
    wc = (f"В выгрузке найдены записи туалетов: {toilets}. Это не число подтверждённых работающих туалетов."
          if toilets else "В используемой выгрузке туалеты не найдены. Это не подтверждает их отсутствие в парке.")
    items = []
    description = cofix_description(data, park, source_park)
    for lat, lon, category, name in records:
        url = f'https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}'
        extra = ""
        cafe = park.get("cofix")
        if cafe and name == cafe["name"] and lat == cafe["lat"] and lon == cafe["lon"]:
            extra = f'<p>{esc(description)} {source_link(data, cafe["source"], "Официальный каталог сети")}.</p>'
        items.append(f'<li><a href="{esc(url)}">{esc(name)}</a> — {esc(LABELS.get(category, category))}{extra}</li>')
    empty = "<li>В этой выгрузке объекты не найдены. Реестр может быть неполным.</li>"
    sources = "".join(f'<li>{source_link(data, key, data["sources"][key]["title"])}. '
                      f'{esc(data["sources"][key]["scope"])}</li>' for key in park["sources"])
    return marked("reference", f'''<section class="stage1-park" aria-labelledby="stage1-directory">
<h2 id="stage1-directory">Справочник объектов из OpenStreetMap</h2>
<p>Выгрузка {esc(date)}. Выборка включает контур парка и небольшой запас у его границы: часть заведений может находиться рядом с парком. Список может быть неполным.</p>
<p>{esc(wc)}</p><details><summary>Текстовый список и внешние карты ({len(records)})</summary>
<p class="stage1-note">Доступен и без интерактивной карты. Ссылки показывают точку из OSM, а не проверенный вход.</p><ul>{''.join(items) or empty}</ul></details>
</section>
<section class="stage1-park"><details><summary id="stage1-sources">Источники и проверка</summary>
<p>Редакционные источники просмотрены {esc(data["checked"])}. Это дата обращения к документам, а не обследования на месте; старые публикации не подтверждают текущий режим работы.</p><ul>{sources}</ul>
<p class="stage1-note">Координаты объектов и контур — OpenStreetMap, выгрузка {esc(date)}. Сведения о входах и готовом маршруте пока не подтверждены.</p></details></section>''')


def build(slugs=None):
    data = json.loads(DATA.read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / "parks/catalog/parks.json").read_text(encoding="utf-8"))
    places = json.loads((ROOT / "parks/catalog/places.json").read_text(encoding="utf-8"))
    source = (ROOT / "parks.html").read_text(encoding="utf-8")
    park_shapes = json.loads(re.search(r"const PARKS = (.*?);\n", source).group(1))
    selected = slugs or list(data["parks"])
    for slug in selected:
        if slug not in data["parks"]:
            raise ValueError(f"Not a pilot: {slug}")
        park = data["parks"][slug]
        path = ROOT / "parks" / slug / "index.html"
        page = strip_blocks(path.read_text(encoding="utf-8"))
        info = next(item for item in catalog if item["id"] == park["id"])
        if f'window.PARK_ID="{park["id"]}"' not in page:
            raise ValueError(f"Unexpected park id in {path}")
        source_park = park_shapes[int(park["id"]) - 1]
        config = {"id": park["id"], "slug": slug, "checked": data["checked"]}
        if park.get("cofix"):
            cafe = park["cofix"]
            config["cofix"] = {**cafe, "description": cofix_description(data, park, source_park),
                               "url": data["sources"][cafe["source"]]["url"]}
            if not any(row[:2] == [cafe["lat"], cafe["lon"]] and row[3] == cafe["name"]
                       for row in places["parks"].get(park["id"], [])):
                raise ValueError("Cofix identity/coordinates changed; review before enrichment")
        head = marked("head", '<link rel="stylesheet" href="../../assets/stage1-parks.css?v=20261114b">\n'
                      + '<script>window.PARK_STAGE1=' + json.dumps(config, ensure_ascii=False).replace("<", "\\u003c") + ';</script>\n'
                      + '<script defer src="../../assets/stage1-parks.js?v=20261114b"></script>')
        page = page.replace("</head>", head + "\n</head>")
        page = re.sub(r'(<script defer src="../catalog/catalog.js\?v=)[^"\s]+', r'\g<1>20261114-stage1', page)
        page = re.sub(r'(<p id="intro">).*?(</p>)', lambda m: m[1] + esc(park["intro"]) + m[2], page, count=1, flags=re.S)
        anchor = '  <p id="load-error"'
        if anchor not in page:
            raise ValueError("Missing insertion anchor")
        page = page.replace(anchor, before_map(data, park, info["center"], places["parks"].get(park["id"], [])) + "\n" + anchor, 1)
        # Replace auto-generated name-only category sections, leaving nearby parks intact.
        page = re.sub(r'<section class="park-sec"><h2>(?:Достопримечательности|Музеи и театры|Смотровые площадки|Скульптуры|Кафе и рестораны)</h2>.*?</section>\n?', "", page, flags=re.S)
        footer = "  <footer>Карта, дорожки и объекты"
        if footer not in page:
            raise ValueError("Missing source footer")
        page = page.replace(footer, reference(data, park, places["parks"].get(park["id"], []), places["date"], source_park) + "\n" + footer, 1)
        path.write_text(page, encoding="utf-8", newline="\n")
        print(f"Stage-one park: {slug}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", action="append", choices=["park-otradnoe", "petrovskiy-park"])
    build(parser.parse_args().slug)
