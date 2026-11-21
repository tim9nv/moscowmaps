"""Apply editorial improvements to selected generated district pages.

Run LAST, after the normal build including seo_fix.py:
    python tools/stage1_districts.py
    python tools/stage1_districts.py --check

No importing gen_pages/life_block/district_layout: those modules write globally.
This postprocessor changes labels and explanations, not scores or formulas.
Unknown input fails closed; rerunning is byte-idempotent.
"""
import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOTS = {"otradnoe": "Отрадное", "aeroport": "Аэропорт"}
QUICK_LINKS = {"bogorodskoe": "Богородское", "orehovo-borisovo-severnoe": "Орехово-Борисово Северное"}
PILOTS.update(QUICK_LINKS)
QUIET = (
    "Расчётная оценка по расстоянию от домов до магистралей, крупных улиц и железнодорожных "
    "станций (без метро); это не замер шума."
)


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def embedded_data(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    start = text.index("=", text.index("const DATA")) + 1
    return json.JSONDecoder().raw_decode(text[start:].lstrip())[0]["features"]


def fmt(value):
    return f"{value:.1f}".replace(".", ",")


def replace_checked(text, old, new):
    if old in text:
        return text.replace(old, new)
    if new not in text:
        raise ValueError(f"Unrecognised page structure: {old[:90]}")
    return text


def section_note(text, heading, key, content, summary=None, visible=None):
    pattern = rf"<!--STAGE1-{key}-->.*?<!--STAGE1-{key}-END-->"
    text = re.sub(pattern, "", text, flags=re.S)
    start = text.index(f"<h2>{heading}</h2>")
    end = text.index("</section>", start)
    body = f'<p class="small" style="margin-top:10px">{content}</p>'
    if summary:
        body = (f'<details style="margin-top:10px"><summary style="cursor:pointer">{summary}</summary>'
                f'{body}</details>')
    if visible:
        body = f'<p class="small" style="margin-top:10px">{visible}</p>' + body
    note = f'<!--STAGE1-{key}-->{body}<!--STAGE1-{key}-END-->'
    return text[:end] + note + text[end:]


def zero_stat(count, per, per10):
    """Never turn unknown records into zero, or divide by unknown population."""
    if count is None:
        return "Нет данных", "Число объектов неизвестно; обеспеченность не рассчитана"
    if count == 0:
        return "Не найдены", "В используемой выгрузке OpenStreetMap; это не подтверждает отсутствие объектов"
    value = f"{count:,}".replace(",", " ")
    if per is None or per10 is None:
        return value, "Нет данных для расчёта на жителя"
    denominator = f"{per:,}".replace(",", " ")
    return value, f"1 на {denominator} чел. · {fmt(per10)} на 10 тыс."


def sync_faq(text):
    """Visible answers are the single source for FAQPage structured data."""
    faq = re.search(r'<section class="faq">.*?</section>', text, re.S).group(0)
    plain = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s))
    entries = [
        {"@type": "Question", "name": plain(q),
         "acceptedAnswer": {"@type": "Answer", "text": plain(a)}}
        for q, a in re.findall(r"<summary>(.*?)</summary><p>(.*?)</p>", faq, re.S)
    ]
    assert len(entries) == 6, "Unexpected FAQ shape"

    def rewrite(match):
        data = json.loads(match.group(1))
        if data.get("@type") != "FAQPage":
            return match.group(0)
        data["mainEntity"] = entries
        return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'

    return re.sub(r'<script type="application/ld\+json">(.*?)</script>', rewrite, text, flags=re.S)


