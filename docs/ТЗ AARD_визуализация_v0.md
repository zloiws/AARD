

##  Метасознающая визуализация

Поскольку код сам генерирует агентов/инструменты, нам нужно визуализировать не только **исполнение**, но и **эволюцию** системы.

### 1. Создаем систему мета-отслеживания

**Файл:** `src/core/meta_tracker.py`

**Промпт:**
```
Создай систему, которая отслеживает ВСЕ изменения в коде и архитектуре в реальном времени. Она должна:

1. Хукнуть в систему контроля версий кода (как Git, но для рантайма):
   - Каждый созданный/измененный файл
   - Каждое изменение класса/функции
   - Каждый новый агент/инструмент

2. Создавать "снимки" (snapshots) системы в ключевые моменты:
   - После генерации промпта
   - После создания плана
   - После написания кода агента
   - После тестирования
   - После обучения в песочнице
   - После применения изменений

3. Формировать граф эволюции, где:
   - Ноды: версии компонентов (Agent_v1, Agent_v2, Tool_v1)
   - Ребра: отношения ("порождено из", "исправлено после теста", "оптимизировано")

4. Пример структуры события мета-изменения:
```python
{
  "event_id": "gen_001",
  "timestamp": "2024-01-01T12:00:00Z",
  "type": "agent_generation",
  "trigger": {
    "prompt_id": "prompt_001",
    "prompt_text": "Создай агента для анализа рынка..."
  },
  "input": {
    "context": "Существующие агенты: research_agent, data_agent",
    "requirements": "Должен уметь анализировать тренды"
  },
  "output": {
    "generated_code": {
      "file": "agents/market_analyzer_v1.py",
      "class": "MarketAnalyzerAgent",
      "methods": ["analyze_trends", "collect_data"],
      "dependencies": ["pandas", "yfinance"]
    },
    "explanation": "Агент создан с фокусом на финансовый анализ..."
  },
  "metadata": {
    "confidence_score": 0.87,
    "generation_time": 12.5,
    "model_used": "claude-3-opus"
  }
}
```

5. Интегрировать с существующим бэкендом так, чтобы КАЖДОЕ действие системы записывалось в журнал эволюции.
```

### 2. Визуализация двухуровневой системы

Теперь нам нужно показывать **два параллельных графа**:

**Файл:** `src/components/Graph/DualFlowCanvas.tsx`

**Промпт:**
```
Создай компонент двойного графа для визуализации:
1. Левый граф (исполнение): Текущий workflow (как в n8n)
2. Правый граф (эволюция): История изменений системы (как git graph)

Требования:

ГРАФ ИСПОЛНЕНИЯ (слева):
- Реальные вызовы агентов в текущей сессии
- Статусы: ожидание, выполнение, успех, ошибка
- Параметры вызовов и результаты
- Возможность "войти" в ноду и увидеть её внутренний workflow

ГРАФ ЭВОЛЮЦИИ (справа):
- Древовидная структура версий каждого компонента
- Ветвления при разных подходах (например, Agent_v1, Agent_v1_optimized)
- Теги: "после теста", "после обучения", "стабильная версия"
- Diff между версиями при клике
- Возможность откатиться к любой версии

Связь между графами:
- При клике на ноду в графе исполнения - подсвечивается её версия в графе эволюции
- При клике на версию в графе эволюции - показываются все её использования в графе исполнения

Пример компонента:
```tsx
interface DualFlowProps {
  executionGraph: ExecutionGraph;  // Текущий workflow
  evolutionGraph: EvolutionGraph;  // История изменений системы
  onVersionSelect: (componentId: string, version: string) => void;
}

const DualFlowCanvas: React.FC<DualFlowProps> = () => {
  // Split view для двух графов
  return (
    <div className="dual-graph-container">
      <ResizablePanel direction="horizontal">
        <ExecutionFlow 
          graph={executionGraph}
          onNodeClick={(node) => highlightEvolutionNode(node.componentVersion)}
        />
        <EvolutionFlow 
          graph={evolutionGraph}
          onVersionClick={(componentId, version) => showUsages(componentId, version)}
        />
      </ResizablePanel>
    </div>
  );
};
```

Добавь timeline между графами, показывающий временную ось событий.
```

