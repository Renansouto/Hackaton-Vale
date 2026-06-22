# Don't Go Analyzer — Apontamentos + Telemetria

Aplicação Streamlit para carregar, validar, tratar, cruzar e analisar bases de **apontamentos operacionais**, **telemetria** e eventos **Don’t Go**.

O projeto foi desenhado como um **MVP funcional**, mas com arquitetura modular para evoluir para um produto analítico completo.

## 1. Arquitetura proposta

```text
project/
│
├── app.py
├── requirements.txt
├── README.md
│
├── src/
│   ├── config.py
│   ├── loaders.py
│   ├── validators.py
│   ├── preprocessing.py
│   ├── metrics.py
│   ├── telemetry_analysis.py
│   ├── apontamentos_analysis.py
│   ├── dontgo_analysis.py
│   ├── feature_engineering.py
│   ├── modeling.py
│   ├── visualizations.py
│   ├── reports.py
│   └── utils.py
│
├── data/
│   ├── raw/
│   ├── silver/
│   └── gold/
│
├── outputs/
│   ├── reports/
│   ├── exports/
│   └── figures/
│
└── tests/
    ├── test_loaders.py
    ├── test_validators.py
    └── test_metrics.py
```

### Principais decisões técnicas

- **Streamlit**: interface web rápida para upload, filtros e dashboards.
- **DuckDB**: consulta Parquets grandes diretamente, sem carregar tudo em Pandas.
- **Pandas**: manipulação de tabelas menores, principalmente apontamentos e agregações.
- **Plotly**: gráficos interativos.
- **OpenPyXL / XlsxWriter**: leitura e exportação Excel.
- **PyArrow**: suporte a Parquet.
- **Scikit-learn**: baseline exploratório de modelo preditivo.
- **ReportLab**: relatório executivo PDF.

## 2. Arquivos aceitos

A aplicação aceita upload múltiplo de:

- `README.md`
- Dicionário de dados em Excel
- Apontamentos em `.xlsx`
- Apontamentos brutos em `.parquet`
- Exemplo/referência de Don’t Go em `.xlsx`
- Telemetria mensal em `.parquet`, como:
  - `telemetry_jan.parquet`
  - `telemetry_feb.parquet`
  - `telemetry_mar.parquet`
  - `telemetry_abr.parquet`
  - `telemetry_may.parquet`
  - `telemetry_jun.parquet`
  - futuros arquivos no mesmo padrão

O reconhecimento do tipo de arquivo é automático pelo nome/extensão.

## 3. Como executar

### Passo 1 — Criar ambiente virtual

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

No Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

### Passo 2 — Instalar dependências

```bash
pip install -r requirements.txt
```

### Passo 3 — Rodar o Streamlit

```bash
streamlit run app.py
```

### Passo 4 — Anexar os arquivos

Use o uploader na barra lateral para enviar todos os arquivos necessários.

Alternativa: coloque os arquivos diretamente em:

```text
data/raw/
```

Depois clique em **Recarregar data/raw** na barra lateral.

## 4. Como interpretar as páginas

### Página Inicial
Mostra o objetivo do app, arquivos necessários e status dos uploads.

### Diagnóstico dos Dados
Exibe registros, colunas, tipos, período de datas, nulos, duplicidades e problemas de schema.

### Dicionário de Dados
Compara o dicionário com as colunas reais das bases carregadas.

### Apontamentos
Mostra KPIs, filtros, gráficos por mês, classe, tipo, equipamentos, duração e Pareto.

### Telemetria
Consulta os Parquets mensais como uma base histórica única, com KPIs e gráficos de eventos.

### Don’t Go
Filtra `Is_Dont_Go = 1`, gera rankings e permite investigar a linha do tempo de um evento específico.

### Cruzamento
Cruza apontamentos e telemetria usando TAG e janelas antes/durante/depois do apontamento.

### Engenharia de Features
Gera dataset analítico para investigação e evolução de modelo preditivo.

### Modelo Preditivo
Treina um baseline exploratório a partir de uma base equipamento-hora.

### Relatórios e Exportações
Exporta tabelas em Excel/CSV/Parquet e gera relatório PDF executivo.

## 5. Observações importantes

- O app preserva a privacidade de operadores anonimizados.
- O app não tenta reidentificar operadores.
- Rankings e precursores são **hipóteses analíticas**, não conclusões causais automáticas.
- Para produção, valide regras com operação, manutenção, despacho e especialistas de processo.

## 6. Melhorias futuras

- Banco de dados central com DuckDB/SQLite/PostgreSQL.
- Jobs agendados para atualização automática.
- Integração com Power BI.
- Deploy web com autenticação.
- Controle de usuários e perfis.
- Monitoramento automático de novas telemetrias.
- Alertas operacionais por e-mail/Teams.
- Modelo preditivo com validação temporal, explicabilidade e MLOps.