def process(slug, name, text, p, age, houses, life):
    # Verify inputs against the current generated score data. Never repair silently.
    hp = houses["d"][slug]
    lp = life["d"][slug]["p"]
    quiet = max(0, min(10, 10 * (1 - (hp["n3"] + .5 * hp["n2"]) / hp["n"])))
    assert abs(lp["eco"] - (10 - p["i"])) < .00001
    assert abs(lp["quiet"] - quiet) < .00051
    ar = age["districts"][slug]
    assert sum(ar["bins"]) == ar["dated"] and 0 < ar["dated"] <= ar["all"]

    old_social = (f'Школ, детских садов и поликлиник хватает: балл {fmt(p["score"])} из 10.'
                  if slug == "aeroport" else
                  f'Не хватает поликлиник на число жителей: балл {fmt(p["score"])} из 10.')
    new_social = (f'Оценка по числу школ, детских садов, поликлиник и больниц в используемых данных — '
                  f'{fmt(p["score"])} из 10. Она не показывает наличие свободных мест, очереди или качество услуг.'
                  if slug == "aeroport" else
                  f'Оценка раздела «Школы и поликлиники» — {fmt(p["score"])} из 10. '
                  'По этим данным нельзя определить наличие свободных мест или очереди.')
    text = replace_checked(text, old_social, new_social)
    text = replace_checked(text, "Экологический балл района", "Индекс загрязнения района")
    text = replace_checked(text, "Экологический балл", "Индекс загрязнения")
    text = replace_checked(text, "Экология · 10 грязно", "Индекс загрязнения · 10 — хуже")
    text = replace_checked(text, "Итоговый балл", "Индекс загрязнения")
    text = replace_checked(text, '<span>Экология</span>', '<span>Экологическое благополучие</span>')
    text = replace_checked(text, "Каждый показатель — от 0 до 10, справа его вес",
                           "Каждый показатель — от 0 до 10, больше — лучше; справа его вес")
    text = replace_checked(text, "по средней цене метра на вторичке", "по медианной цене метра на вторичке")
    text = replace_checked(text, "Средняя цена метра на вторичке", "Медианная цена метра на вторичке")
    text = replace_checked(text, "население — Росстат и Wikidata 2025",
        'население — <a href="https://www.real-stats.ru/data/export/msk/population.json">'
        'real-stats.ru: Википедия (сводные таблицы), период 2025</a>')
    # Compact explanation immediately below the quiet row, not hidden in a tooltip.
    text = re.sub(r'<!--STAGE1-QUIET-->.*?<!--STAGE1-QUIET-END-->', "", text, flags=re.S)
    row = re.search(r'<li><span>Тишина</span>.*?</li>', text, re.S)
    assert row
    text = text[:row.end()] + (
        '<!--STAGE1-QUIET--><li style="display:block;font-size:13px;color:var(--muted)">'
        + QUIET + '</li><!--STAGE1-QUIET-END-->') + text[row.end():]

    share = round(max(ar["bins"]) / ar["dated"] * 100)
    old = round(sum(ar["bins"][:3]) / ar["dated"] * 100)
    text = replace_checked(text,
        f'{share} % жилых домов района · построено до 1981 года — {old} %',
        f'{share} % домов с известным годом · среди них построено до 1981 года — {old} %')
    text = re.sub(r'<p class="small house-age-src">.*?</p>',
        '<p class="small house-age-src">'
        f'Год постройки известен для {ar["dated"]} из {ar["all"]} жилых домов в OpenStreetMap '
        f'(дата подготовки данных: {age["date"]}). Доли возрастных групп рассчитаны только по '
        f'{ar["dated"]} домам с известным годом; остальные {ar["all"] - ar["dated"]} не распределены по периодам. '
        '<a href="../../tools/data/house_age.json">Данные о возрасте домов</a>.</p>', text, flags=re.S)

    # Keep count and rate values, correct the meaning and provenance of their labels.
    text = replace_checked(text, "Балл обеспеченности", "Оценка по числу объектов на жителя")
    social_faq = re.search(r'(<summary>Хватает ли.*?</summary><p>)(.*?)(</p>)', text, re.S)
    assert social_faq
    answer = social_faq.group(2).split(" По этим данным")[0]
    answer += " По этим данным нельзя определить свободные места, очереди или качество услуг; реестр может быть неполным."
    text = text[:social_faq.start(2)] + answer + text[social_faq.end(2):]
    text = section_note(text, "Школы, детские сады и поликлиники", "SOCIAL",
        'Источник количеств: <a href="https://www.real-stats.ru/data/">real-stats.ru</a> '
        '(OpenStreetMap 2026). Население — '
        '<a href="https://www.real-stats.ru/data/export/msk/population.json">real-stats.ru: Википедия (сводные таблицы)</a>; '
        'период наблюдения — 2025 год, дата обновления источника — 29 июня 2026 года. '
        'Дата выгрузки населения для Атласа не зафиксирована. '
        '«На 10 тыс.» — число объектов / население × 10 000; «1 на N» — население / число объектов. '
        'Оценка объединяет образование (школы и сады) и здравоохранение (поликлиники и больницы); '
        '<a href="../../social.html">описание методики</a>.',
        summary="Источники и расчёт показателей",
        visible="Реестр объектов может быть неполным; число зданий не показывает вместимость, свободные места или очереди.")
    if p["sp"]["pool"] == 0:
        value, note = zero_stat(0, p["sp"]["pp"], p["sp"]["p10"])
        text = replace_checked(text,
            '<div class="l">Бассейны</div><div class="v">нет</div><div class="s">в районе таких объектов нет</div>',
            f'<div class="l">Бассейны</div><div class="v">{value}</div><div class="s">{note}</div>')
        text = replace_checked(text, "Бассейнов в районе нет,", "В используемой выгрузке OpenStreetMap бассейны не найдены; это не подтверждает их отсутствие в районе. Число")
    text = section_note(text, "Спорт и жизнь вокруг", "SPORT",
        'Источник спортивных объектов: OpenStreetMap, выгрузка 7 ноября 2026 года '
        '(<a href="../../sport.html">источник и методика</a>). Реестр может быть неполным. '
        '«На 10 тыс.» — число объектов / население × 10 000; «1 на N» — население / число объектов. '
        'Плотность кафе и магазинов — их суммарное число / площадь района; '
        'население и площадь взяты из данных real-stats.ru. Ноль найденных объектов не означает их отсутствия.',
        summary="Источники и расчёт показателей",
        visible="Числа относятся к объектам в используемой выгрузке; реестр может быть неполным.")
    text = section_note(text, "Экология района " + name, "ECO",
        'Экологическое благополучие в балле для жизни = 10 минус индекс загрязнения. '
        'Это два представления одних данных, а не независимые оценки. '
        'У индекса загрязнения меньше — чище; у экологического благополучия больше — лучше. '
        '<a href="../../ecology.html">Источники и методика экологии</a>.')
    text = section_note(text, "Жильё и транспорт", "HOUSE",
        'Стоимость квартиры 54 м² — медианная цена метра × 54, а не оценка конкретной квартиры. '
        'Источник и месяц цен указаны выше; <a href="../../housing.html">методика цен</a>.',
        summary="Как рассчитана стоимость квартиры")
    if slug in QUICK_LINKS:
        text = text.replace("Для спорта мало мест: бассейнов нет,", "В выгрузке OpenStreetMap бассейны не отмечены,")
        park_tip = (
            'Для прогулки по готовому маршруту откройте <a href="../../parks/natsionalnyy-park-losinyy-ostrov/#walks">«Лабиринт и Босоногая тропа» в Лосином Острове</a>. '
            'Если выбираете прогулку с видом, на <a href="../../parks/yauzskiy-lesopark/#map-section">карте Яузского лесопарка</a> отмечены смотровые площадки.'
            if slug == "bogorodskoe" else
            'Для прогулки от Фигурного моста через дворцы откройте <a href="../../parks/muzey-zapovednik-tsaritsyno/#walks">маршрут по «Царицыну»</a>. '
            'Для прогулки у воды с детьми на <a href="../../parks/borisovskie-prudy/#map-section">карте Борисовских прудов</a> отмечены детские площадки и туалеты.'
        )
        heading = f'<h2>Парки района {name}</h2>'
        text = re.sub(r'<!--PARK-CHOICE-->.*?<!--PARK-CHOICE-END-->', '', text, flags=re.S)
        text = text.replace(heading, heading + '<!--PARK-CHOICE--><p>' + park_tip + '</p><!--PARK-CHOICE-END-->')
        text = district_navigation(text, name)
    return sync_faq(text)