### 3. API для мета-данных системы

Поскольку у вас уже есть API для всего, добавляем эндпоинты для мета-информации:

**Файл:** `backend/api/meta_api.py`

**Промпт:**
```
Расширь существующее API для поддержки мета-визуализации. Добавь эндпоинты:

1. GET /api/meta/components
   Возвращает все компоненты системы с их версиями:
   ```json
   {
     "components": {
       "MarketAnalyzerAgent": {
         "versions": {
           "v1": {
             "created_at": "2024-01-01T12:00:00Z",
             "created_by": "prompt_001",
             "file_path": "agents/market_analyzer_v1.py",
             "methods": ["analyze_trends", "collect_data"],
             "test_results": {"passed": 3, "failed": 1},
             "performance_metrics": {"avg_response_time": 2.3}
           },
           "v2": {
             "created_at": "2024-01-02T10:30:00Z",
             "created_by": "test_feedback_001",
             "changes": ["optimized analyze_trends method", "added caching"],
             "diff_url": "/api/meta/components/MarketAnalyzerAgent/diff/v1/v2"
           }
         },
         "current_version": "v2",
         "usage_count": 47,
         "last_used": "2024-01-03T15:45:00Z"
       }
     }
   }
   ```

2. GET /api/meta/evolution-timeline
   Хронология всех значимых событий:
   ```json
   [
     {
       "timestamp": "2024-01-01T12:00:00Z",
       "type": "agent_generation",
       "component": "MarketAnalyzerAgent",
       "version": "v1",
       "trigger": "user_prompt",
       "confidence": 0.87
     },
     {
       "timestamp": "2024-01-01T14:30:00Z",
       "type": "test_execution",
       "component": "MarketAnalyzerAgent",
       "version": "v1",
       "result": "failed",
       "feedback": "слишком медленный на больших данных"
     },
     {
       "timestamp": "2024-01-02T10:30:00Z",
       "type": "self_optimization",
       "component": "MarketAnalyzerAgent",
       "from_version": "v1",
       "to_version": "v2",
       "improvements": ["добавлено кэширование", "оптимизированы запросы"]
     }
   ]
   ```

3. WebSocket /ws/meta-events
   Реалтайм события о самоизменении системы:
   - "agent_generated"
   - "code_modified"
   - "test_completed"
   - "learning_iteration"
   - "version_promoted"

4. GET /api/meta/dependency-graph
   Полный граф зависимостей между всеми компонентами всех версий.

5. POST /api/meta/rollback/{component}/{version}
   Откат компонента к указанной версии (только для админов).
```

### 4. Адаптивные ноды, которые меняются в реальном времени

**Файл:** `src/components/Nodes/LiveNode.tsx`

**Промпт:**
```
Создай компонент ноды, который ОТРАЖАЕТ реальное состояние компонента в системе:

1. Внешний вид ноды зависит от:
   - Версии компонента (цвет рамки)
   - Статуса (выполняется, успех, ошибка, устарел)
   - Популярности (размер ноды)
   - Качества (прозрачность/насыщенность)

2. В реальном времени показывать:
   - Текущие метрики (загрузка CPU, память, latency)
   - Счетчик вызовов в текущей сессии
   - Последний результат (успех/ошибка)

3. Контекстное меню ноды:
   - "Показать исходный код этой версии"
   - "Сравнить с другими версиями"
   - "Запустить тесты для этого компонента"
   - "Оптимизировать этот компонент" (отправляет запрос системе на self-improvement)
   - "Заморозить версию" (предотвращает авто-изменения)

4. Анимации:
   - Пульсация при активном использовании
   - Мигание при изменении версии
   - Плавное увеличение при улучшении метрик

5. Пример LiveNode:
```tsx
interface LiveNodeProps {
  node: ExecutionNode;
  metaData: ComponentMeta;
  realtimeMetrics: NodeMetrics;
  onAction: (action: NodeAction) => void;
}

