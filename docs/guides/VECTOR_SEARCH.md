# Vector Search Guide

## Обзор

Система векторного поиска позволяет находить похожие воспоминания агентов на основе семантического сходства, а не только точного совпадения текста. Это реализовано через интеграцию с pgvector - расширением PostgreSQL для работы с векторными данными.

## Архитектура

### Компоненты

1. **pgvector Extension** - расширение PostgreSQL для векторных операций
2. **AgentMemory.embedding** - векторное поле в модели памяти
3. **EmbeddingService** - сервис генерации embeddings через LLM
4. **MemoryService.search_memories_vector()** - метод векторного поиска

### Поток данных

```
Текст запроса
    ↓
EmbeddingService.generate_embedding()
    ↓
Векторное представление (1536 измерений)
    ↓
pgvector cosine similarity search
    ↓
Похожие воспоминания (отсортированные по similarity)
```

## Установка и настройка

### 1. Установка pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Миграция `024_add_vector_search.py` автоматически устанавливает расширение.

### 2. Применение миграции

```bash
cd backend
alembic upgrade head
```

### 3. Проверка установки

```python
from app.core.database import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.connect() as conn:
    result = conn.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');"))
    assert result.scalar() == True
```

## Использование

### Генерация embeddings

```python
from app.services.embedding_service import EmbeddingService
from app.core.database import SessionLocal

db = SessionLocal()
embedding_service = EmbeddingService(db)

# Генерация embedding для текста
embedding = await embedding_service.generate_embedding("Python is a programming language")
# Результат: [0.1, 0.2, ...] (1536 значений)

# Batch генерация
texts = ["text 1", "text 2", "text 3"]
embeddings = await embedding_service.generate_embeddings_batch(texts)
```

### Сохранение памяти с embedding

#### Автоматическая генерация (рекомендуется)

```python
from app.services.memory_service import MemoryService

memory_service = MemoryService(db)

# Сохранить память с автоматической генерацией embedding (async)
memory = await memory_service.save_memory_async(
    agent_id=agent_id,
    memory_type="fact",
    content={"fact": "Python is a programming language"},
    summary="Python programming language fact",
    generate_embedding=True  # Автоматически генерирует embedding
)

# Embedding уже сохранен в memory.embedding
```

#### Ручная генерация

```python
from app.services.embedding_service import EmbeddingService

embedding_service = EmbeddingService(db)

# Сохранить память
memory = memory_service.save_memory(
    agent_id=agent_id,
    memory_type="fact",
    content={"fact": "Python is a programming language"},
    summary="Python programming language fact"
)

# Генерировать и сохранить embedding вручную
embedding = await embedding_service.generate_embedding(memory.summary or "")
memory.embedding = embedding
db.commit()
```

### Векторный поиск

```python
# Поиск похожих воспоминаний
results = await memory_service.search_memories_vector(
    agent_id=agent_id,
    query_text="programming language",
    limit=10,
    similarity_threshold=0.7,  # Минимальная схожесть
    memory_type="fact",  # Опциональный фильтр
    combine_with_text_search=True  # Комбинировать с текстовым поиском
)

for memory in results:
    print(f"Memory: {memory.summary}, Similarity: {similarity}")
```

## Параметры поиска

### similarity_threshold

Минимальная cosine similarity (0.0 - 1.0):
- `0.9+` - очень похожие
- `0.7-0.9` - похожие
- `0.5-0.7` - умеренно похожие
- `<0.5` - слабо похожие

### combine_with_text_search

Если `True`, результаты векторного поиска дополняются результатами текстового поиска для более полного покрытия.

## Индексы

Система использует HNSW (Hierarchical Navigable Small World) индекс для быстрого приближенного поиска ближайших соседей.

### Параметры индекса

- `m = 16` - количество связей на уровень
- `ef_construction = 64` - размер списка кандидатов при построении

Эти параметры можно настроить в миграции при необходимости.

## Производительность

### Кэширование

`EmbeddingService` кэширует embeddings для часто используемых текстов:
- Размер кэша: 1000 записей
- LRU стратегия замены

### Оптимизация запросов

1. Используйте фильтры (`memory_type`, `agent_id`) для уменьшения пространства поиска
2. Установите разумный `similarity_threshold` для фильтрации слабо релевантных результатов
3. Используйте `limit` для ограничения количества результатов

## Модели embeddings

По умолчанию используется модель `nomic-embed-text` через Ollama. Размерность: 1536.

### Настройка модели

Измените метод `_get_default_embedding_model()` в `EmbeddingService`:

```python
def _get_default_embedding_model(self) -> str:
    return "your-embedding-model"  # Ваша модель
```

## Обработка ошибок

Система имеет несколько уровней fallback:

1. **Ошибка генерации embedding** → возвращает zero vector
2. **Ошибка векторного поиска** → fallback на текстовый поиск (если `combine_with_text_search=True`)
3. **Отсутствие embeddings** → использует только текстовый поиск

## Тестирование

### Unit тесты

```bash
pytest backend/tests/test_embedding_service.py
pytest backend/tests/test_memory_vector_search.py
```

### Интеграционные тесты

```bash
pytest backend/tests/integration/test_vector_search.py
```

## Миграция существующих данных

Для генерации embeddings для существующих записей памяти используйте скрипт (будет создан в этапе 4.2):

```bash
python backend/scripts/migrate_memories_to_vectors.py
```

## Ограничения

1. **Размерность**: Текущая размерность 1536 (для OpenAI-совместимых моделей)
2. **Производительность**: HNSW индекс требует памяти пропорционально количеству векторов
3. **Точность**: HNSW - приближенный алгоритм, точность зависит от параметров индекса

## Будущие улучшения

- Поддержка различных размерностей embeddings
- Автоматическая настройка параметров индекса
- Метрики качества поиска
- A/B тестирование различных моделей embeddings

