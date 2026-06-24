from pathlib import Path
import duckdb

ROOT = Path(".")
DATA = ROOT / "data" / "raw"

con = duckdb.connect(database=":memory:")

telemetry = str(DATA / "telemetry_*.parquet")

print("\n🔍 Verificando duplicados nos dados brutos...\n")

# ------------------------------
# TOTAL DE LINHAS
# ------------------------------
total = con.execute(f"""
SELECT COUNT(*) FROM read_parquet('{telemetry}')
""").fetchone()[0]

# ------------------------------
# TOTAL DISTINCT (sem duplicados)
# ------------------------------
distinct = con.execute(f"""
SELECT COUNT(DISTINCT (TAG, Data_Evento)) 
FROM read_parquet('{telemetry}')
""").fetchone()[0]

# ------------------------------
# DUPLICADOS
# ------------------------------
dups = total - distinct

print(f"Total de linhas: {total:,}".replace(",", "."))
print(f"Linhas únicas: {distinct:,}".replace(",", "."))
print(f"Duplicados: {dups:,}".replace(",", "."))

# ------------------------------
# TOP EXEMPLOS DE DUPLICADOS
# ------------------------------
print("\n📊 Exemplos de duplicados:")

dup_samples = con.execute(f"""
SELECT 
    TAG,
    Data_Evento,
    COUNT(*) as qtd
FROM read_parquet('{telemetry}')
GROUP BY TAG, Data_Evento
HAVING COUNT(*) > 1
ORDER BY qtd DESC
LIMIT 10
""").fetchdf()

print(dup_samples)