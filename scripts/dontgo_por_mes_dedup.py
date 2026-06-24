from pathlib import Path
import duckdb
import pandas as pd

# matplotlib para o gráfico
import matplotlib.pyplot as plt

ROOT = Path(".")
DATA = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

con = duckdb.connect(database=":memory:")
telemetry = str(DATA / "telemetry_*.parquet")

# Base DEDUP (mesma lógica do target)
query = f"""
WITH base AS (
  SELECT DISTINCT TAG, Data_Evento, Is_Dont_Go
  FROM read_parquet('{telemetry}')
)
SELECT
  DATE_TRUNC('month', Data_Evento) AS mes,
  COUNT(*) AS total_eventos,
  SUM(CASE WHEN Is_Dont_Go=1 THEN 1 ELSE 0 END) AS dontgo,
  SUM(CASE WHEN Is_Dont_Go=1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS taxa
FROM base
GROUP BY 1
ORDER BY 1
"""

df = con.execute(query).fetchdf()
df["mes"] = pd.to_datetime(df["mes"])
df["mes_str"] = df["mes"].dt.strftime("%Y-%m")

# Salvar CSV
out_csv = REPORTS / "eda_dontgo_por_mes_DEDUP.csv"
df.to_csv(out_csv, index=False)

# Gráfico: taxa (%)
plt.figure(figsize=(10, 5))
plt.plot(df["mes_str"], df["taxa"]*100, marker="o")
plt.title("Taxa de 'Don't Go' por mês (DEDUP)")
plt.xlabel("Mês")
plt.ylabel("Taxa (%)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()

out_png = REPORTS / "fig_dontgo_por_mes_taxa_DEDUP.png"
plt.savefig(out_png, dpi=200)
plt.close()

# Gráfico: quantidade
plt.figure(figsize=(10, 5))
plt.bar(df["mes_str"], df["dontgo"])
plt.title("Quantidade de 'Don't Go' por mês (DEDUP)")
plt.xlabel("Mês")
plt.ylabel("Quantidade (Is_Dont_Go=1)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()

out_png2 = REPORTS / "fig_dontgo_por_mes_qtd_DEDUP.png"
plt.savefig(out_png2, dpi=200)
plt.close()

print("✅ EDA mensal (DEDUP) gerado:")
print("-", out_csv)
print("-", out_png)
print("-", out_png2)