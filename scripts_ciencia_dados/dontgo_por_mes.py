from pathlib import Path
import duckdb
import pandas as pd

# caminhos
ROOT = Path(".")
DATA = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# arquivos
files = sorted(DATA.glob("telemetry_*.parquet"))

# conexão
con = duckdb.connect(database=":memory:")

# criar query unindo todos os meses
union_all = " UNION ALL ".join(
    [f"SELECT * FROM read_parquet('{str(f)}')" for f in files]
)

# agregação por mês
query = f"""
SELECT
    DATE_TRUNC('month', Data_Evento) AS mes,
    COUNT(*) AS total_eventos,
    SUM(CASE WHEN Is_Dont_Go = 1 THEN 1 ELSE 0 END) AS dontgo,
    SUM(CASE WHEN Is_Dont_Go = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS taxa_dontgo
FROM ({union_all})
GROUP BY 1
ORDER BY 1
"""

df = con.execute(query).fetchdf()

print("\n=== DON'T GO POR MÊS ===")
print(df)

# salvar resultado
df.to_csv(REPORTS / "eda_dontgo_por_mes.csv", index=False)

print(f"\n✅ Resultado salvo em: {REPORTS.resolve()}")
