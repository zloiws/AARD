# Auth API Endpoints

API для аутентификации и авторизации.

## POST /api/auth/register

Регистрация нового пользователя.

### Request Body

```json
{
  "username": "user123",
  "email": "user@example.com",
  "password": "secure_password",
  "role": "user"
}
```

### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "user123",
  "email": "user@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T12:00:00Z",
  "last_login": null
}
```

---

## POST /api/auth/login

Вход в систему.

### Request Body

```json
{
  "username": "user123",
  "password": "secure_password"
}
```

### Response

```json
{
  "token": "session_token_here",
  "user": {
    "id": "...",
    "username": "user123",
    "email": "user@example.com",
    "role": "user",
    "is_active": true
  },
  "expires_at": "2024-01-02T12:00:00Z"
}
```

**Примечание:** Токен также устанавливается в HTTP-only cookie.

---

## POST /api/auth/logout

Выход из системы.

---

## GET /api/auth/me

Получить информацию о текущем пользователе.

---

## POST /api/auth/refresh

Обновить токен сессии.

