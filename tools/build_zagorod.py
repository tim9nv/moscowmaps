"""Раздел «За город»: куда поехать из Москвы на день или выходные.
Запуск: python3 tools/build_zagorod.py -> zagorod/index.html, zagorod/<slug>/index.html, пункт «За город» в верхнем меню всех страниц, sitemap.xml.
Тексты свои; факты (часы, цены, дорога) — с официальных сайтов и справочников, у каждого места список источников и дата проверки.
Координаты точек — OpenStreetMap (Nominatim), ноябрь 2026. После сборки запустить tools/night_theme.py не нужно: страницы на стилях парков.
"""
import os, re, glob, html, datetime
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://www.mskatlas.ru'
V = '20261111z'
CHECKED = '11 ноября 2026'
E = lambda s: html.escape(str(s), quote=True)
METRIKA = open(f'{REPO}/tools/metrika.html', encoding='utf-8').read().strip()

PLACES = [
 dict(slug='sergiev-posad', name='Сергиев Посад', kind='на день', km='около 75 км',
  lead='Троице-Сергиева лавра — главный монастырь Подмосковья и самый простой выезд на день: электричка идёт полтора часа, от станции до стен Лавры пешком 15 минут.',
  title='Сергиев Посад за один день: как добраться из Москвы и что посмотреть в Лавре',
  get=[('Электричка', 'С Ярославского вокзала (метро «Комсомольская») до станции «Сергиев Посад» — подходят поезда на Сергиев Посад, Александров и Балакирево. Сесть можно и на станции Ростокино (МЦК). Обычная электричка идёт около полутора часов, билет около 200 ₽; несколько раз в день ходит экспресс — около часа, дороже.'),
       ('Автобус', '№ 388 от метро «ВДНХ» (улица Космонавтов, 2А, у гостиницы «Космос»), примерно каждые 20–25 минут.'),
       ('От станции до Лавры', 'Около 1 км пешком по Сергиевской улице. По пути — смотровая площадка на Блинной горе, откуда Лавра видна целиком; дальше подземный переход прямо к монастырю.')],
  plan=[('Утро', 'Блинная гора', 'Первый вид на Лавру — лучшая точка для фотографии, особенно в солнечный день.'),
        ('', 'Троице-Сергиева лавра', 'Действующий мужской монастырь, основан Сергием Радонежским в XIV веке. Внутри стен — Троицкий собор с мощами преподобного Сергия, Успенский собор, высокая колокольня. Это действующий монастырь: одевайтесь как для храма.'),
        ('День', 'Экскурсия или музей', 'Обзорная экскурсия Лавры — 3000 ₽ за группу до 6 человек или 500 ₽ взрослый, 300 ₽ детский. Церковно-археологический кабинет при Духовной академии, крупнейший церковный музей, — 400 ₽ взрослый, 200 ₽ детский.'),
        ('Обед', 'Кафе у Лавры', '«Келарский дворик» — ежедневно 8:00–20:00, горячее и выпечка. Ресторан-музей «Гостевая изба» — ежедневно 10:00–23:00, русская кухня. «Маковец» — пн–чт 8:00–20:00, пт–вс 8:00–21:00.'),
        ('После обеда', 'Белый пруд и город', 'Пруд у северной стены Лавры и купеческие улицы вокруг; обратно на станцию той же дорогой через Блинную гору.')],
  tips=['Паломнический центр Лавры (проспект Красной Армии, 131) работает с 8:30 до 17:00 с ноября по апрель и с 8:00 до 18:00 с апреля по ноябрь: там записывают на экскурсии.',
        'Часы открытия ворот на сайте Лавры отдельно не указаны — перед поездкой в праздник лучше позвонить в паломнический центр: +7 (496) 540-57-21.',
        'При Лавре есть гостиницы — можно остаться на ночь и утром попасть на службу.'],
  points=[('Станция Сергиев Посад', 56.30436, 38.13661, 'Сюда приходят электрички с Ярославского вокзала.', '', 'Ст'),
          ('Блинная гора', 56.30734, 38.135, 'Смотровая площадка с видом на Лавру.', '', '1'),
          ('Троице-Сергиева лавра', 56.31069, 38.13021, 'Монастырь, экскурсии, музей и кафе рядом.', '', '2–4'),
          ('Белый пруд', 56.31296, 38.13389, 'Пруд у стен Лавры.', '', '5')],
  sources=[('Официальный сайт Лавры: как добраться', 'https://www.stsl.ru/welcome/all/kak-dobratsya'),
           ('Сайт Лавры: экскурсии и цены', 'https://www.stsl.ru/excursions/'),
           ('Сайт Лавры: музеи', 'https://www.stsl.ru/excursions/ekskursii-po-muzeyam/'),
           ('Расписание электричек', 'https://rasp.yandex.ru/')]),
 dict(slug='kolomna', name='Коломна', kind='на день или с ночёвкой', km='около 100 км',
  lead='Старый город с кремлём XVI века, калачами и пастилой. Самое интересное собрано на нескольких улицах — за день можно обойти пешком, а с ночёвкой — без спешки.',
  title='Коломна за один день: как добраться из Москвы, кремль, пастила и калачи',
  get=[('Поезд', 'С Казанского вокзала. Выходите на станции «Коломна», а не на конечной «Голутвин»: «Коломна» ближе к Старому городу. Самые быстрые поезда идут около 1 ч 25 мин, обычная электричка — 2–2,5 часа.'),
       ('Автобус', 'От метро «Котельники» до автовокзала «Коломна» — около 1 ч 35 мин.'),
       ('От станции', 'До музеев пастилы — около 15 минут пешком, до кремля — около получаса.')],
  plan=[('Утро', 'Музей «Коломенская пастила»', 'Музей с дегустацией: пастилу здесь делают по старым рецептам. В Старом городе два музея пастилы метрах в трёхстах друг от друга — оба с экскурсиями.'),
        ('', 'Пятницкие ворота и «Калачная»', 'Главный въезд в кремль. Рядом музей-пекарня «Калачная» — можно попробовать горячий калач и купить хлеб домой; открыта ежедневно с 10:00 до 18:00.'),
        ('День', 'Коломенский кремль', 'Крепость XVI века: из шестнадцати башен до наших дней дошли семь. Внутри — Соборная площадь с храмами и колокольней.'),
        ('', 'Маринкина башня', 'Угловая башня кремля, по легенде здесь держали Марину Мнишек.'),
        ('После обеда', 'Ново-Голутвин монастырь', 'Женский монастырь внутри кремлёвских стен, с садом и прогулочными дорожками.')],
  tips=['Театрализованные программы в «Калачной» и музеях пастилы платные и идут по расписанию — время сеансов смотрите на их страницах.'],
  points=[('Станция Коломна', 55.09957, 38.77964, 'Выходить здесь, а не на «Голутвине».', '', 'Ст'),
          ('Музей «Коломенская пастила»', 55.10467, 38.76993, 'Посадская улица.', '', '1'),
          ('Пятницкие ворота и «Калачная»', 55.1058, 38.7633, 'Въезд в кремль, рядом музей-пекарня.', '', '2'),
          ('Ново-Голутвин монастырь', 55.10486, 38.75794, 'Внутри кремля.', '', '5'),
          ('Маринкина башня', 55.10446, 38.75101, 'Угловая башня кремля.', '', '4')],
  sources=[('Яндекс Расписания: поезда Москва — Коломна', 'https://rasp.yandex.ru/train/moscow--kolomna'),
           ('Т—Ж: Коломна за один день', 'https://t-j.ru/kolomna-one-day/'),
           ('Тонкости туризма: музей «Калачная»', 'https://tonkosti.ru/Музей_«Калачная»'),
           ('Российская газета: что посмотреть в Коломне', 'https://rg.ru/2023/08/30/reg-cfo/chto-posmotret-v-kolomne-za-odin-den.html')]),
 dict(slug='arhangelskoe', name='Архангельское', kind='на полдня', km='5 км от МКАД',
  lead='Усадьба князей Юсуповых сразу за МКАД: дворец с коллекцией живописи, парк террасами к Москве-реке и храм-усыпальница «Колоннада». Хватит половины дня.',
  title='Усадьба Архангельское: как добраться, режим работы и что посмотреть',
  get=[('Метро и автобус', 'До метро «Тушинская» или «Строгино», оттуда автобусом около получаса. Номера маршрутов в Подмосковье в последние годы меняли — проверьте актуальный в приложении с транспортом перед выездом.'),
       ('На машине', 'По Волоколамскому или Новорижскому шоссе до поворота на Ильинское шоссе.')],
  plan=[('', 'Большой дворец', 'Главный дом усадьбы. Юсуповы владели Архангельским с начала XIX века до 1917 года; князь Николай Юсупов собрал здесь картины европейских мастеров. Музеем усадьба стала в 1919 году.'),
        ('', 'Парк и террасы', 'Регулярный парк спускается террасами со скульптурами к Москве-реке — главная прогулка усадьбы.'),
        ('', 'Церковь Михаила Архангела', 'Самая старая постройка усадьбы, XVII век, над обрывом к реке.'),
        ('', 'Храм-усыпальница «Колоннада»', 'Построена после гибели на дуэли сына владельцев, Николая Юсупова.')],
  tips=['Зимний режим (с 12 октября): парк открыт ежедневно с 10:00 до 20:00, вход и кассы — до 19:00.',
        'Онлайн-продажа билетов на сайте музея сейчас недоступна, цены там не указаны — уточняйте в кассе или по телефону +7 (498) 653-86-60.'],
  points=[('Большой дворец и парк', 55.78858, 37.28593, 'Главный дом усадьбы, от него террасы к реке.', '', '1–2'),
          ('Храм-усыпальница «Колоннада»', 55.78463, 37.28918, 'К юго-востоку от дворца.', '', '4'),
          ('Церковь Михаила Архангела', 55.78314, 37.29058, 'Над рекой.', '', '3')],
  sources=[('Официальный сайт музея-усадьбы', 'https://arhangelskoe.su/'),
           ('Т—Ж: поездка в Архангельское', 'https://t-j.ru/arkhangelskoe/'),
           ('Москвич Mag: дорога до Архангельского', 'https://moskvichmag.ru/?p=102730')]),
]


