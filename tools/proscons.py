# helper module: pros/cons and FAQ for a district
import json
def load_green(repo):
    s=open(f'{repo}/parks.html',encoding='utf-8').read()
    i=s.index('const DATA'); i+=s[i:].index('=')+1
    while s[i]==' ': i+=1
    d,_=json.JSONDecoder().raw_decode(s[i:])
    return {f['properties']['n']:f['properties'] for f in d['features']}

def fmt(v): return f'{float(v):.1f}'.replace('.', ',')
def num(v): return f'{round(v):,}'.replace(',', ' ')

def build(p, ranks, green, N):
    """ranks: dict with er, tr_r, tr_n, soc_r, soc_n, sp_r, sp_n, green_r, green_n"""
    n=p['n']; pros=[]; cons=[]
    g=green.get(n) or {}
    # price
    if p.get('hp'):
        k=round(p['hp']/1000)
        if p['hrk']>=95: pros.append(f'Недорогое по московским меркам жильё: около {k} тыс. ₽ за метр на вторичке ({p["hrk"]}-е место из 125 по цене).')
        elif p['hrk']<=25: cons.append(f'Дорогое жильё: около {k} тыс. ₽ за метр на вторичке, {p["hrk"]}-е место из 125 по цене.')
    # ecology
    er=ranks['er']
    src=[x[1] for x in (p.get('s') or [])][:3]
    if er<=30: pros.append(f'Чистый по московским меркам воздух: экологический балл {fmt(p["i"])} из 10, {er}-е место из {N} по чистоте.')
    elif er>=N-30: cons.append(f'Слабая экология: балл {fmt(p["i"])} из 10, {er}-е место из {N} по чистоте' + (f'; рядом {", ".join(src)}.' if src else '.'))
    elif src: cons.append(f'Рядом источники загрязнения: {", ".join(src)}.')
    # green
    if g.get('pct') is not None and ranks.get('green_n'):
        if ranks['green_r']<=30: pros.append(f'Много зелени: {g["pct"]} % территории занято деревьями и газонами' + (f', рядом {", ".join(g["parks"][:2])}' if g.get('parks') else '') + '.')
        elif ranks['green_r']>=ranks['green_n']-25: cons.append(f'Мало зелени: всего {g["pct"]} % территории.')
    # transport
    tr=p.get('tr')
    if tr:
        if tr['score']>=7.5: pros.append(f'Отличный транспорт: до центра около {tr["tmed"]} минут, до станции в среднем {tr["walk"]} минут пешком.')
        elif tr['score']<=3.5: cons.append(f'Далеко ехать: до центра около {tr["tmed"]} минут, до ближайшей станции в среднем {tr["walk"]} минут пешком.')
    # social
    if p.get('score') is not None:
        if p['score']>=7.5: pros.append(f'Школ, детских садов и поликлиник хватает: балл {fmt(p["score"])} из 10.')
        elif p['score']<4.5:
            weak=[]
            if p.get('edu') is not None and p['edu']<4.5: weak.append('школ и детских садов')
            if p.get('med') is not None and p['med']<4.5: weak.append('поликлиник')
            cons.append(f'Не хватает {" и ".join(weak) if weak else "соцобъектов"} на число жителей: балл {fmt(p["score"])} из 10.')
    # sport
    sp=p.get('sp')
    if sp and sp.get('s') is not None:
        if sp['s']>=7.5: pros.append(f'Много мест для спорта: бассейнов — {sp["pool"]}, спортзалов и клубов — {sp["halls"]}, площадок и воркаутов — {sp["grounds"]}.')
        elif sp['s']<3.5: cons.append('Для спорта мало мест: ' + ('бассейнов нет, ' if not sp['pool'] else '') + f'спортзалов и клубов — {sp["halls"]} на {num(p["pop"])} жителей.')
    # liveliness
    lv=p.get('lv')
    if lv:
        if lv['l']>=3: pros.append(f'Всё рядом: {num(lv["f"])} кафе и ресторанов, {num(lv["h"])} магазинов.')
        elif lv['l']==0: pros.append('Тихий спальный район: мало кафе и магазинов, спокойно по вечерам.')
    # climate
    c=p.get('cl')
    if c:
        if c['rel']>=25: pros.append(f'Район на возвышенности ({round(c["h"])} м): лучше продувается, реже туманы.')
        elif c['rel']<=-20: cons.append(f'Район в низине ({round(c["h"])} м): чаще туманы и сырость, в безветрие дольше держатся выбросы.')
    # FAQ
    faq=[]
    faq.append((f'Какая экология в районе {n}?', f'Экологический балл района {fmt(p["i"])} из 10 (чем меньше, тем чище), {er}-е место из {N} районов по чистоте.' + (f' Рядом с районом: {", ".join(src)}.' if src else ' Крупных источников загрязнения рядом нет.')))
    if p.get('hp'): faq.append((f'Сколько стоят квартиры в районе {n}?', f'Средняя цена метра на вторичке около {round(p["hp"]/1000)} тыс. ₽, это {p["hrk"]}-е место из 125 районов по цене. Двухкомнатная квартира 54 м² стоит примерно {fmt(p["hp"]*54/1e6)} млн ₽.'))
    if tr:
        st=[x[0] for x in tr['st']]
        faq.append((f'Какое метро в районе {n} и сколько ехать до центра?', (f'Станции в районе: {", ".join(st)}. ' if st else 'Внутри района нет станций метро, МЦК и МЦД. ') + f'До центра около {tr["tmed"]} минут, до ближайшей станции в среднем {tr["walk"]} минут пешком.'))
    if p.get('score') is not None: faq.append((f'Хватает ли в районе {n} школ и поликлиник?', f'Зданий школ в районе — {p["school"]}, детских садов — {p["kinder"]}, поликлиник и больниц — {p["clinic"]}. Балл обеспеченности {fmt(p["score"])} из 10, {ranks["soc_r"]}-е место из {ranks["soc_n"]}.'))
    if sp: faq.append((f'Где заниматься спортом в районе {n}?', f'Бассейнов в районе — {sp["pool"]}, спортзалов, клубов и катков — {sp["halls"]}, открытых площадок и воркаутов — {sp["grounds"]}. Балл спорта {fmt(sp["s"])} из 10.'))
    if g.get('pct') is not None: faq.append((f'Много ли зелени в районе {n}?', f'Деревья и газоны занимают {g["pct"]} % территории района' + (f', это около {num(g["pp"])} м² зелени на жителя' if g.get('pp') else '') + '.' + (f' Крупные зелёные зоны: {", ".join(g["parks"][:3])}.' if g.get('parks') else '')))
    return pros, cons, faq
