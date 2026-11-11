# JEV SMART ROUTER

Prova de conceito: uma mensagem de cliente é classificada pelo JEV em categoria e prioridade; o Python usa a categoria escolhida para encaminhá-la à fila correta.

> **JEV julga. Python executa o roteamento.**

## Pré-requisitos

- Python 3.11+
- Node.js 20+
- Uma chave da TypeSafe AI

## Configuração

Na raiz do projeto, edite `.env` e informe somente a chave:

```env
TYPESAFE_API_KEY=sua_chave_aqui
JEV_MODEL=jev-latest
JEV_TIMEOUT_SECONDS=20
MAX_REAL_JEV_CALLS=20
```

O arquivo `.env` está ignorado pelo Git e a chave nunca é enviada ao frontend.

## Backend

No PowerShell, a partir da raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r apps\backend\requirements-dev.txt
python -m uvicorn app.main:app --app-dir apps\backend --reload
```

O backend estará em `http://localhost:8000`. A saúde pode ser verificada em `http://localhost:8000/health`.

## Frontend

Em outro terminal:

```powershell
cd apps\frontend
npm install
npm run dev
```

Abra `http://localhost:5173`.

## Primeira chamada real

1. Coloque `TYPESAFE_API_KEY` no `.env` da raiz.
2. Inicie backend e frontend com os comandos acima.
3. Abra `http://localhost:5173`.
4. Digite ou escolha uma mensagem de exemplo.
5. Clique **ANALISAR COM JEV**.

Nenhuma chamada é feita ao carregar a aplicação ou ao selecionar um exemplo. Não há retry automático. O processo aceita no máximo `MAX_REAL_JEV_CALLS` chamadas reais desde a inicialização.

## Testes e build

```powershell
python -m pytest apps\backend\tests -q
cd apps\frontend
npm run typecheck
npm run build
```

## API

`POST /api/analyze`

```json
{ "message": "Meu cartão foi clonado." }
```

O backend cria o state `{ "customer_message": "..." }`, envia duas `Choice` ao JEV e mapeia a categoria para uma das filas `FILA_FRAUDE`, `FILA_SUPORTE`, `FILA_COMERCIAL` ou `FILA_CANCELAMENTO`.