# Рисунки в шапках — в стиле парков (линия currentColor, жёлтое солнце), viewBox 320×210
def svg(body, sun):
    return ('<svg class="hero-art" viewBox="0 0 320 210" aria-hidden="true" fill="none">'
            f'<circle cx="{sun[0]}" cy="{sun[1]}" r="{sun[2]}" fill="#e6bc71"/>' + body + '</svg>')
merl = ''.join(f'M{x + 4} 135v-8h9v8' for x in range(10, 300, 20))   # зубцы кремлёвской стены
S3 = 'stroke="currentColor" stroke-width="3" stroke-linejoin="round"'
S2 = 'stroke="currentColor" stroke-width="2" stroke-linejoin="round"'
ART = {
 'sergiev-posad': svg(f'<path d="M0 180h320M20 180v-40h280v40M20 140v-18h20v18m240 0v-18h20v18M17 122l13-15 13 15m234 0 13-15 13 15M110 140V95h80v45m-48 0v-14a8 8 0 0 1 16 0v14M140 95V78h20v17m-20-17c0-10 10-14 10-23 0 9 10 13 10 23m-10-23v-9m-4 4h8M116 95V84h12v11m-12-11c0-6 6-8 6-13 0 5 6 7 6 13m44 11V84h12v11m-12-11c0-6 6-8 6-13 0 5 6 7 6 13M228 140v-35h24v35m-21-35V80h18v25m-15-25V62h12v18m-10-18V50h8v12m-8-12c0-6 4-8 4-12 0 4 4 6 4 12m-4-12v-9" {S3}/>', (70, 50, 30)),
 'kolomna': svg(f'<path d="M0 185h320M10 185v-50h300v50{merl}M40 185V100h40v85M36 100h48L60 60zm24-40V48M210 185V95h50v90m-38 0v-26a13 13 0 0 1 26 0v26M206 95h58l-29-38zm29-38V45M120 135v-30h40v30m-30-30c0-12 10-14 10-24 0 10 10 12 10 24m-10-24V70m-4 4h8" {S3}/>', (285, 42, 28)),
 'arhangelskoe': svg(f'<path d="M0 190h320M30 176h260M50 162h220M70 162v-57h180v57m-120 0v-50m15 50v-50m15 50v-50m15 50v-50m15 50v-50m-68 0h76l-38-20zm18-20V72h40v20m-40-20a20 14 0 0 1 40 0m-20-14V48M84 122h22m-22 20h22m108-20h22m-22 20h22" {S3}/><path d="M22 176v-30m278 30v-30" {S2}/><circle cx="22" cy="134" r="13" {S2}/><circle cx="300" cy="134" r="13" {S2}/>', (268, 44, 26)),
 'hub': svg(f'<path d="M0 160c60-26 120-26 170-6s110 15 150 0M120 210l32-52m58 52-30-52m-20 47v-9m0-14v-7m0-12v-4M60 140v-20h18v20m-16-20c0-8 7-9 7-15 0 6 7 7 7 15m-7-15v-8" {S3}/><path d="M250 152v-22m-8 10 8-18 8 18m17 15v-26m-9 12 9-20 9 20M110 52q6-6 12 0 6-6 12 0m14 14q5-5 10 0 5-5 10 0" {S2}/>', (240, 55, 32)),
}

