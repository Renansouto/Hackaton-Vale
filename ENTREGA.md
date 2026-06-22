# Entrega — Execução do Prompt

## PARTE 1 — Arquitetura do software

O software foi estruturado como uma aplicação analítica modular em Python, com interface em Streamlit e processamento pesado via DuckDB.

### Camadas principais

1. **Interface (`app.py`)**
   - Upload múltiplo de arquivos.
   - Navegação lateral por páginas.
   - Filtros, KPIs, gráficos e botões de exportação.

2. **Leitura e organização (`src/loaders.py`)**
   - Classificação automática dos arquivos.
   - Leitura de Excel.
   - Consulta de Parquet com DuckDB.
   - Registro dos arquivos carregados.

3. **Validação (`src/validators.py`)**
   - Diagnóstico de colunas, tipos, nulos, duplicidades e períodos.
   - Comparação com dicionário de dados.
   - Validação de colunas mínimas por base.

4. **Tratamento (`src/preprocessing.py`)**
   - Conversão de datas.
   - Cálculo de duração dos apontamentos.
   - Filtros e padronizações.
   - Proteção de privacidade para operadores anonimizados.

5. **Análises (`src/*_analysis.py`)**
   - Apontamentos.
   - Telemetria.
   - Don’t Go.
   - Cruzamento temporal entre apontamentos e telemetria.

6. **Features e modelo (`src/feature_engineering.py`, `src/modeling.py`)**
   - Dataset de features para eventos Don’t Go.
   - Dataset equipamento-hora.
   - Baseline exploratório com Random Forest.

7. **Visualizações e relatórios (`src/visualizations.py`, `src/reports.py`)**
   - Gráficos Plotly.
   - Exportação Excel/CSV/Parquet.
   - Relatório PDF executivo.

### Por que essas tecnologias

- **Streamlit**: cria interface profissional rapidamente, ideal para MVP analítico.
- **DuckDB**: consulta arquivos Parquet grandes sem carregar 100% em memória.
- **Pandas**: ótimo para agregações menores e manipulação tabular.
- **Plotly**: gráficos interativos com filtros e hover.
- **Scikit-learn**: baseline preditivo simples e interpretável.
- **ReportLab/XlsxWriter**: geração de relatórios e exportações.

## PARTE 2 — requirements.txt

O arquivo `requirements.txt` foi criado na raiz do projeto com:

```text
streamlit
pandas
numpy
duckdb
polars
pyarrow
openpyxl
xlsxwriter
plotly
scikit-learn
reportlab
pydantic
python-dateutil
```

## PARTE 3 — Código principal app.py

O arquivo `app.py` contém:

- Configuração do layout Streamlit.
- Upload múltiplo de arquivos.
- Reconhecimento automático de arquivos.
- Páginas:
  - Página Inicial
  - Diagnóstico dos Dados
  - Dicionário de Dados
  - Apontamentos
  - Telemetria
  - Don’t Go
  - Cruzamento
  - Engenharia de Features
  - Modelo Preditivo
  - Relatórios e Exportações

## PARTE 4 — Módulos auxiliares

Foram criados os módulos dentro de `src/`:

- `config.py`
- `loaders.py`
- `validators.py`
- `preprocessing.py`
- `metrics.py`
- `telemetry_analysis.py`
- `apontamentos_analysis.py`
- `dontgo_analysis.py`
- `feature_engineering.py`
- `modeling.py`
- `visualizations.py`
- `reports.py`
- `utils.py`

Também foram adicionados testes básicos em `tests/`.

## PARTE 5 — Como executar

### 1. Criar ambiente virtual

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Rodar o Streamlit

```bash
streamlit run app.py
```

### 4. Anexar os arquivos

Pelo uploader lateral, envie:

- README.md
- Dicionário de Dados Excel
- Apontamentos `.xlsx` ou `.parquet`
- Don’t Go `.xlsx`
- Arquivos mensais de telemetria `.parquet`

Alternativamente, coloque os arquivos em `data/raw/` e clique em **Recarregar data/raw**.

### 5. Interpretar as páginas

- **Diagnóstico**: valide schema e período.
- **Apontamentos**: avalie volume, duração, classes e equipamentos.
- **Telemetria**: avalie eventos, alarmes, criticidades, localidade e heatmap.
- **Don’t Go**: investigue eventos críticos e sua linha do tempo.
- **Cruzamento**: identifique eventos antes/durante/depois dos apontamentos.
- **Features**: gere dataset analítico.
- **Modelo**: rode baseline exploratório, não produtivo.
- **Relatórios**: exporte Excel/CSV/Parquet/PDF.

## PARTE 6 — Melhorias futuras

- Banco de dados central com PostgreSQL, DuckDB persistido ou Lakehouse.
- Agendamento de atualização por Airflow, Prefect ou cron.
- Integração com Power BI.
- Deploy web com autenticação.
- Controle de usuários e permissões.
- Monitoramento automático de novos arquivos.
- Alertas operacionais via Teams/e-mail.
- MLOps para modelo preditivo em produção.
- Explicabilidade com SHAP.
- Validação operacional dos alarmes precursores.

## MVP entregue

O MVP cobre:

1. Upload dos arquivos.
2. Leitura de Parquets com DuckDB.
3. Diagnóstico dos dados.
4. KPIs de apontamentos.
5. KPIs de telemetria.
6. KPIs de Don’t Go.
7. Gráficos principais.
8. Cruzamento básico entre apontamentos e telemetria.
9. Exportação de tabelas.
10. Geração inicial de features e baseline exploratório.
