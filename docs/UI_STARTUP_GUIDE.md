# Руководство по запуску UI

## Запуск обоих UI одновременно

### Старый UI (HTMX + Jinja2)
**Расположение:** Обслуживается через backend FastAPI  
**Порт:** 8000  
**URL:** http://localhost:8000

**Запуск:**
```bash
cd backend
python main.py
```

### Новый UI (Next.js + React)
**Расположение:** `ui/`  
**Порт:** 3000  
**URL:** http://localhost:3000

**Запуск:**
```bash
cd ui
npm run dev
```

## Конфигурация

### Новый UI (.env.local)
Файл `ui/.env.local` должен содержать:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws/events
```

### Backend (CORS)
Backend автоматически добавляет `localhost:3000` в разрешенные origins для CORS.

## Порты

- **Backend (старый UI):** 8000
- **Новый UI (Next.js):** 3000

Оба могут работать одновременно без конфликтов.

## Проверка запуска

1. **Backend:** http://localhost:8000 - должен показать старый UI
2. **Новый UI:** http://localhost:3000 - должен показать новый UI

## Устранение проблем

### Новый UI не стартует

1. Проверьте что порт 3000 свободен:
   ```bash
   netstat -ano | findstr :3000
   ```

2. Проверьте что `.env.local` существует и содержит правильные URL

3. Проверьте зависимости:
   ```bash
   cd ui
   npm install
   ```

4. Очистите кэш Next.js:
   ```bash
   cd ui
   rm -rf .next
   npm run dev
   ```

### Конфликт портов

Если порт 3000 занят, можно изменить в `package.json`:
```json
"dev": "next dev -p 3001"
```

И обновить `.env.local` соответственно.