MORE = {'sergiev-posad': {'hist': ['В 1337 году Варфоломей — будущий преподобный Сергий Радонежский — с братом Стефаном поселился на холме Маковец и срубил деревянную церковь Троицы. Вокруг обители вырос крупнейший монастырь Руси.', 'Слободы у стен монастыря в 1782 году по указу Екатерины II объединили в Сергиев посад, а к 1792 году он получил регулярный план — отсюда прямые улицы старого центра.', 'В 1919 году город назвали Сергиевым, в 1930-м — Загорском, а в 1991-м вернули прежнее имя. С 1993 года ансамбль Лавры — в списке Всемирного наследия ЮНЕСКО.'], 'extra': [('Музей игрушки', 'Собрание, начатое в Москве Николаем Бартрамом; в 1931 году музей переехал в Загорск. Сергиев Посад — столица русской матрёшки.'), ('Абрамцево', 'Усадьба Саввы Мамонтова по дороге из Москвы — именно в её мастерских в конце XIX века появилась первая русская матрёшка. Удобнее на машине.')], 'food': [('Русский дворик', 'Ресторан', 'просп. Красной Армии, 134/2', 'https://yandex.ru/maps/org/russkiy_dvorik/1018960453/'), ('Гостевая изба', 'Ресторан-музей русской кухни', 'просп. Красной Армии, 133А', 'https://yandex.ru/maps/org/gostevaya_izba/1135378238/'), ('Сергиевская кухмистерская', 'Кафе-музей', 'ул. Карла Маркса, 7, корп. 16', 'https://yandex.ru/maps/org/sergiyevskaya_kukhmisterskaya/158408549823/'), ('Мануфактура 1858', 'Ресторан', 'ул. Карла Маркса, 7А', 'https://yandex.ru/maps/org/manufaktura_1858/27851712935/'), ('Вареничная № 9', 'Кафе-столовая, недорого', 'ул. Карла Маркса, 7', 'https://yandex.ru/maps/org/varenichnaya_9/71758346433/'), ('Хлебник', 'Пекарня', 'просп. Красной Армии, 142', 'https://yandex.ru/maps/org/khlebnik/8284951612/')], 'hsrc': [('Вокруг света: Сергиев Посад за день', 'https://www.vokrugsveta.ru/articles/vse-glavnoe-za-1-den-progulka-po-sergievu-posadu-i-troice-sergievoi-lavre-id892421/'), ('МТС Медиа: Сергиев Посад за один день', 'https://media.mts.ru/society/209716-sergiev-posad-chto-posmotret')]}, 'kolomna': {'hist': ['Впервые Коломна упомянута в Лаврентьевской летописи под 1177 годом — как пограничная крепость Рязанского княжества. В начале XIV века её присоединили к Москве.', 'Каменный кремль из красного кирпича построили в 1525–1531 годах по приказу Василия III. Стены поднимались до 21 метра и тянулись почти на два километра; сегодня от них осталось два участка и семь башен из шестнадцати.', 'В XIX веке город славился пастилой и калачами. Оба промысла возродили местные музеи — с ними Коломна и стала популярной поездкой на выходные.'], 'extra': [('Краеведческий музей', 'Улица Лажечникова, 15 — история города от древних стоянок до XX века.'), ('Музей «Сие деньги коломьски»', 'Небольшой музей монет в Пятницкой башне кремля.'), ('Музей любимой игрушки', 'Игрушки советского детства — особенно нравится семьям с детьми.'), ('Зарайск', 'Если остаётесь на ночь: соседний город с ещё одним каменным кремлём.')], 'food': [('Дом с мезонином', 'Ресторан и кофейня', 'ул. Лажечникова, 4', 'https://yandex.ru/maps/org/dom_s_mezoninom/15372403424/'), ('Гербергъ 1-го нумера', 'Ресторан', 'ул. Лажечникова, 10', 'https://yandex.ru/maps/org/gerberg_1_go_numera/59204053227/'), ('Литературное кафе «Лажечников»', 'Кафе', 'ул. Лажечникова, 13', 'https://yandex.ru/maps/org/literaturnoye_kafe_lazhechnikov/100397037904/'), ('Марфа Соломоновна', 'Ресторан', 'ул. Пушкина, 2', 'https://yandex.ru/maps/org/marfa_solomonovna/53119875091/'), ('Трактир «Рыба»', 'Ресторан', 'Москворецкая ул., 7', 'https://yandex.ru/maps/org/traktir_ryba/45009957889/'), ('Рульки вверх', 'Ресторан', 'Красногвардейская ул., 3', 'https://yandex.ru/maps/org/rulki_vverkh/151130240437/')], 'hsrc': [('Rusmania: история Коломны', 'https://rusmania.com/central/moscow-region/kolomna/history/'), ('Т—Ж: Коломна за один день', 'https://t-j.ru/kolomna-one-day/')]}, 'arhangelskoe': {'hist': ['Каменная церковь Михаила Архангела, давшая имя усадьбе, построена в 1646 году, при князьях Одоевских. С 1703 по 1810 год имением владели Голицыны: при Н. А. Голицыне в 1780-х начали строить дворец и разбили регулярный парк.', 'В 1810 году усадьбу купил князь Николай Борисович Юсупов, один из крупнейших коллекционеров своего времени. При нём появились театр с декорациями Пьетро Гонзаго, павильон «Каприз», а во дворце — картины ван Дейка, Тьеполо, Буше и Юбера Робера.', 'Юсуповы владели Архангельским до революции; в начале XX века ансамбль завершил храм-усыпальница «Колоннада». 1 мая 1919 года в залы дворца вошли первые посетители музея.'], 'extra': [('Театр Гонзаго', 'Усадебный театр 1817–1818 годов с сохранившимися декорациями.'), ('Павильон «Каприз»', 'Малый дворец в парке, 1819 год.')], 'food': [('Дача № 7', 'Ресторан на территории музея-заповедника', 'территория музея, 7', 'https://yandex.ru/maps/org/dacha_7/73404892295/'), ('Ботаника', 'Ресторан на территории музея-заповедника', 'территория музея, 15', 'https://yandex.ru/maps/org/botanika/196493396659/'), ('Амбар № 13', 'Кафе', 'посёлок Архангельское, 157А', 'https://yandex.ru/maps/org/ambar_13/229325391972/'), ('Food to Go', 'Кофейня', 'посёлок Архангельское, 17В', 'https://yandex.ru/maps/org/food_to_go/216266902665/')], 'hsrc': [('БСЭ: Архангельское', 'https://booksite.ru/FullText/1/001/008/074/123.htm'), ('Сайт музея-заповедника (буклет)', 'https://arhangelskoe.su/upload/iblock/1ed/1ed4a67e0413753ba64f9bb1c96c403b.pdf')]}}

