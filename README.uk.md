[English](README.md) | **Українська**

[![CI](https://github.com/ZavarOvek/tg-corpus/actions/workflows/ci.yml/badge.svg)](https://github.com/ZavarOvek/tg-corpus/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# tg-corpus — Telegram-канал → чистий текстовий корпус

Інструмент командного рядка, що перетворює публічний Telegram-канал на
чистий, дедуплікований текстовий корпус, готовий для лінгвістичних
досліджень, NLP-пайплайнів чи аналізу контенту.

## Архітектура

Дві чітко розділені стадії:

1. **fetch** (мережа) — тонка обгортка над Telethon, що вивантажує сирі
   повідомлення у JSONL, зберігаючи метадані (id, дата, перегляди, поширення,
   позначка репосту).
2. **clean** (офлайн) — чистий, повністю покритий тестами пайплайн:
   фільтрація, очищення тексту, дедуплікація й експорт. Можна перечищати з
   іншими налаштуваннями без повторного скачування.

## Можливості

- Очищення: емодзі й піктограми, URL-адреси, @згадки, символи нульової
  ширини, нормалізація пробілів (хештеги лишаються за замовчуванням —
  часто несуть сенс)
- Автодетект і видалення підпису (`--strip-signature`): багато каналів
  завершують кожен пост однаковим рядком (наприклад, "Підписуйтесь" чи
  авторський підпис) — це шаблон, а не контент, і він спотворює частоти слів
  надалі. Детектується автоматично з самих даних по кожному каналу окремо,
  нічого налаштовувати вручну не треба; канали без повторюваного підпису
  лишаються недоторканими
- Фільтрація: порожні/службові повідомлення, репости (опційно), мінімальна
  кількість слів
- Дедуплікація: без урахування регістру й пунктуації, лишає перше
  (хронологічно найраніше) входження
- Хронологічний порядок відновлюється з порядку Telegram API (від новіших
  до старіших)
- Експорт у JSONL (повні метадані), CSV (сумісний з Excel) та звичайний
  текст — по одному повідомленню на рядок, готовий одразу подавати в
  інші інструменти на кшталт [ua-freq-dict](https://github.com/ZavarOvek/ua-freq-dict)
- Прозора статистика відсіву: `total: 8  kept: 5  dropped: no_text=1, too_short=1, duplicate=1`

## Встановлення

```bash
pip install .
```

## Використання

**1. Отримай API-ключі** на https://my.telegram.org, збережи їх у файл
`.env` у теці проєкту (він уже в .gitignore — ніколи не комітьте його):

```
TG_API_ID=12345
TG_API_HASH=abcdef...
```

```bash
tg-corpus fetch @якийсь_канал -o raw.jsonl --limit 5000
```

`.env` завантажується автоматично. Якщо зручніше користуватись справжніми
змінними оточення (наприклад у CI) — це теж працює, `.env` лише зручність,
а не вимога.

При першому запуску Telethon спитає номер телефону й код входу, потім
збереже локальний файл `.session` (теж у .gitignore — не комітьте і його).

**2. Побудуй корпус (офлайн, повторювано):**

```bash
tg-corpus clean raw.jsonl -o corpus/ --min-words 3 --drop-forwards --strip-signature
```

```
detected sign-off, stripped: 'Subscribe for more updates.'
total: 5000  kept: 4102
dropped: no_text=412, forward=305, too_short=98, duplicate=83
written: corpus/corpus.jsonl
written: corpus/corpus.csv
written: corpus/corpus.txt
```

Спробуй без ключів на прикладеному зразку:

```bash
tg-corpus clean examples/raw_sample.jsonl -o /tmp/demo --strip-signature
```

![Вивід tg-corpus clean](docs/screenshot.png)

## Як бібліотека

```python
from tgcorpus import run_pipeline
from tgcorpus.io import read_jsonl

result = run_pipeline(read_jsonl("raw.jsonl"), min_words=3, drop_forwards=True)
print(result.stats)  # Counter із причинами відсіву
texts = [r["text"] for r in result.records]
```

## Обмеження та плани розвитку

Дедуплікація точна (після нормалізації); детекція близьких дублів
(edit-distance / shingles) у планах. Детекція підпису шукає точний
повторюваний рядок, тож канал, що варіює формулювання підпису між постами,
не буде спіймано — тільки дослівні повтори. Збирається лише текст — підписи
до медіа входять, самі медіафайли не завантажуються. Поважайте умови
використання Telegram і збирайте дані лише з публічних каналів, з якими
вам дозволено працювати.

## Тестування

Увесь пайплайн очищення покритий офлайн-тестами на синтетичних даних —
мережа й ключі не потрібні:

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

## Ліцензія

MIT
