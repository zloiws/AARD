# Создание .env файла

Файл `.env` заблокирован для автоматического создания (в .gitignore).

## Создайте файл вручную:

1. Создайте файл `.env` в корне проекта `C:\work\AARD\.env`

2. Скопируйте следующий контент:

```env
# Database
POSTGRES_HOST=10.39.0.101
POSTGRES_DB=aard
POSTGRES_USER=postgres
POSTGRES_PASSWORD=Cdthrf12
POSTGRES_PORT=5432
DATABASE_URL=postgresql://postgres:Cdthrf12@10.39.0.101:5432/aard
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Ollama Instance 1 (General/Reasoning)
OLLAMA_URL_1=http://10.39.0.101:11434/v1
OLLAMA_MODEL_1=huihui_ai/deepseek-r1-abliterated:8b
OLLAMA_CAPABILITIES_1=general,reasoning,conversation
OLLAMA_MAX_CONCURRENT_1=2

# Ollama Instance 2 (Coding)
OLLAMA_URL_2=http://10.39.0.6:11434/v1
OLLAMA_MODEL_2=qwen3-coder:30b-a3b-q4_K_M
OLLAMA_CAPABILITIES_2=coding,code_generation,code_analysis
OLLAMA_MAX_CONCURRENT_2=1

# Application
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=CPY8Vwfel-0tx3snbry9X4RydZnkhv3RY-Isi2DQgFA
API_HOST=0.0.0.0
API_PORT=8000

# Features
ENABLE_AGENT_OPS=false
ENABLE_A2A=false
ENABLE_PLANNING=false
ENABLE_TRACING=false
ENABLE_CACHING=true

# Security
ALLOWED_ORIGINS=http://localhost:8000
```

3. Сохраните файл

4. Проверьте, что файл создан:
```powershell
Get-Content C:\work\AARD\.env | Select-Object -First 5
```

5. Попробуйте запустить сервер снова:
```bash
cd backend
python main.py
```

## Альтернатива: Создать через PowerShell

```powershell
cd C:\work\AARD
$content = @"
# Database
POSTGRES_HOST=10.39.0.101
POSTGRES_DB=aard
POSTGRES_USER=postgres
POSTGRES_PASSWORD=Cdthrf12
POSTGRES_PORT=5432
DATABASE_URL=postgresql://postgres:Cdthrf12@10.39.0.101:5432/aard
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Ollama Instance 1 (General/Reasoning)
OLLAMA_URL_1=http://10.39.0.101:11434/v1
OLLAMA_MODEL_1=huihui_ai/deepseek-r1-abliterated:8b
OLLAMA_CAPABILITIES_1=general,reasoning,conversation
OLLAMA_MAX_CONCURRENT_1=2

# Ollama Instance 2 (Coding)
OLLAMA_URL_2=http://10.39.0.6:11434/v1
OLLAMA_MODEL_2=qwen3-coder:30b-a3b-q4_K_M
OLLAMA_CAPABILITIES_2=coding,code_generation,code_analysis
OLLAMA_MAX_CONCURRENT_2=1

# Application
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=CPY8Vwfel-0tx3snbry9X4RydZnkhv3RY-Isi2DQgFA
API_HOST=0.0.0.0
API_PORT=8000

# Features
ENABLE_AGENT_OPS=false
ENABLE_A2A=false
ENABLE_PLANNING=false
ENABLE_TRACING=false
ENABLE_CACHING=true

# Security
ALLOWED_ORIGINS=http://localhost:8000
"@
$content | Out-File -FilePath .env -Encoding utf8 -NoNewline
```

