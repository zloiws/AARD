## Полное ТЗ: Визуализация самоэволюционирующей AI-системы с полной интеграцией чата и бэкенда

### 1. Архитектурная схема

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ФРОНТЕНД (React/TS)                            │
├─────────────┬───────────────────────────────┬───────────────────────────────┤
│    ЧАТ      │     ВИЗУАЛИЗАЦИЯ              │     МЕТА-УПРАВЛЕНИЕ          │
│ (50%)       │     (40%)                     │     (10%/сворачиваемое)      │
├─────────────┼───────────────────────────────┼───────────────────────────────┤
│ • Сессии    │ • Граф исполнения (реалтайм)  │ • Настройки модели           │
│ • Вкладки   │ • Граф эволюции (версии)      │ • Уровень автономности       │
│ • История   │ • Песочница обучения          │ • Правила изменений          │
│ • Управление│ • Diff-просмотрщик            │ • Мониторинг системы         │
└─────────────┴───────────────┬───────────────┴───────────────────────────────┘
                              │
               WebSocket/SSE  │  REST API
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              БЭКЕНД (Python/FastAPI)                        │
├─────────────┬───────────────────────────────┬───────────────────────────────┤
│   ЧАТ API   │    МЕТА-ТРЕКЕР               │    ИСПОЛНЕНИЕ                │
├─────────────┼───────────────────────────────┼───────────────────────────────┤
│ • LLM вызовы│ • Отслеживание изменений     │ • Запуск агентов              │
│ • Сессии    │ • Верионирование компонентов │ • Выполнение инструментов     │
│ • Контекст  │ • История эволюции           │ • Работа с памятью            │
│ • Потоковая │ • Анализ зависимостей        │ • RAG операции                │
│   генерация │ • Сбор метрик                │ • Тестирование                │
└─────────────┴───────────────┬───────────────┴───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          САМОЭВОЛЮЦИОНИРУЮЩАЯ СИСТЕМА                       │
├─────────────────────┬─────────────────────┬─────────────────────────────────┤
│ Генерация кода      │ Планирование        │ Обучение в песочнице           │
├─────────────────────┼─────────────────────┼─────────────────────────────────┤
│ • Создание агентов  │ • Создание планов   │ • A/B тестирование             │
│ • Создание инструм. │ • Репланирование    │ • Метрики качества             │
│ • Модификация кода  │ • Оптимизация       │ • Авто-дообучение              │
│ • Рефакторинг       │ • Решение конфликтов│ • Безопасное исполнение        │
└─────────────────────┴─────────────────────┴─────────────────────────────────┘
```

### 2. API спецификация для полной интеграции

**Файл:** `backend/api/__init__.py`

#### 2.1. WebSocket эндпоинты (реалтайм события)

```python
# WebSocket соединения
@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    Реалтайм события чата:
    - Потоковая генерация ответа
    - Статусы агентов
    - Обновления контекста
    """

@router.websocket("/ws/execution/{session_id}")
async def websocket_execution(websocket: WebSocket, session_id: str):
    """
    Реалтайм события графа исполнения:
    - node_started: началось выполнение ноды
    - node_completed: нода завершила выполнение
    - node_failed: ошибка в ноде
    - edge_created: создано новое соединение
    - graph_updated: обновлен весь граф
    """

@router.websocket("/ws/meta")
async def websocket_meta(websocket: WebSocket):
    """
    Реалтайм мета-события системы:
    - component_generated: создан новый компонент
    - component_modified: изменен существующий
    - test_completed: завершен тест
    - learning_iteration: завершена итерация обучения
    - version_promoted: версия промоутед в продакшн
    """
```

#### 2.2. REST API эндпоинты

```python
# Чат и сессии
@router.get("/api/chat/sessions")
async def get_chat_sessions():
    """Получить все сессии чата"""

@router.post("/api/chat/sessions")
async def create_chat_session(session: ChatSessionCreate):
    """Создать новую сессию чата"""

@router.post("/api/chat/{session_id}/message")
async def send_chat_message(session_id: str, message: ChatMessage):
    """Отправить сообщение в чат (инициирует выполнение)"""

@router.post("/api/chat/{session_id}/stop")
async def stop_generation(session_id: str):
    """Остановить генерацию текущего ответа"""

# Граф исполнения
@router.get("/api/execution/{session_id}/graph")
async def get_execution_graph(session_id: str):
    """Получить полный граф исполнения для сессии"""

@router.get("/api/execution/{session_id}/node/{node_id}")
async def get_node_details(session_id: str, node_id: str):
    """Получить детальную информацию о ноде"""

@router.post("/api/execution/{session_id}/replay/{node_id}")
async def replay_node(session_id: str, node_id: str):
    """Перезапустить выполнение конкретной ноды"""

# Мета-данные системы
@router.get("/api/meta/components")
async def get_all_components():
    """Получить все компоненты системы с их версиями"""

@router.get("/api/meta/components/{component_id}")
async def get_component_history(component_id: str):
    """Получить историю изменений компонента"""

@router.get("/api/meta/components/{component_id}/diff/{version_a}/{version_b}")
async def get_component_diff(component_id: str, version_a: str, version_b: str):
    """Получить diff между версиями компонента"""

@router.post("/api/meta/components/{component_id}/rollback/{version}")
async def rollback_component(component_id: str, version: str):
    """Откатить компонент к указанной версии"""

@router.get("/api/meta/evolution/timeline")
async def get_evolution_timeline():
    """Получить timeline эволюции системы"""

# Управление системой
@router.get("/api/system/metrics")
async def get_system_metrics():
    """Получить метрики системы"""

@router.post("/api/system/autonomy/level")
async def set_autonomy_level(level: AutonomyLevel):
    """Установить уровень автономности системы"""

@router.get("/api/system/predictions")
async def get_system_predictions():
    """Получить предсказания системы о необходимых изменениях"""

@router.post("/api/system/predictions/{prediction_id}/execute")
async def execute_prediction(prediction_id: str):
    """Выполнить предложенное изменение"""

# Песочница обучения
@router.post("/api/sandbox/experiments")
async def create_experiment(experiment: ExperimentCreate):
    """Создать новый эксперимент в песочнице"""

@router.get("/api/sandbox/experiments/{experiment_id}")
async def get_experiment_results(experiment_id: str):
    """Получить результаты эксперимента"""

@router.post("/api/sandbox/experiments/{experiment_id}/approve")
async def approve_experiment(experiment_id: str):
    """Одобрить изменения из эксперимента"""

@router.post("/api/sandbox/experiments/{experiment_id}/reject")
async def reject_experiment(experiment_id: str):
    """Отклонить изменения из эксперимента"""
```

### 3. Структуры данных (Pydantic модели)

**Файл:** `backend/models/schemas.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

# Enums
class NodeType(str, Enum):
    USER_INPUT = "user_input"
    MODEL_SELECTOR = "model_selector"
    AGENT = "agent"
    TOOL = "tool"
    MEMORY = "memory"
    RAG = "rag"
    DATABASE = "database"
    TEST = "test"
    PLAN = "plan"
    DECISION = "decision"
    RESPONSE = "response"
    ERROR = "error"
    LEARNING = "learning"

class ComponentType(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    MEMORY = "memory"
    MODEL = "model"
    CHAIN = "chain"
    WORKFLOW = "workflow"

class AutonomyLevel(str, Enum):
    MANUAL = "manual"  # Только с подтверждением
    ASSISTED = "assisted"  # С предложениями
    SEMI_AUTO = "semi_auto"  # Авто, кроме критических
    FULL = "full"  # Полная автономность

# Chat models
class ChatMessage(BaseModel):
    id: str
    session_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    node_id: Optional[str] = None  # Связь с нодой в графе

class ChatSession(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage] = []
    execution_graph_id: Optional[str] = None

# Execution graph models
class ExecutionNode(BaseModel):
    id: str
    type: NodeType
    data: Dict[str, Any]
    position: Dict[str, float]  # {x: float, y: float}
    status: str = "pending"  # pending, executing, success, error
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    chat_message_ids: List[str] = []  # Связь с сообщениями чата
    parent_node_id: Optional[str] = None
    version: str = "latest"

class ExecutionEdge(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    label: Optional[str] = None
    data: Dict[str, Any] = {}

class ExecutionGraph(BaseModel):
    id: str
    session_id: str
    nodes: List[ExecutionNode] = []
    edges: List[ExecutionEdge] = []
    created_at: datetime
    updated_at: datetime

# Meta models
class ComponentVersion(BaseModel):
    version: str
    component_id: str
    component_type: ComponentType
    created_at: datetime
    created_by: str  # prompt_id, test_id, etc.
    code_hash: str
    file_path: str
    dependencies: List[str] = []
    test_results: Dict[str, Any] = {}
    performance_metrics: Dict[str, float] = {}
    metadata: Dict[str, Any] = {}

class Component(BaseModel):
    id: str
    name: str
    type: ComponentType
    description: str
    versions: List[ComponentVersion] = []
    current_version: str
    usage_count: int = 0
    last_used: Optional[datetime] = None
    tags: List[str] = []

class MetaEvent(BaseModel):
    id: str
    type: str  # component_created, code_modified, test_completed, etc.
    timestamp: datetime
    component_id: Optional[str] = None
    component_version: Optional[str] = None
    trigger: Dict[str, Any]  # Что вызвало событие
    data: Dict[str, Any]  # Детали события
    metadata: Dict[str, Any] = {}

# System models
class SystemMetrics(BaseModel):
    total_components: int
    active_versions: int
    deprecated_versions: int
    autonomy_level: AutonomyLevel
    avg_improvement_rate: float
    system_stability: float
    total_auto_changes: int
    change_success_rate: float
    timeline: List[Dict[str, Any]] = []

class Prediction(BaseModel):
    id: str
    type: str  # optimization, refactoring, new_component, etc.
    component_id: Optional[str] = None
    description: str
    expected_improvement: float
    confidence: float
    estimated_effort: float  # в часах
    priority: int  # 1-10
    created_at: datetime

# Sandbox models
class Experiment(BaseModel):
    id: str
    name: str
    description: str
    component_id: str
    version_a: str
    version_b: str
    test_suite: List[str] = []
    status: str = "running"  # running, completed, approved, rejected
    results_a: Dict[str, Any] = {}
    results_b: Dict[str, Any] = {}
    conclusion: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
```

### 4. Мета-трекер с интеграцией в существующую систему

**Файл:** `backend/core/meta_tracker.py`

```python
import asyncio
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MetaTracker:
    """Система отслеживания всех изменений в самоэволюционирующей системе"""
    
    def __init__(self, db_connection, websocket_manager):
        self.db = db_connection
        self.ws = websocket_manager
        self.component_registry = {}
        self.file_watcher = None
        
    async def start(self):
        """Запуск мета-трекера"""
        # 1. Сканируем существующий код
        await self._scan_existing_components()
        
        # 2. Запускаем отслеживание изменений файлов
        self._start_file_watching()
        
        # 3. Подписываемся на события системы
        await self._subscribe_to_system_events()
        
        # 4. Запускаем периодический сбор метрик
        asyncio.create_task(self._collect_metrics_periodically())
    
    async def track_code_generation(self, event: Dict[str, Any]):
        """Отслеживание генерации нового кода"""
        component_info = await self._analyze_generated_code(
            event['code'],
            event['prompt'],
            event.get('parent_component')
        )
        
        # Сохраняем в БД
        await self.db.save_component_version(component_info)
        
        # Отправляем WebSocket событие
        await self.ws.broadcast_meta_event({
            'type': 'component_generated',
            'component_id': component_info['id'],
            'version': component_info['version'],
            'data': component_info
        })
        
        # Обновляем граф эволюции
        await self._update_evolution_graph(component_info)
    
    async def track_code_modification(self, event: Dict[str, Any]):
        """Отслеживание модификации существующего кода"""
        diff = await self._calculate_code_diff(
            event['old_code'],
            event['new_code']
        )
        
        # Анализируем причину изменения
        reason = await self._analyze_change_reason(
            diff,
            event.get('test_results'),
            event.get('performance_metrics'),
            event.get('user_feedback')
        )
        
        # Сохраняем новую версию
        new_version = await self._create_new_version(
            event['component_id'],
            event['new_code'],
            reason
        )
        
        # Запускаем авто-тесты для новой версии
        test_results = await self._run_automated_tests(new_version)
        
        # Принимаем решение о промоуте версии
        if await self._should_promote_version(test_results):
            await self._promote_version(new_version)
    
    async def track_learning_iteration(self, experiment: Dict[str, Any]):
        """Отслеживание итерации обучения в песочнице"""
        # Записываем эксперимент
        experiment_id = await self.db.save_experiment(experiment)
        
        # Мониторим прогресс в реальном времени
        async for update in self._monitor_experiment(experiment_id):
            await self.ws.broadcast_meta_event({
                'type': 'learning_progress',
                'experiment_id': experiment_id,
                'progress': update['progress'],
                'metrics': update['metrics']
            })
        
        # По завершении анализируем результаты
        conclusion = await self._analyze_experiment_results(experiment_id)
        
        # Предлагаем решение
        await self._suggest_experiment_conclusion(experiment_id, conclusion)
    
    async def get_evolution_graph(self, component_id: Optional[str] = None):
        """Получить граф эволюции системы или конкретного компонента"""
        if component_id:
            return await self._build_component_evolution(component_id)
        else:
            return await self._build_system_evolution()
    
    async def get_system_predictions(self):
        """Анализировать систему и предложить улучшения"""
        predictions = []
        
        # 1. Анализ производительности
        performance_issues = await self._analyze_performance_bottlenecks()
        predictions.extend(performance_issues)
        
        # 2. Анализ кодовой базы
        code_issues = await self._analyze_code_quality()
        predictions.extend(code_issues)
        
        # 3. Анализ использования
        usage_patterns = await self._analyze_usage_patterns()
        predictions.extend(usage_patterns)
        
        # 4. Предсказание будущих потребностей
        future_needs = await self._predict_future_needs()
        predictions.extend(future_needs)
        
        return sorted(predictions, key=lambda x: x['priority'], reverse=True)
    
    async def set_autonomy_level(self, level: AutonomyLevel, rules: Dict[str, Any]):
        """Установить уровень автономности системы"""
        self.autonomy_level = level
        self.autonomy_rules = rules
        
        # Применяем правила
        await self._apply_autonomy_rules()
        
        # Уведомляем фронтенд
        await self.ws.broadcast_meta_event({
            'type': 'autonomy_level_changed',
            'level': level,
            'rules': rules
        })
    
    # Внутренние методы
    async def _scan_existing_components(self):
        """Сканирование существующего кода на предмет компонентов"""
        for file_path in Path('.').rglob('*.py'):
            if self._is_component_file(file_path):
                component = await self._analyze_component_file(file_path)
                self.component_registry[component['id']] = component
    
    def _start_file_watching(self):
        """Запуск отслеживания изменений файлов"""
        event_handler = CodeChangeHandler(self)
        self.file_watcher = Observer()
        self.file_watcher.schedule(event_handler, '.', recursive=True)
        self.file_watcher.start()
    
    async def _subscribe_to_system_events(self):
        """Подписка на события системы"""
        # Подписываемся на:
        # - Создание агентов
        # - Вызов инструментов
        # - Результаты тестов
        # - Обучение в песочнице
        pass

class CodeChangeHandler(FileSystemEventHandler):
    """Обработчик изменений файлов"""
    def __init__(self, tracker: MetaTracker):
        self.tracker = tracker
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            asyncio.create_task(
                self.tracker._handle_file_change(event.src_path)
            )
```

### 5. WebSocket менеджер для реалтайм событий

**Файл:** `backend/core/websocket_manager.py`

```python
import asyncio
import json
from typing import Dict, Set, Any
from fastapi import WebSocket

class WebSocketManager:
    """Менеджер WebSocket соединений"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            'chat': set(),
            'execution': set(),
            'meta': set()
        }
    
    async def connect(self, websocket: WebSocket, channel: str, session_id: str):
        """Подключение нового клиента"""
        await websocket.accept()
        self.active_connections[channel].add(websocket)
        
        # Отправляем текущее состояние
        await self.send_current_state(websocket, channel, session_id)
    
    async def disconnect(self, websocket: WebSocket, channel: str):
        """Отключение клиента"""
        self.active_connections[channel].discard(websocket)
    
    async def broadcast_chat_event(self, session_id: str, event: Dict[str, Any]):
        """Трансляция события чата"""
        message = json.dumps({
            'type': 'chat_event',
            'session_id': session_id,
            'data': event
        })
        
        for connection in self.active_connections['chat']:
            try:
                await connection.send_text(message)
            except:
                await self.disconnect(connection, 'chat')
    
    async def broadcast_execution_event(self, session_id: str, event: Dict[str, Any]):
        """Трансляция события исполнения"""
        message = json.dumps({
            'type': 'execution_event',
            'session_id': session_id,
            'data': event
        })
        
        for connection in self.active_connections['execution']:
            try:
                await connection.send_text(message)
            except:
                await self.disconnect(connection, 'execution')
    
    async def broadcast_meta_event(self, event: Dict[str, Any]):
        """Трансляция мета-события"""
        message = json.dumps({
            'type': 'meta_event',
            'data': event
        })
        
        for connection in self.active_connections['meta']:
            try:
                await connection.send_text(message)
            except:
                await self.disconnect(connection, 'meta')
    
    async def send_current_state(self, websocket: WebSocket, channel: str, session_id: str):
        """Отправка текущего состояния новому клиенту"""
        if channel == 'chat':
            # Отправляем историю чата
            chat_history = await get_chat_history(session_id)
            await websocket.send_text(json.dumps({
                'type': 'initial_state',
                'data': chat_history
            }))
        
        elif channel == 'execution':
            # Отправляем текущий граф исполнения
            execution_graph = await get_execution_graph(session_id)
            await websocket.send_text(json.dumps({
                'type': 'initial_state',
                'data': execution_graph
            }))
        
        elif channel == 'meta':
            # Отправляем мета-данные системы
            system_metrics = await get_system_metrics()
            evolution_timeline = await get_evolution_timeline()
            await websocket.send_text(json.dumps({
                'type': 'initial_state',
                'data': {
                    'metrics': system_metrics,
                    'timeline': evolution_timeline
                }
            }))
