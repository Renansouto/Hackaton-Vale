from pathlib import Path
import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"

APONT = DATA_DIR / "desenvolver_apontamentos.parquet"
TELE_FILES = sorted(DATA_DIR.glob("telemetry_*.parquet"))

print("Projeto:", PROJECT_ROOT)
print("Dados:", DATA_DIR)

if not DATA_DIR.exists():
    raise FileNotFoundError(f"Pasta não existe: {DATA_DIR}")

if not APONT.exists():
    raise FileNotFoundError(
        f"Não achei: {APONT}\nArquivos em data/raw:\n" +
        "\n".join([p.name for p in DATA_DIR.iterdir()])
    )

if len(TELE_FILES) == 0:
    raise FileNotFoundError(
        "Não achei telemetry_*.parquet em data/raw.\nArquivos:\n" +
        "\n".join([p.name for p in DATA_DIR.iterdir()])
    )

con = duckdb.connect(database=":memory:")

print("\n=== INVENTÁRIO ===")
print(f"{APONT.name:28s} | {APONT.stat().st_size/1e6:10.1f} MB")
for f in TELE_FILES:
    print(f"{f.name:28s} | {f.stat().st_size/1e6:10.1f} MB")

# Detectar colunas principais na Telemetria
tele_desc = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{str(TELE_FILES[0])}')").fetchdf()
cols = tele_desc["column_name"].tolist()
lower_map = {c.lower(): c for c in cols}

def pick(*names):
    for n in names:
        if n.lower() in lower_map:
            return lower_map[n.lower()]
    return None

Data_Evento = pick("Data_Evento", "data_evento")
TAG = pick("TAG", "Tag", "tag")
Is_Dont_Go = pick("Is_Dont_Go", "is_dont_go", "IsDontGo")

if Data_Evento is None or TAG is None or Is_Dont_Go is None:
    raise ValueError(f"Colunas esperadas não encontradas na telemetria.\nDisponíveis: {cols}")

print("\n=== COLUNAS DETECTADAS (Telemetria) ===")
print({"Data_Evento": Data_Evento, "TAG": TAG, "Is_Dont_Go": Is_Dont_Go})

# 1) Datas por arquivo mensal (pega erro proposital “mês errado”)
print("\n=== CHECAGEM DE DATAS POR ARQUIVO (Telemetria) ===")
rows = []
for f in TELE_FILES:
    q = f"""
    SELECT
      '{f.name}' AS arquivo,
      COUNT(*) AS n,
      MIN("{Data_Evento}") AS min_data,
      MAX("{Data_Evento}") AS max_data,
      COUNT(DISTINCT "{TAG}") AS tags_unicas,
      SUM(CASE WHEN "{Is_Dont_Go}"=1 THEN 1 ELSE 0 END) AS dontgo
    FROM read_parquet('{str(f)}')
    """
    rows.append(con.execute(q).fetchdf())

dates_df = pd.concat(rows, ignore_index=True)
print(dates_df)

# 2) Checagem temporal de Apontamentos (Inicio > Fim, duração <= 0)
ap_desc = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{str(APONT)}')").fetchdf()
ap_cols = ap_desc["column_name"].tolist()
ap_map = {c.lower(): c for c in ap_cols}
Inicio = ap_map.get("inicio")
Fim = ap_map.get("fim")

if Inicio is None or Fim is None:
    raise ValueError(f"Não encontrei Inicio/Fim em apontamentos.\nDisponíveis: {ap_cols}")

print("\n=== APONTAMENTOS: CHECAGEM TEMPORAL ===")
q = f"""
SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN "{Inicio}" > "{Fim}" THEN 1 ELSE 0 END) AS inicio_maior_fim,
  SUM(CASE WHEN date_diff('second', "{Inicio}", "{Fim}") <= 0 THEN 1 ELSE 0 END) AS duracao_nao_positiva
FROM read_parquet('{str(APONT)}')
"""
ap_check = con.execute(q).fetchdf()
print(ap_check)

# Exportar evidências para relatório
out = PROJECT_ROOT / "reports"
out.mkdir(exist_ok=True)

dates_df.to_csv(out / "telemetria_datas_por_arquivo.csv", index=False)
ap_check.to_csv(out / "apontamentos_cheque_temporal.csv", index=False)

print(f"\n✅ CSVs gerados em: {out.resolve()}")