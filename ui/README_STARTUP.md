# Запуск нового UI

## Быстрый старт

1. Убедитесь что backend запущен на порту 8000
2. Установите зависимости (если еще не установлены):
   ```bash
   npm install
   ```

3. Запустите dev сервер:
   ```bash
   npm run dev
   ```

4. Откройте http://localhost:3000 в браузере

## Конфигурация

Файл `.env.local` должен содержать:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/ws/events
```

Если файл отсутствует, он будет создан автоматически при первом запуске.

## Порты

- **Backend (старый UI):** http://localhost:8000
- **Новый UI (Next.js):** http://localhost:3000

Оба могут работать одновременно без конфликтов.

## Устранение проблем

### Порт 3000 занят

Если порт 3000 занят, можно изменить в `package.json`:
```json
"dev": "next dev -p 3001"
```

И обновить `.env.local` соответственно.

### Ошибки при запуске

1. Очистите кэш Next.js:
   ```bash
   rm -rf .next
   npm run dev
   ```

2. Переустановите зависимости:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

3. Проверьте что backend запущен на порту 8000
