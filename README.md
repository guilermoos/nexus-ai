# AI Connector Platform

Middleware/Orquestrador agnóstico de modelos (LLMs) para Function Calling padronizado.

## Arquitetura

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   LLMs      │────▶│  Orchestrator    │────▶│  WebApps    │
│ (OpenAI,    │     │  (FastAPI)       │     │  (Tools)    │
│  Ollama)    │◀────│  - Validação     │◀────│             │
└─────────────┘     │  - Roteamento    │     └─────────────┘
                    │  - Adapters      │
                    └──────────────────┘
```

## Estrutura do Projeto

```
/workspace
├── core/              # Orquestrador principal
│   ├── main.py        # Servidor FastAPI + lógica de orquestração
│   └── adapters.py    # Adaptadores para diferentes LLMs
├── sdk/               # SDK para desenvolvedores
│   ├── __init__.py    # Exportações
│   └── decorators.py  # Decorador @tool
└── demos/             # Aplicações de demonstração
    ├── weather_app.py # Demo: API de clima
    └── math_app.py    # Demo: Operações matemáticas
```

## Instalação

```bash
# Instalar dependências
pip install fastapi uvicorn pydantic httpx python-dotenv

# Ou usar o gerenciador de pacotes moderno UV:
uv pip install -e .
```

## Uso Rápido

### 1. Iniciar o Orchestrator

```bash
cd /workspace
python core/main.py
# Roda em http://localhost:8000
```

### 2. Iniciar um WebApp Demo

```bash
# Terminal separado
python demos/weather_app.py
# Roda em http://localhost:8001

# Outro terminal
python demos/math_app.py
# Roda em http://localhost:8002
```

### 3. Criar Seu Próprio WebApp

```python
from fastapi import FastAPI
from sdk.decorators import tool

app = FastAPI()

@tool
def minha_funcao(param: str) -> str:
    """Descrição do que a função faz."""
    return f"Resultado: {param}"

@app.post("/execute/minha_funcao")
async def execute(request: ExecuteRequest):
    result = minha_funcao(request.arguments["param"])
    return {"result": result}
```

## API Endpoints

### Orchestrator (port 8000)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/register` | POST | Registrar nova ferramenta |
| `/tools` | GET | Listar todas as ferramentas |
| `/tools/{name}` | GET | Detalhes de uma ferramenta |
| `/invoke` | POST | Executar uma ferramenta |

### Exemplo de Registro

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_weather",
    "description": "Get weather for a city",
    "parameters": {
      "type": "object",
      "properties": {"city": {"type": "string"}},
      "required": ["city"]
    },
    "app_url": "http://localhost:8001"
  }'
```

### Exemplo de Invocação

```bash
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_weather",
    "arguments": {"city": "São Paulo"}
  }'
```

## Design Patterns

### Adapter Pattern

O módulo `core/adapters.py` implementa o padrão Adapter para suportar múltiplos provedores de LLM:

- **OpenAIAdapter**: Para GPT-4, GPT-3.5 e APIs compatíveis
- **OllamaAdapter**: Para modelos locais rodando via Ollama

Cada adapter traduz:
1. Formato de tool calling do LLM → Formato padrão da plataforma
2. Ferramentas da plataforma → Formato esperado pelo LLM
3. Resultados → Formato de resposta do LLM

### SDK Minimalista

O decorador `@tool` gera automaticamente JSON Schema a partir de:
- Assinatura da função (tipos dos parâmetros)
- Docstring (descrição)

```python
@tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

# Schema gerado automaticamente:
# {
#   "name": "add",
#   "description": "Add two numbers together.",
#   "parameters": {
#     "type": "object",
#     "properties": {
#       "a": {"type": "integer"},
#       "b": {"type": "integer"}
#     },
#     "required": ["a", "b"]
#   }
# }
```

## Testes Locais com LLMs

### Com OpenAI (Cloud)

```python
from openai import OpenAI
from core.adapters import get_adapter

client = OpenAI(api_key="your-key")
adapter = get_adapter("openai")

# Obter ferramentas registradas
tools_response = requests.get("http://localhost:8000/tools")
tools = tools_response.json()["tools"]

# Format for OpenAI
formatted_tools = adapter.format_tools_for_llm(tools)

# Chat with tool support
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Qual é o clima em São Paulo?"}],
    tools=formatted_tools
)

# Parse and invoke
tool_call = adapter.parse_tool_call(response)
if tool_call["tool_name"]:
    result = requests.post(
        "http://localhost:8000/invoke",
        json=tool_call
    )
```

### Com Ollama (Local - RTX 4060 8GB)

```bash
# Instalar Ollama e baixar modelo
ollama pull llama3.1:8b  # Modelo otimizado para 8GB VRAM

# Rodar servidor
ollama serve
```

```python
import requests
from core.adapters import get_adapter

adapter = get_adapter("ollama")

# Obter ferramentas
tools_response = requests.get("http://localhost:8000/tools")
tools = tools_response.json()["tools"]

# Formatar para Ollama
formatted_tools = adapter.format_tools_for_llm(tools)

# Chamar modelo local
response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "llama3.1:8b",
        "messages": [{"role": "user", "content": "Some 15 + 27"}],
        "tools": formatted_tools
    }
)

# Processar resposta
tool_call = adapter.parse_tool_call(response.json())
```

## Próximos Passos

- [ ] Implementar registry distribuído (Redis)
- [ ] Adicionar autenticação e rate limiting
- [ ] Suporte a WebSockets para streaming
- [ ] Dashboard de monitoramento
- [ ] Mais adapters (Anthropic, Google Gemini, etc.)

## Licença

MIT
