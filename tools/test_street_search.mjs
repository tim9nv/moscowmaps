import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const root = new URL('../', import.meta.url);
const source = await readFile(new URL('assets/street-search.js', root), 'utf8');
const {normalize, findStreets, splitAddress, findAddress, addresses} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const data = JSON.parse(await readFile(new URL('assets/streets.json', root), 'utf8'));
assert.equal(normalize('ул. Сущёвский Вал'), normalize('Сущевский Вал'));
assert.equal(normalize('пр-т Мира'), normalize('проспект Мира'));
assert.equal(findStreets(data.streets, 'пр-т Мира')[0][0], 'проспект Мира');
assert.ok(!findStreets(data.streets, 'пр-т Мира').some(r => r[0] === 'аллея Мира'));
assert.equal(normalize('Ленинский пр-кт'), normalize('проспект Ленинский'));
assert.equal(normalize('1-я Тверская-Ямская ул.'), normalize('1 Тверская Ямская'));
const search = q => findStreets(data.streets, q);
assert.equal(search('ул. Декабристов')[0][0], 'улица Декабристов');
assert.deepEqual(search('Декабристов')[0][1].map(i => data.districts[i][0]), ['otradnoe']);
assert.equal(search('Тверская')[0][0], 'Тверская улица');
assert.ok(search('Ленинский проспект')[0][1].length > 1);
assert.ok(search('МКАД')[0][1].length > 20);
assert.equal(search('1-я Тверская-Ямская')[0][0], '1-я Тверская-Ямская улица');
assert.equal(search('несуществующаяабракадабра').length, 0);
assert.equal(search('улица').length, 0);
assert.equal(search('а').length, 0);
assert.equal(findStreets([['Название', [0], ['Старое имя']]], 'старое')[0][0], 'Название');
const covered = new Set();
for (const [name, ids, aliases] of data.streets) {
  assert.ok(name && ids.length && Array.isArray(aliases));
  assert.equal(new Set(ids).size, ids.length);
  for (const id of ids) {
    assert.ok(data.districts[id]); covered.add(id);
    await readFile(new URL(`rayon/${data.districts[id][0]}/index.html`, root));
  }
}
assert.equal(covered.size, 125);
const olonets = addresses[0];
const seen = new Set();
for (const [slug, numbers] of Object.entries(olonets.districts)) {
  for (const number of numbers) {
    assert.ok(!seen.has(number));
    seen.add(number);
    assert.equal(findAddress(addresses, splitAddress(`Олонецкая, ${number}`)).slug, slug);
  }
}
assert.equal(findAddress(addresses, splitAddress('ул. Олонецкая, дом 21А, строение 2')).slug, 'otradnoe');
assert.equal(findAddress(addresses, splitAddress('г. Москва, Олонецкая улица, 13-с1')).number, '13с1');
assert.equal(findAddress(addresses, splitAddress('Олонецкая 14 вл. 1')).slug, 'ostankinskiy');
assert.equal(findAddress(addresses, splitAddress('Олонецкая 999')).slug, undefined);
assert.equal(splitAddress('Олонецкая улица'), null);
assert.equal(splitAddress('1-я Тверская-Ямская'), null);
assert.equal(findAddress(addresses, splitAddress('Олонецкий проезд 6')), null);
console.log(`Поиск: нормализация, приоритет точных совпадений, алиасы, неоднозначность и ссылки ${data.streets.length} улиц — OK`);
