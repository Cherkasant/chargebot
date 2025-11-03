## ChargeBot — Telegram бот по поиску электрозарядок в РБ

Бот ищет ближайшие электрозарядные станции по вашей геолокации (Республика Беларусь) c использованием OpenChargeMap. Технологии: Python 3.8+, python-telegram-bot v20 (async), aiohttp, SQLite (по умолчанию), Requests/BS4 (для будущих парсеров).

### Быстрый старт

1. Установите Python 3.8+
2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Создайте `.env` в корне и заполните:
   ```bash
   TELEGRAM_BOT_TOKEN=ваш_токен
   DATABASE_URL=sqlite:///data/chargebot.db
   OCM_API_KEY=
   DEFAULT_RADIUS_KM=10
   MAX_RESULTS=10
   ```
4. Запуск:
   ```bash
   python -m src.chargebot.main
   ```

Отправьте боту геолокацию — получите список ближайших станций с кнопкой «Открыть на карте».

### Команды
- `/start` — приветствие и запрос геолокации
- `/help` — помощь

### Настройки
- `TELEGRAM_BOT_TOKEN` — токен бота Telegram (обязателен)
- `DATABASE_URL` — `sqlite:///data/chargebot.db` по умолчанию
- `OCM_API_KEY` — ключ OpenChargeMap (опционально)
- `DEFAULT_RADIUS_KM` — радиус поиска в км (по умолчанию 10)
- `MAX_RESULTS` — ограничение результатов (по умолчанию 10)

### Docker (опционально)

1. Собрать образ:
   ```bash
   docker build -t chargebot .
   ```
2. Запуск (Windows PowerShell):
   ```bash
   docker run --name chargebot --rm \
     -e TELEGRAM_BOT_TOKEN=$Env:TELEGRAM_BOT_TOKEN \
     -e DATABASE_URL=sqlite:////app/data/chargebot.db \
     -e OCM_API_KEY=$Env:OCM_API_KEY \
     -v ${PWD}/data:/app/data \
     chargebot
   ```

### Миграция на PostgreSQL

Текущая минималистичная БД использует SQLite через `sqlite3`. Для перехода на PostgreSQL рекомендуется вынести слой доступа к данным на ORM (например, SQLAlchemy) или реализовать отдельный репозиторий под Postgres.