NAV = [('index.html', 'Районы'), ('housing.html', 'Цены'), ('ecology.html', 'Экология'), ('transport.html', 'Транспорт'), ('social.html', 'Школы и поликлиники'),
       ('parks.html', 'Парки и прогулки'), ('zagorod/', 'За город'), ('reyting/', 'Рейтинги'), ('new-moscow.html', 'Новая Москва'), ('climate.html', 'Климат и рельеф')]
def nav(pre, active):
    return '<nav class="tabs" aria-label="Разделы">' + ''.join(f'<a href="{pre}{h}"' + (' aria-current="page"' if h == active else '') + f'>{t}</a>' for h, t in NAV) + '</nav>'

def head(title, desc, url, pre):
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:site_name" content="Атлас Москвы"><meta property="og:locale" content="ru_RU">
<link rel="stylesheet" href="{pre}parks/vdnh/guide.css?v={V}">
<link rel="stylesheet" href="{pre}parks/catalog/catalog.css?v={V}">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<script defer src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<style>
.zg-grid{{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}}
.zg-card{{display:block;background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px 18px;color:var(--ink);text-decoration:none;transition:transform .15s cubic-bezier(.23,1,.32,1),border-color .15s ease}}
@media (hover:hover){{.zg-card:hover{{transform:translateY(-2px);border-color:#FFD86B}}}}
.zg-card h3{{margin:0 0 4px;font-size:20px}}.zg-card .meta{{color:var(--muted);font-size:14px;margin:0 0 8px}}.zg-card p{{margin:0;line-height:1.5}}
.zg-facts{{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 0;padding:0;list-style:none}}.zg-facts li{{background:rgba(255,255,255,.1);border-radius:999px;padding:5px 12px;font-size:14px}}
.zg-sec{{margin-top:36px}}.zg-sec h2{{margin:0 0 12px}}
.zg-get dt{{font-weight:700;margin-top:12px}}.zg-get dd{{margin:4px 0 0;line-height:1.55;max-width:72ch}}
.zg-plan{{list-style:none;padding:0;margin:0;counter-reset:s}}.zg-plan li{{counter-increment:s;display:grid;grid-template-columns:34px 1fr;gap:12px;padding:12px 0;border-bottom:1px solid var(--border)}}
.zg-plan li::before{{content:counter(s);width:28px;height:28px;border-radius:50%;background:#22614c;color:#fff;display:grid;place-items:center;font-weight:700;font-size:14px;border:2px solid #fff;box-sizing:border-box}}
.zg-plan b{{display:block}}.zg-plan .when{{color:#FFD86B;font-size:13px;font-weight:600;text-transform:none}}.zg-plan p{{margin:4px 0 0;line-height:1.55;max-width:72ch}}
.zg-p{{line-height:1.6;max-width:72ch;margin:0 0 10px}}.zg-note{{color:var(--muted);font-size:14px;margin:-4px 0 12px}}.zg-food .zg-card h3{{font-size:18px}}.zg-go{{color:#FFD86B;font-size:14px;margin-top:8px!important}}.zg-tips li{{margin:6px 0;line-height:1.55;max-width:72ch}}
#zgmap .route-pin{{--pin:#22614c;font-size:12px}}#zgmap .route-pin.st{{--pin:#4d5a5a}}#zgmap{{height:clamp(320px,52vh,520px);border-radius:14px;border:1px solid var(--border);background:#dce8da}}
.zg-src{{font-size:14px;color:var(--muted)}}.zg-src a{{color:var(--muted)}}
</style>
</head>
<body>
<header class="topbar"><div class="in"><a class="brand" href="{pre}index.html" aria-label="Атлас Москвы, на главную"><i aria-hidden="true"></i>Атлас Москвы</a>{nav(pre, 'zagorod/')}</div></header><script>(function(){{var t=document.querySelector(".topbar .tabs"),a=t&&t.querySelector("[aria-current]");if(a&&t.scrollWidth>t.clientWidth)t.scrollLeft=a.offsetLeft-(t.clientWidth-a.offsetWidth)/2}})()</script>
'''

def map_js(points, numbered):
    pts = ','.join('[%s,%s,%s,%s,%s,%s]' % (q[1], q[2], js(q[0]), js(q[3]), js(q[4] if len(q) > 4 else ''), js(q[5] if len(q) > 5 else '')) for q in points)
    num = 'p[5]||String(i+1)' if numbered else '"★"'
    return f'''<script>addEventListener("load",function(){{if(!window.L)return;var P=[{pts}];var m=L.map("zgmap",{{scrollWheelZoom:false,zoomSnap:0.25}});m.attributionControl.setPrefix(false);
L.tileLayer("https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",{{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}}).addTo(m);
var b=[];P.forEach(function(p,i){{var ic=L.divIcon({{className:"poi-icon route-pin",html:{num},iconSize:[p[5]&&p[5].length>2?40:29,29]}});var d=document.createElement("div"),h=document.createElement("strong"),t=document.createElement("p");h.textContent=p[2];t.textContent=p[3];d.append(h,t);if(p[4]){{var a=document.createElement("a");a.href=p[4];a.textContent="Подробнее →";d.append(a)}}L.marker([p[0],p[1]],{{icon:ic,title:p[2]}}).addTo(m).bindPopup(d);b.push([p[0],p[1]])}});
m.fitBounds(b,{{padding:[40,40],maxZoom:16}})}})</script>'''
def js(s): return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'

def place_page(p):
    url = f'{BASE}/zagorod/{p["slug"]}/'
    desc = p['lead'][:160]
    out = head(p['title'], desc, url, '../../')
    out += f'''<main class="wrap">
  <nav class="crumb" aria-label="Навигация"><a href="../">За город</a> / {E(p["name"])}</nav>
  <header class="hero has-art"><div class="hero-copy"><p class="eyebrow">За город · {E(p["kind"])}</p><h1>{E(p["name"])}</h1><p>{E(p["lead"])}</p>
  <ul class="zg-facts"><li>{E(p["km"])}</li><li>{E(p["kind"])}</li></ul></div>{ART[p["slug"]]}</header>
  <section class="zg-sec"><h2>Как добраться</h2><dl class="zg-get">{''.join(f'<dt>{E(a)}</dt><dd>{E(b)}</dd>' for a, b in p['get'])}</dl></section>
  <section class="zg-sec"><h2>Маршрут на день</h2><div id="zgmap" aria-label="Карта маршрута"></div>
  <ol class="zg-plan">{''.join(f'<li><div>{f"<span class=when>{E(w)}</span>" if w else ""}<b>{E(n)}</b><p>{E(t)}</p></div></li>' for w, n, t in p['plan'])}</ol></section>
  <section class="zg-sec"><h2>Немного истории</h2>{''.join(f'<p class="zg-p">{E(t)}</p>' for t in MORE[p["slug"]]['hist'])}</section>
  <section class="zg-sec"><h2>Куда ещё зайти</h2><dl class="zg-get">{''.join(f'<dt>{E(a)}</dt><dd>{E(b)}</dd>' for a, b in MORE[p["slug"]]['extra'])}</dl></section>
  <section class="zg-sec"><h2>Где поесть</h2><p class="zg-note">Места с высокой оценкой и большим числом отзывов в Яндекс Картах (по состоянию на {CHECKED}). Свежий рейтинг, часы и меню — по ссылке.</p><div class="zg-grid zg-food">{''.join(f'<a class="zg-card" href="{E(u)}" target="_blank" rel="nofollow noopener"><h3>{E(n)}</h3><p class="meta">{E(t)} · {E(a)}</p><p class="zg-go">В Яндекс Картах →</p></a>' for n, t, a, u in MORE[p["slug"]]['food'])}</div></section>
  <section class="zg-sec"><h2>Что учесть</h2><ul class="zg-tips">{''.join(f'<li>{E(t)}</li>' for t in p['tips'])}</ul></section>
  <section class="zg-sec"><h2>Ещё за город</h2><div class="zg-grid">{''.join(card(q, '../') for q in PLACES if q is not p)}</div></section>
  <footer class="zg-src">Проверено {CHECKED}. Часы работы, цены и расписания меняются — перед поездкой загляните на сайт места. Источники: {' · '.join(f'<a href="{E(u)}" rel="nofollow noopener">{E(t)}</a>' for t, u in p['sources'] + MORE[p['slug']]['hsrc'])}. Карта — <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap</a>.</footer>
</main>
{map_js(p['points'], True)}
{METRIKA}
</body>
</html>
'''
    return out

HUBPT = {'sergiev-posad': (56.31069, 38.13021), 'kolomna': (55.1058, 38.7633), 'arhangelskoe': (55.78858, 37.28593)}
def card(p, pre):
    return f'<a class="zg-card" href="{pre}{p["slug"]}/"><h3>{E(p["name"])}</h3><p class="meta">{E(p["km"])} · {E(p["kind"])}</p><p>{E(p["lead"])}</p></a>'

def hub():
    title = 'За город: куда поехать из Москвы на день или выходные'
    desc = 'Места в пределах дня пути от Москвы: как добраться на электричке и машине, маршрут на день, где поесть. Сергиев Посад, Коломна, Архангельское.'
    out = head(title, desc, f'{BASE}/zagorod/', '../')
    out += f'''<main class="wrap">
  <header class="hero has-art"><div class="hero-copy"><p class="eyebrow">Атлас Москвы · выезд на день</p><h1>За город</h1><p>Куда съездить из Москвы на день или на выходные: как добраться, что посмотреть по порядку, где поесть. Раздел только начат — места будут добавляться.</p></div>{ART["hub"]}</header>
  <section class="zg-sec"><h2>На карте</h2><div id="zgmap" aria-label="Карта мест за городом"></div></section>
  <section class="zg-sec"><h2>Куда поехать</h2><div class="zg-grid">{''.join(card(p, '') for p in PLACES)}</div></section>
  <footer class="zg-src">Проверено {CHECKED}. У каждого места — источники фактов. Карта — <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap</a>.</footer>
</main>
{map_js([(p['name'], *HUBPT[p['slug']], p['km'] + ' · ' + p['kind'], p['slug'] + '/') for p in PLACES], False)}
{METRIKA}
</body>
</html>
'''
    return out

os.makedirs(f'{REPO}/zagorod', exist_ok=True)
open(f'{REPO}/zagorod/index.html', 'w', encoding='utf-8').write(hub())
for p in PLACES:
    os.makedirs(f'{REPO}/zagorod/{p["slug"]}', exist_ok=True)
    open(f'{REPO}/zagorod/{p["slug"]}/index.html', 'w', encoding='utf-8').write(place_page(p))

# пункт «За город» в меню всех страниц — после «Парки и прогулки» (идемпотентно)
n = 0
for f in glob.glob(f'{REPO}/**/*.html', recursive=True):
    if '/zagorod/' in f or '/node_modules/' in f: continue
    s = open(f, encoding='utf-8').read()
    m = re.search(r'<a href="([^"]*)parks\.html"( aria-current="page")?>Парки и прогулки</a>', s)
    if not m or 'zagorod/">За город</a>' in s: continue
    s = s[:m.end()] + f'<a href="{m.group(1)}zagorod/">За город</a>' + s[m.end():]
    open(f, 'w', encoding='utf-8').write(s); n += 1
# генератор страниц парков пишет меню сам — тоже добавить
g = f'{REPO}/tools/build_park_pages.py'; s = open(g, encoding='utf-8').read()
if 'zagorod/">За город' not in s:
    s = s.replace('Парки и прогулки</a><a href="../../reyting/">', 'Парки и прогулки</a><a href="../../zagorod/">За город</a><a href="../../reyting/">'); open(g, 'w', encoding='utf-8').write(s)
# sitemap
sm = open(f'{REPO}/sitemap.xml', encoding='utf-8').read()
sm = re.sub(r'  <url><loc>' + re.escape(BASE) + r'/zagorod/[^<]*</loc>.*?</url>\n', '', sm)
today = datetime.date.today().isoformat()
urls = [f'{BASE}/zagorod/'] + [f'{BASE}/zagorod/{p["slug"]}/' for p in PLACES]
sm = sm.replace('</urlset>', ''.join(f'  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n' for u in urls) + '</urlset>')
open(f'{REPO}/sitemap.xml', 'w', encoding='utf-8').write(sm)
print('страниц «За город»:', 1 + len(PLACES), '· меню добавлено на', n, 'страниц')
