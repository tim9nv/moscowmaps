# Атлас районов Москвы — mskatlas.ru

Владелец — tim9nv. Отвечать по-русски, коротко и по делу.

С этим же репозиторием работает ChatGPT (Codex): для него инструкция в AGENTS.md (тот же текст — при правках обновляй оба). Перед работой читай CHANGELOG.md, после работы дописывай туда, что изменил и кто (Claude).

## Как устроен сайт

- Хостинг: Timeweb App Platform, приложение «Атлас Москвы» (ID 284367). Берёт ветку `main` этого репозитория и сам выкладывает каждый коммит на https://www.mskatlas.ru за 1–2 минуты. Дополнительно сайт открывается на GitHub Pages (tim9nv.github.io/moscowmaps).
- Всё статичное: HTML + d3, данные встроены в страницы.
- Разделы: `index.html` (главная, карта районов), `housing.html`, `ecology.html`, `climate.html` (География), `transport.html`, `social.html`, `parks.html`, `sport.html` (три вкладки «Городской среды»), `new-moscow.html`.
- `assets/atlas.js` — данные всех районов (`const DATA`) и код главной карты и подробной карты района. Его подключают главная и все страницы районов.
- `rayon/<slug>/` — 125 страниц районов, `rayon/` — список по округам. Генерируются.
- `reyting/` и `reyting/<slug>/` — 6 страниц-рейтингов под поисковые запросы. Генерируются.
- `rayon/gerb/` — гербы районов (часть подгружается с Викисклада, список в `tools/data/arms.json`).
- `sitemap.xml`, `robots.txt`, `ads.txt`, `yandex_*.html` — для Яндекса. Не удалять.

## Сборка (tools/)

После любого изменения данных районов в `assets/atlas.js`, `parks.html` (зелень) или `tools/data/sport_data.json`:

```
python3 tools/gen_pages.py   # страницы районов, рейтинги, sitemap.xml, robots.txt
python3 tools/ads.py         # рекламный блок РСЯ на все страницы (идемпотентно). Сейчас РСЯ отклонила сайт (меньше 100 посетителей в неделю), поэтому реклама снята: `python3 tools/ads.py --remove`. Вернуть — без флага, после одобрения.
```

Спорт и оживлённость (OpenStreetMap):
```
curl -o /tmp/moscow.osm.pbf https://download.openstreetmap.fr/extracts/russia/central_federal_district/moscow.osm.pbf
python3 tools/extract.py /tmp/moscow.osm.pbf   # -> tools/data/osm_points.json
python3 tools/assign.py                        # -> tools/data/sport_data.json
python3 tools/build_sport.py                   # sport.html из шаблона social.html
```
После этого — обновить `sp`/`lv` в DATA (см. историю коммитов) и снова `gen_pages.py` + `ads.py`.

- `tools/proscons.py` — правила «Плюсов и минусов» и «Частых вопросов» на страницах районов.
- `tools/metrika.html` — код Яндекс Метрики (счётчик 114123900), уже стоит на всех страницах.

## Реклама и аналитика

- РСЯ: 7.11.2026 отклонена — меньше 100 реальных посетителей в неделю; реклама снята с сайта. Повторно отправить на модерацию в интерфейсе РСЯ, когда трафик вырастет. Площадка 20355368, блок `R-A-20355368-1` — один на странице, после основного содержимого. Не ставить рекламу поверх карт, не включать авторасстановку, не менять код блока.
- Метрика: 114123900. Вебмастер: сайт https://www.mskatlas.ru подтверждён файлом `yandex_b0d109ca05fc58a6.html`.
- Доступ к Метрике, Вебмастеру, Вордстату и РСЯ — только через браузер владельца (Claude in Chrome). Агенты команды туда сами не ходят: главный Claude выгружает цифры и передаёт им.

## Правила для всех

- Ничего не выдумывать: каждое число — с источником и датой. Нет данных — так и писать.
- Перед публикацией — проверка `verstalshchik` (вид, телефон, тёмная тема, ошибки) и `proveryayushchiy` (данные совпадают с источниками и между страницами).
- Коммиты от имени tim9nv, сообщения по-русски, что изменилось для посетителя.
- Отчёты агентов показывать владельцу целиком.

## Команда (.claude/agents)

Данные: `ecolog`, `klimatolog`, `parkovod`, `sotsialshchik`, `rieltor` (цены), `transportnik`.
Сайт и рост: `seoshnik` (поиск), `redaktor` (тексты), `monetizator` (деньги), `razvitie` (новые идеи).
Контроль: `verstalshchik`, `proveryayushchiy`.

Регулярно:
- раз в неделю — `seoshnik` по свежим данным Вебмастера и Метрики;
- раз в месяц — `rieltor` (цены), `monetizator` (доход РСЯ), обновление спорта из OSM;
- раз в квартал — `ecolog`, `sotsialshchik`, `transportnik`, `parkovod`, `klimatolog`.