const LiveNode: React.FC<LiveNodeProps> = ({ node, metaData, realtimeMetrics }) => {
  const versionColor = getVersionColor(metaData.current_version);
  const status = getNodeStatus(node);
  
  return (
    <div 
      className={`live-node ${status}`}
      style={{ borderColor: versionColor, opacity: metaData.confidence_score }}
    >
      <div className="node-header">
        <span className="node-icon">{getIcon(node.type)}</span>
        <span className="node-name">{node.name}</span>
        <span className="node-version-badge">v{metaData.current_version}</span>
        <span className="node-metrics">
          {realtimeMetrics.calls}/s | {realtimeMetrics.avg_latency}ms
        </span>
      </div>
      
      <div className="node-body">
        <div className="node-description">{metaData.description}</div>
        
        <div className="node-evolution">
          <div className="evolution-timeline">
            {metaData.versions.map(v => (
              <div 
                key={v.version}
                className={`version-dot ${v.version === metaData.current_version ? 'active' : ''}`}
                title={`v${v.version}: ${v.changes_summary}`}
              />
            ))}
          </div>
          <button onClick={() => onAction('show_evolution')}>
            История изменений
          </button>
        </div>
        
        {node.is_executing && (
          <div className="execution-progress">
            <ProgressBar value={node.progress} />
            <span>Выполняется...</span>
          </div>
        )}
      </div>
      
      <NodeHandles node={node} />
    </div>
  );
};
```

Добавь тултипы с подробной информацией при наведении.
```

### 5. Dashboard эволюции системы

**Файл:** `src/components/Dashboard/EvolutionDashboard.tsx`

**Промпт:**
```
Создай дашборд, который показывает общую картину эволюции ВСЕЙ системы:

1. Основные метрики:
   - Всего компонентов (агентов/инструментов)
   - Активных версий / устаревших
   - Общее количество авто-изменений
   - Коэффициент улучшения (среднее улучшение метрик после оптимизации)
   - Уровень автономности системы (% решений принятых системой самостоятельно)

2. Графики:
   - Timeline эволюции (когда что создавалось/менялось)
   - График качества системы по времени (по результатам тестов)
   - График сложности системы (количество зависимостей, LOC)
   - Heatmap наиболее часто изменяемых компонентов

3. Список недавних само-изменений:
   - Компонент, что изменилось, почему (какой промпт/тест/ошибка спровоцировала)
   - Результат изменения (улучшение/ухудшение)
   - Возможность отката

4. Прогностические элементы:
   - "Система предлагает оптимизировать X, ожидаемое улучшение: 15%"
   - "Обнаружена избыточность: компоненты A и B можно объединить"
   - "Рекомендуется создать новый компонент для паттерна Y"

5. Контроль автономности:
   - Слайдер: "Уровень авто-изменений" (от "только с подтверждением" до "полная автономность")
   - Белый/черный список компонентов для авто-изменений
   - Правила: "Не трогать компоненты старше N дней без тестов"

Пример дашборда:
```tsx
const EvolutionDashboard: React.FC = () => {
  const { systemMetrics, recentChanges, predictions } = useSystemEvolution();
  
  return (
    <div className="evolution-dashboard">
      <div className="metrics-grid">
        <MetricCard 
          title="Автономность" 
          value={`${systemMetrics.autonomy_level}%`}
          trend={systemMetrics.autonomy_trend}
          description="Уровень самостоятельных решений системы"
        />
        <MetricCard 
          title="Скорость эволюции" 
          value={`${systemMetrics.changes_per_day}/день`}
          description="Среднее количество авто-изменений в день"
        />
        <MetricCard 
          title="Качество системы" 
          value={systemMetrics.quality_score}
          description="Средний результат по всем тестам"
        />
        <MetricCard 
          title="Стабильность" 
          value={`${systemMetrics.stability}%`}
          description="% изменений без регрессии"
        />
      </div>
      
      <div className="charts-section">
        <EvolutionTimelineChart events={systemMetrics.timeline} />
        <QualityTrendChart data={systemMetrics.quality_trend} />
      </div>
      
      <div className="recent-changes">
        <h3>Последние само-изменения</h3>
        {recentChanges.map(change => (
          <ChangeItem 
            key={change.id}
            change={change}
            onRevert={() => handleRevert(change)}
            onApprove={() => handleApprove(change)}
          />
        ))}
      </div>
      
      <div className="predictions">
        <h3>Предложения системы</h3>
        {predictions.map(prediction => (
          <PredictionItem 
            key={prediction.id}
            prediction={prediction}
            onExecute={() => executePrediction(prediction)}
            onIgnore={() => ignorePrediction(prediction)}
          />
        ))}
      </div>
    </div>
  );
};
```

Добавь фильтры по времени, типу компонентов, типу изменений.
```