```

### 6. Главный файл приложения с интеграцией всего

**Файл:** `backend/main.py`

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from core.meta_tracker import MetaTracker
from core.websocket_manager import WebSocketManager
from api import chat_api, execution_api, meta_api, system_api, sandbox_api

# Глобальные объекты
meta_tracker = None
websocket_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск при старте
    global meta_tracker, websocket_manager
    
    # Инициализация
    websocket_manager = WebSocketManager()
    meta_tracker = MetaTracker(db, websocket_manager)
    
    # Запуск мета-трекера
    await meta_tracker.start()
    
    yield
    
    # Очистка при завершении
    await meta_tracker.stop()
    await db.close()

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение API роутеров
app.include_router(chat_api.router, prefix="/api/chat")
app.include_router(execution_api.router, prefix="/api/execution")
app.include_router(meta_api.router, prefix="/api/meta")
app.include_router(system_api.router, prefix="/api/system")
app.include_router(sandbox_api.router, prefix="/api/sandbox")

# WebSocket эндпоинты
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    await websocket_manager.connect(websocket, "chat", session_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Обработка сообщений от клиента
            message = json.loads(data)
            await handle_chat_message(session_id, message, websocket)
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, "chat")

@app.websocket("/ws/execution/{session_id}")
async def websocket_execution_endpoint(websocket: WebSocket, session_id: str):
    await websocket_manager.connect(websocket, "execution", session_id)
    try:
        while True:
            await websocket.receive_text()  # Клиент только слушает
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, "execution")

@app.websocket("/ws/meta")
async def websocket_meta_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket, "meta", "global")
    try:
        while True:
            await websocket.receive_text()  # Клиент только слушает
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, "meta")

# Главный обработчик сообщений чата
async def handle_chat_message(session_id: str, message: dict, websocket: WebSocket):
    """Обработка сообщения из чата - запуск всей системы"""
    
    # 1. Сохраняем сообщение пользователя
    user_message = await save_chat_message(session_id, "user", message['content'])
    
    # 2. Создаем ноду в графе исполнения
    user_node = await create_execution_node(
        session_id=session_id,
        node_type="user_input",
        data={"content": message['content']},
        chat_message_ids=[user_message.id]
    )
    
    # 3. Запускаем обработку сообщения
    # Это инициирует цепочку агентов, инструментов и т.д.
    execution_task = asyncio.create_task(
        process_user_message(session_id, message['content'], user_node.id)
    )
    
    # 4. Отправляем подтверждение
    await websocket.send_text(json.dumps({
        "type": "message_received",
        "message_id": user_message.id,
        "node_id": user_node.id
    }))
    
    # 5. Мониторим выполнение и отправляем обновления
    async for update in monitor_execution(execution_task, session_id):
        await websocket_manager.broadcast_execution_event(session_id, update)

async def process_user_message(session_id: str, content: str, user_node_id: str):
    """Основной пайплайн обработки сообщения пользователя"""
    
    # 1. Анализ сообщения (агент анализа)
    analysis_node = await create_execution_node(
        session_id=session_id,
        node_type="agent",
        data={"agent": "message_analyzer", "task": "analyze_intent"},
        parent_node_id=user_node_id
    )
    
    analysis_result = await analyze_message(content)
    await update_node_status(analysis_node.id, "success", analysis_result)
    
    # 2. Планирование (агент планировщик)
    plan_node = await create_execution_node(
        session_id=session_id,
        node_type="plan",
        data={"task": "create_execution_plan"},
        parent_node_id=analysis_node.id
    )
    
    execution_plan = await create_execution_plan(analysis_result)
    await update_node_status(plan_node.id, "success", execution_plan)
    
    # 3. Выполнение плана (цепочка агентов и инструментов)
    previous_node = plan_node
    for step in execution_plan['steps']:
        step_node = await create_execution_node(
            session_id=session_id,
            node_type=step['type'],
            data=step['data'],
            parent_node_id=previous_node.id
        )
        
        # Выполнение шага
        result = await execute_step(step)
        await update_node_status(step_node.id, "success", result)
        
        previous_node = step_node
    
    # 4. Формирование финального ответа
    response_node = await create_execution_node(
        session_id=session_id,
        node_type="response",
        data={"task": "format_final_response"},
        parent_node_id=previous_node.id
    )
    
    final_response = await format_response(
        execution_plan['steps'][-1]['result']
    )
    
    await update_node_status(response_node.id, "success", final_response)
    
    # 5. Сохраняем ответ в чат
    chat_message = await save_chat_message(
        session_id, 
        "assistant", 
        final_response['text'],
        node_id=response_node.id
    )
    
    # 6. Запускаем пост-обработку (обучение, оптимизация)
    if should_learn_from_interaction(session_id):
        await meta_tracker.track_learning_iteration({
            'session_id': session_id,
            'user_message': content,
            'system_response': final_response,
            'execution_graph': await get_execution_graph(session_id)
        })
    
    return final_response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 7. Фронтенд интеграция - главный компонент

**Файл:** `src/App.tsx`

```tsx
import React, { useState, useEffect } from 'react';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import ChatPanel from './components/ChatPanel';
import VisualizationPanel from './components/VisualizationPanel';
import MetaPanel from './components/MetaPanel';
import { useWebSocket } from './hooks/useWebSocket';
import { useSystemStore } from './stores/systemStore';