def district_navigation(text, name):
    sections = (
        ("homes-map", None, "Карта домов"),
        ("housing", "Жильё и транспорт", "Цены и метро"),
        ("schools", "Школы, детские сады и поликлиники", "Школы и поликлиники"),
        ("parks", "Парки района " + name, "Парки"),
        ("ecology", "Экология района " + name, "Экология"),
    )
    links = []
    for anchor, heading, label in sections:
        pattern = (r'<section(?=[^>]*class="map")[^>]*>' if heading is None
                   else r'<section[^>]*>(?=<h2>' + re.escape(heading) + r'</h2>)')
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Missing district section: {anchor}")
        tag = match.group()
        if f'id="{anchor}"' not in tag:
            text = text[:match.start()] + tag[:-1] + f' id="{anchor}">' + text[match.end():]
        links.append(f'<a href="#{anchor}">{label}</a>')
    text = re.sub(r'<!--DISTRICT-NAV-->.*?<!--DISTRICT-NAV-END-->', '', text, flags=re.S)
    nav = ('<!--DISTRICT-NAV--><style>.district-nav{display:flex;flex-wrap:wrap;gap:0 1em;margin:.5em 0}'
           '.district-nav a{display:inline-flex;align-items:center;min-height:44px}'
           'main section[id]{scroll-margin-top:4.5rem}</style>'
           '<nav class="district-nav" aria-label="На странице района">' + ''.join(links) + '</nav><!--DISTRICT-NAV-END-->')
    return replace_checked(text, '</header><!--LIFE-SCORE-->', '</header>' + nav + '<!--LIFE-SCORE-->')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if either pilot requires rebuilding")
    args = parser.parse_args()
    props = {f["properties"]["n"]: f["properties"] for f in embedded_data("assets/atlas.js")}
    age, houses, life = [load_json(f"tools/data/{n}.json") for n in ("house_age", "houses", "life_parts")]
    pending = []
    for slug, name in PILOTS.items():
        path = ROOT / "rayon" / slug / "index.html"
        before = path.read_text(encoding="utf-8")
        after = process(slug, name, before, props[name], age, houses, life)
        assert process(slug, name, after, props[name], age, houses, life) == after, "Not idempotent"
        if before != after:
            pending.append((path, after))
    if args.check and pending:
        raise SystemExit("Rebuild needed: " + ", ".join(str(p.relative_to(ROOT)) for p, _ in pending))
    for path, text in pending:
        path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Stage 1 districts: {len(pending)} changed; only {', '.join(PILOTS)}")


if __name__ == "__main__":
    main()
