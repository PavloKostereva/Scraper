# Скрипт для імпорту listings у Supabase

## Опис

Скрипт `create_ghost_listings.py` призначений для автоматичного імпорту listings з JSON-файлів у базу даних Supabase. Він перетворює дані зі скраперів (Gumtree, Craigslist та інші платформи) у формат ghost listings, які готові до подальшої обробки та відправки продавцям.

## Основні функції

### 1. Імпорт listings з JSON

- Підтримує як одиночні об'єкти, так і масиви listings
- Автоматично валідує структуру даних
- Обробляє помилки та надає детальну інформацію про проблеми

### 2. Створення ghost listings

- Генерує унікальний claim token для кожного listing
- Автоматично визначає джерело (platform) з URL
- Витягує email продавця з поля contact_info
- Встановлює статус "pending_claim" та термін дії (30 днів)

### 3. Захист від дублікатів

- Автоматично перевіряє наявність існуючих listings за комбінацією title + location
- Пропускає дублікати без створення нових записів
- Можливість примусового створення дублікатів через опцію --allow-duplicates

### 4. Гнучке налаштування

- Обмеження кількості listings для імпорту
- Режим тестування (dry-run) без вставки в базу
- Детальна статистика обробки

## Формат вхідних даних

Скрипт приймає JSON файли з наступною структурою:

```json
{
  "listing_id": "7886200749",
  "title": "Hurry before you miss our 50% off promo! Available for all sizes!",
  "location": "201 W Stassney Lane, Austin, TX 78745",
  "price": "$21",
  "description": "Get 2 months 50% off today! Call today to rent your unit over the phone!",
  "url": "https://austin.craigslist.org/prk/d/austin-hurry-before-you-miss-our-50-off/7886200749.html",
  "reply_url": "N/A",
  "scraped_at": "2025-11-17T17:35:50.616370",
  "contact_info": "N/A"
}
```

**Обов'язкові поля:**

- `title` - назва listing
- `location` - локація

**Опціональні поля:**

- `listing_id` - ідентифікатор listing
- `price` - ціна
- `description` - опис
- `url` - посилання на listing (використовується для визначення платформи)
- `reply_url` - посилання для відповіді
- `scraped_at` - дата скрапінгу
- `contact_info` - контактна інформація (email буде витягнуто автоматично)

## Встановлення та налаштування

### Вимоги

- Python 3.7+
- Бібліотеки: `supabase`, `python-dotenv`

### Налаштування

1. Створіть файл `.env` в корені проекту
2. Додайте змінні оточення:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE=your_service_role_key
   ```

## Використання

### Базове використання

```bash
python3 create_ghost_listings.py listings.json
```

### Обмеження кількості listings

```bash
python3 create_ghost_listings.py listings.json --max-inserts 10
```

### Тестування без вставки в базу (dry-run)

```bash
python3 create_ghost_listings.py listings.json --dry-run
```

### Дозвіл дублікатів

```bash
python3 create_ghost_listings.py listings.json --allow-duplicates
```

## Результат роботи

Скрипт створює записи в таблиці `ghost_listings` з наступними полями:

- `claim_token` - унікальний токен для claim посилання
- `title` - назва listing
- `description` - опис
- `original_price` - ціна
- `location` - локація
- `seller_email` - email продавця (якщо знайдено в contact_info)
- `source_platform` - платформа джерела (craigslist, gumtree, unknown)
- `status` - статус (завжди "pending_claim" при створенні)
- `expires_at` - термін дії (30 днів від дати створення)

## Приклад виводу

```
============================================================
CREATE GHOST LISTINGS FROM JSON
============================================================

Connected to Supabase successfully

Loading JSON from: listings.json
Loaded 5 listing(s)

============================================================
PROCESSING LISTINGS
============================================================

[1/5] Processing: Hurry before you miss our 50% off promo...
   Listing ID: 7886200749
   Inserted ghost listing
   Token: XXI3lZwm...

[2/5] Processing: Storage Unit Available...
   Listing ID: 7886200750
   Skipped (duplicate already exists)

============================================================
SUMMARY
============================================================
Processed: 5
Success: 4
Skipped (duplicates): 1
Errors: 0
============================================================
```

## Перевірка результатів

Для перевірки створених ghost listings використовуйте скрипт `check_ghost_listings.py`:

```bash
# Показати останні 10 listings
python3 check_ghost_listings.py 10

# Показати статистику за статусами
python3 check_ghost_listings.py count
```

## Обробка помилок

Скрипт автоматично обробляє наступні ситуації:

- Відсутні обов'язкові поля (title, location) - пропускає з помилкою
- Дублікати listings - пропускає з повідомленням
- Помилки підключення до Supabase - виводить детальну інформацію
- Невірний формат JSON - виводить опис помилки

## Інтеграція з іншими компонентами

Створені ghost listings можуть бути використані:

1. Скриптом `send_claim_links_via_gumtree.py` - для створення JSON з claim посиланнями
2. Месенджером `gumtree_messenger.py` - для автоматичної відправки повідомлень продавцям
3. Веб-інтерфейсом - для відображення listings та обробки claim запитів

## Підтримка

При виникненні проблем перевірте:

- Наявність та коректність змінних оточення в `.env`
- Формат JSON файлу (використовуйте --dry-run для перевірки)
- Підключення до інтернету та доступність Supabase
- Права доступу до бази даних (service role key)
