# Dogma Flats Bot


## Переменные окружения

Создайте `.env` в корне проекта:

```env
# Парсер
BASE_URL=https://dogma.ru

# Бот
TG_BOT=123456:ABC-DEF...           # токен от @BotFather
LLM_API_KEY=sk-or-...              # ключ провайдера LLM (OpenRouter/AITUNNEL)
PARSER_URL=http://localhost:8000   # адрес запущенного server.py

# Опционально — переопределить провайдера/модель LLM (дефолты см. в agent/agent.py)
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free

# Celery
REDIS_URL=redis://localhost:6379/0
```

## Установка

```bash
pip install httpx fastapi uvicorn openai aiogram celery redis python-dotenv
```

Redis должен быть поднят локально или в докере:

```bash
docker run -d -p 6379:6379 redis
```

## Запуск

### 1. Парсер — разово, вручную

Разово наполнить/обновить базу данных (без Celery, просто скрипт):

```bash
python parser.py
```

### 2. Парсер — как периодическая задача Celery

Расписание задано в `tasks.py` (по умолчанию — раз в 30 минут). Нужны
**два отдельных процесса**:

```bash
# терминал 1 — воркер (выполняет задачи)
celery -A tasks worker --loglevel=info

# терминал 2 — планировщик (кладёт задачу по расписанию)
celery -A tasks beat --loglevel=info
```

Прогнать задачу вручную, не дожидаясь расписания:

```bash
pip install -r requirements.txt
```

### 3. Сервер

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 4. Бот

```bash
python bot.py
```

## Порядок запуска с нуля

1. Заполнить `.env`.
2. `python parser.py` — наполнить базу хотя бы раз, иначе бот будет находить 0 квартир.
3. `uvicorn server:app --host 0.0.0.0 --port 8000` — в отдельном терминале, держать запущенным.
4. `python bot.py` — в ещё одном отдельном терминале.
5. (Опционально) `celery -A tasks worker` и `celery -A tasks beat` — вместо ручного шага 2 в будущем, для регулярного автообновления данных.
6. Написать `/start` своему боту в Telegram.
