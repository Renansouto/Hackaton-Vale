from pathlib import Path
import duckdb
import pandas as pd

# ----------------------------
# Configurações
# ----------------------------
ROOT = Path(".")
DATA = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

DELTA_HORAS = 8

# ----------------------------
# Conexão DuckDB
# ----------------------------
con = duckdb.connect(database=":memory:")

telemetry = str(DATA / "telemetry_*.parquet")

print("\n🔄 Construindo dataset com TARGET...")

# ----------------------------
# Query principal
# ----------------------------
query = f"""
WITH base AS (
    SELECT DISTINCT
        TAG,
        Data_Evento,
        Is_Dont_Go
    FROM read_parquet('{telemetry}')
),

target_calc AS (
    SELECT
        b1.TAG,
        b1.Data_Evento AS tempo_T,

        CASE
            WHEN EXISTS (
                SELECT 1
                FROM base b2
                WHERE b2.TAG = b1.TAG
                AND b2.Data_Evento > b1.Data_Evento
                AND b2.Data_Evento <= b1.Data_Evento + INTERVAL '{DELTA_HORAS} hours'
                AND b2.Is_Dont_Go = 1
            )
            THEN 1 ELSE 0
        END AS target_8h

    FROM base b1
)

SELECT DISTINCT *
FROM target_calc
"""

# ----------------------------
# Execução
# ----------------------------
df = con.execute(query).fetchdf()

print("\n✅ Preview:")
print(df.head())

# ----------------------------
# Validação de duplicados
# ----------------------------
duplicates = df.duplicated(subset=["TAG", "tempo_T"]).sum()

print("\n🔍 Checando duplicados...")
print(f"Duplicados encontrados: {duplicates}")

# ----------------------------
# Salvar dataset
# ----------------------------
output_path = REPORTS / "dataset_target_8h.csv"
df.to_csv(output_path, index=False)

print(f"\n✅ Dataset salvo em: {output_path}")
print(f"Total de linhas: {len(df):,}".replace(",", "."))

# ----------------------------
# Análise do target (balanceamento)
# ----------------------------
print("\n📊 Distribuição do target:")

dist = df["target_8h"].value_counts()
dist_pct = df["target_8h"].value_counts(normalize=True) * 100

for val in dist.index:
    print(f"{val} → {dist[val]:,} ({dist_pct[val]:.4f}%)".replace(",", "."))

print("\n✅ Processo finalizado!")