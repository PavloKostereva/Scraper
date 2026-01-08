# Реалізована функція імпорту listings

Я створив скрипт `create_ghost_listings.py`, який імпортує listings з JSON-файлів у базу даних Supabase.

## Що робить скрипт

Скрипт читає JSON файли з listings (один об'єкт або масив) і створює ghost listings у Supabase. Для кожного listing він:

- Генерує унікальний claim token
- Автоматично визначає платформу джерела (craigslist/gumtree) з URL
- Витягує email продавця з поля contact_info (якщо є)
- Перевіряє на дублікати за комбінацією title + location
- Встановлює статус "pending_claim" та термін дії 30 днів

## Формат вхідних даних

Скрипт приймає JSON з такою структурою:

```json
{
  "listing_id": "7886200749",
  "title": "Hurry before you miss our 50% off promo!",
  "location": "201 W Stassney Lane, Austin, TX 78745",
  "price": "$21",
  "description": "Get 2 months 50% off today!",
  "url": "https://austin.craigslist.org/...",
  "reply_url": "N/A",
  "scraped_at": "2025-11-17T17:35:50.616370",
  "contact_info": "N/A"
}
```

Обов'язкові поля: `title`, `location`. Решта опціональні.

## Як використовувати

```bash
# Базове використання
python3 create_ghost_listings.py listings.json

# Обмежити кількість listings
python3 create_ghost_listings.py listings.json --max-inserts 10

# Тестування без вставки в базу
python3 create_ghost_listings.py listings.json --dry-run

# Дозволити дублікати
python3 create_ghost_listings.py listings.json --allow-duplicates
```

## Налаштування

Потрібно створити файл `.env` з наступними змінними:

```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE=your_service_role_key
```

## Додаткові функції

Також створив скрипт `check_ghost_listings.py` для перевірки створених listings:

```bash
# Показати останні 10 listings
python3 check_ghost_listings.py 10

# Статистика за статусами
python3 check_ghost_listings.py count
```

## Результат

Скрипт створює записи в таблиці `ghost_listings` з усіма необхідними полями, готові для подальшої обробки та відправки claim посилань продавцям.