### 6. Интеграция с песочницей самообучения

**Файл:** `src/components/Sandbox/SandboxVisualizer.tsx`

**Промпт:**
```
Создай визуализатор песочницы самообучения, которая показывает:

1. Текущий эксперимент:
   - Что тестируется (новая версия компонента vs старая)
   - Параметры теста
   - Прогресс выполнения

2. В реальном времени:
   - График learning curve
   - Сравнение метрик версий
   - Логи принятия решений

3. По завершении:
   - Статистическая значимость различий
   - Рекомендация (принять/отклонить изменения)
   - Дифф изменений

4. Возможность запустить A/B тест:
   - Выбрать две версии компонента
   - Настроить тестовые данные
   - Запустить параллельное выполнение
   - Автоматический выбор победителя

Пример:
```tsx
const SandboxVisualizer: React.FC<{ experiment: Experiment }> = ({ experiment }) => {
  return (
    <div className="sandbox-visualizer">
      <div className="experiment-header">
        <h3>Эксперимент: {experiment.name}</h3>
        <div className="version-comparison">
          <VersionCard version={experiment.version_a} is_control={true} />
          <VSIcon />
          <VersionCard version={experiment.version_b} is_test={true} />
        </div>
      </div>
      
      <div className="metrics-comparison">
        {experiment.metrics.map(metric => (
          <ComparisonBar 
            key={metric.name}
            metric={metric}
            value_a={experiment.results_a[metric.name]}
            value_b={experiment.results_b[metric.name]}
            higher_is_better={metric.higher_is_better}
          />
        ))}
      </div>
      
      <div className="learning-curve">
        <LineChart 
          data={experiment.learning_data}
          series={['version_a', 'version_b']}
          title="Learning Curve"
        />
      </div>
      
      <div className="conclusion">
        {experiment.conclusion && (
          <>
            <h4>Вывод системы:</h4>
            <div className={`conclusion-text ${experiment.conclusion.recommendation}`}>
              {experiment.conclusion.text}
              <br />
              <strong>Уверенность: {experiment.conclusion.confidence}%</strong>
            </div>
            <button onClick={() => applyConclusion(experiment.conclusion)}>
              Применить изменения
            </button>
          </>
        )}
      </div>
    </div>
  );
};
```

Добавь возможность создавать новые эксперименты из интерфейса.
```

## Ключевые преимущества этого подхода:

1. **Полная прозрачность**: Видите не только ЧТО делает система, но и КАК она меняется
2. **Контроль над автономностью**: Регулируете уровень самостоятельности системы
3. **Обучение на визуализации**: Понимаете паттерны успешных/неуспешных изменений
4. **Проактивное управление**: Предсказываете будущие изменения и направляете их

## Как начать внедрять:

1. **Сначала** создайте `meta_tracker.py` и добавьте логирование всех само-изменений
2. **Затем** расширьте API для предоставления мета-данных
3. **Параллельно** создайте базовый `DualFlowCanvas` с двумя графами
4. **Постепенно** добавляйте фичи: дашборд, песочницу, прогнозы

Ваша система уникальна тем, что она **рефлексивна** - она может анализировать и изменять сама себя. Визуализация должна отражать эту рефлексивность, показывая не только текущее состояние, но и процесс само-трансформации.