function App() {
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [isMetaPanelCollapsed, setIsMetaPanelCollapsed] = useState(false);
  
  // WebSocket соединения
  const chatWs = useWebSocket(`ws://localhost:8000/ws/chat/${currentSessionId}`);
  const executionWs = useWebSocket(`ws://localhost:8000/ws/execution/${currentSessionId}`);
  const metaWs = useWebSocket('ws://localhost:8000/ws/meta');
  
  // Глобальное состояние
  const systemMetrics = useSystemStore(state => state.metrics);
  const autonomyLevel = useSystemStore(state => state.autonomyLevel);
  const setAutonomyLevel = useSystemStore(state => state.setAutonomyLevel);

  useEffect(() => {
    // Создаем новую сессию при загрузке
    createNewSession();
  }, []);

  const createNewSession = async () => {
    const response = await fetch('/api/chat/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Новая сессия' })
    });
    const session = await response.json();
    setCurrentSessionId(session.id);
  };

  const handleSendMessage = async (content: string) => {
    // Отправляем сообщение через API
    await fetch(`/api/chat/${currentSessionId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    
    // WebSocket обновит UI автоматически
  };

  const handleStopGeneration = () => {
    fetch(`/api/chat/${currentSessionId}/stop`, { method: 'POST' });
  };

  const handleNodeClick = (nodeId: string) => {
    // При клике на ноду - показываем детали
    fetch(`/api/execution/${currentSessionId}/node/${nodeId}`)
      .then(res => res.json())
      .then(nodeDetails => {
        // Показываем модалку с деталями
        showNodeDetailsModal(nodeDetails);
      });
  };

  const handleReplayNode = (nodeId: string) => {
    // Перезапускаем ноду
    fetch(`/api/execution/${currentSessionId}/replay/${nodeId}`, {
      method: 'POST'
    });
  };

  const handleAutonomyChange = (level: AutonomyLevel) => {
    setAutonomyLevel(level);
    fetch('/api/system/autonomy/level', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level })
    });
  };

  return (
    <div className="h-screen bg-background">
      <ResizablePanelGroup direction="horizontal">
        {/* Левая панель - Чат (50%) */}
        <ResizablePanel defaultSize={50} minSize={30}>
          <ChatPanel
            sessionId={currentSessionId}
            onSendMessage={handleSendMessage}
            onStopGeneration={handleStopGeneration}
            websocket={chatWs}
          />
        </ResizablePanel>
        
        <ResizableHandle />
        
        {/* Центральная панель - Визуализация (40%) */}
        <ResizablePanel defaultSize={40} minSize={30}>
          <VisualizationPanel
            sessionId={currentSessionId}
            onNodeClick={handleNodeClick}
            onReplayNode={handleReplayNode}
            executionWebsocket={executionWs}
            metaWebsocket={metaWs}
          />
        </ResizablePanel>
        
        <ResizableHandle />
        
        {/* Правая панель - Мета-управление (10%, сворачиваемая) */}
        <ResizablePanel 
          defaultSize={10} 
          minSize={isMetaPanelCollapsed ? 5 : 10}
          maxSize={20}
        >
          <MetaPanel
            isCollapsed={isMetaPanelCollapsed}
            onToggleCollapse={() => setIsMetaPanelCollapsed(!isMetaPanelCollapsed)}
            systemMetrics={systemMetrics}
            autonomyLevel={autonomyLevel}
            onAutonomyChange={handleAutonomyChange}
            metaWebsocket={metaWs}
          />
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}

export default App;
```

### 8. Последовательность реализации

**Неделя 1: Базовый каркас**
- [ ] Мета-трекер (базовый)
- [ ] WebSocket менеджер
- [ ] REST API скелет
- [ ] Базовая структура БД

**Неделя 2: Интеграция чата**
- [ ] WebSocket для чата
- [ ] Сессии и история
- [ ] Потоковая генерация
- [ ] Связь сообщений с нодами

**Неделя 3: Граф исполнения**
- [ ] WebSocket для графа исполнения
- [ ] Ноды и связи
- [ ] Статусы и анимации
- [ ] Детали нод

**Неделя 4: Мета-система**
- [ ] Отслеживание изменений
- [ ] Верионирование
- [ ] Diff просмотр
- [ ] Граф эволюции

**Неделя 5: Управление и автономность**
- [ ] Настройки автономности
- [ ] Мониторинг метрик
- [ ] Предсказания системы
- [ ] Правила изменений

**Неделя 6: Песочница обучения**
- [ ] A/B тестирование
- [ ] Эксперименты
- [ ] Анализ результатов
- [ ] Авто-принятие решений

**Неделя 7: Оптимизация и финальная интеграция**
- [ ] Производительность
- [ ] Обработка ошибок
- [ ] Безопасность
- [ ] Документация

### 9. Ключевые особенности этой реализации:

1. **Полная интеграция**: Чат, визуализация и управление работают как единая система
2. **Реалтайм обновления**: WebSocket для мгновенных обновлений
3. **Мета-осведомленность**: Система знает о себе всё и может это показать
4. **Контроль автономности**: От полного ручного управления до полной автономности
5. **Обучение в продакшене**: Песочница для безопасного тестирования изменений
6. **Эволюция в реальном времени**: Видите как система меняется прямо на глазах

Эта архитектура превращает вашу самоэволюционирующую систему из "черного ящика" в полностью прозрачную, управляемую и самооптимизирующуюся платформу, где каждый аспект работы виден и контролируем.