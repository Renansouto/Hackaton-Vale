from pathlib import Path
import duckdb
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(".")
DATA = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

con = duckdb.connect(database=":memory:")
telemetry = str(DATA / "telemetry_*.parquet")

MIN_EVENTOS = 100000
Q_LOW = 0.33
Q_HIGH = 0.66

# Base DEDUP
df = con.execute(f"""
WITH base AS (
  SELECT DISTINCT TAG, Data_Evento, Is_Dont_Go
  FROM read_parquet('{telemetry}')
)
SELECT
  TAG,
  COUNT(*) AS total_eventos,
  SUM(CASE WHEN Is_Dont_Go=1 THEN 1 ELSE 0 END) AS dontgo,
  SUM(CASE WHEN Is_Dont_Go=1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS taxa_dontgo
FROM base
GROUP BY TAG
ORDER BY dontgo DESC
""").fetchdf()

# Salvar tabela completa
out_all = REPORTS / "eda_dontgo_por_tag_DEDUP.csv"
df.to_csv(out_all, index=False)

# Top10 por quantidade
top_qtd = df.sort_values("dontgo", ascending=False).head(10).copy()
top_qtd.to_csv(REPORTS / "eda_top10_tag_quantidade_DEDUP.csv", index=False)

# Top10 por taxa (com filtro de robustez)
df_taxa = df[df["total_eventos"] >= MIN_EVENTOS].copy()
top_taxa = df_taxa.sort_values("taxa_dontgo", ascending=False).head(10).copy()
top_taxa.to_csv(REPORTS / "eda_top10_tag_taxa_DEDUP.csv", index=False)

# Quantis para Baixo/Médio/Alto (baseado em taxa)
q_low = df_taxa["taxa_dontgo"].quantile(Q_LOW)
q_high = df_taxa["taxa_dontgo"].quantile(Q_HIGH)

def class_risk(row):
    if row["total_eventos"] < MIN_EVENTOS:
        return "Volume insuficiente"
    if row["taxa_dontgo"] <= q_low:
        return "Baixo"
    elif row["taxa_dontgo"] <= q_high:
        return "Médio"
    return "Alto"

df["risco_quantis"] = df.apply(class_risk, axis=1)
df.to_csv(REPORTS / "eda_tag_risco_baixo_medio_alto_DEDUP.csv", index=False)

# ---- Gráficos ----
plt.figure(figsize=(10, 5))
plt.bar(top_qtd["TAG"].astype(str), top_qtd["dontgo"])
plt.title("Top 10 TAGs por quantidade de 'Don't Go' (DEDUP)")
plt.xlabel("TAG")
plt.ylabel("Quantidade")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(REPORTS / "fig_top10_tag_quantidade_DEDUP.png", dpi=200)
plt.close()

plt.figure(figsize=(10, 5))
plt.bar(top_taxa["TAG"].astype(str), top_taxa["taxa_dontgo"] * 100)
plt.title(f"Top 10 TAGs por taxa de 'Don't Go' (DEDUP) (mín. {MIN_EVENTOS} eventos)")
plt.xlabel("TAG")
plt.ylabel("Taxa (%)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(REPORTS / "fig_top10_tag_taxa_DEDUP.png", dpi=200)
plt.close()

plt.figure(figsize=(10, 5))
plt.hist(df_taxa["taxa_dontgo"] * 100, bins=30)
plt.title(f"Distribuição da taxa de 'Don't Go' por TAG (DEDUP) (mín. {MIN_EVENTOS} eventos)")
plt.xlabel("Taxa (%)")
plt.ylabel("Número de TAGs")
plt.tight_layout()
plt.savefig(REPORTS / "fig_hist_taxa_tag_DEDUP.png", dpi=200)
plt.close()

plt.figure(figsize=(6, 5))
plt.boxplot(df_taxa["taxa_dontgo"] * 100, vert=True)
plt.title("Boxplot da taxa de 'Don't Go' por TAG (DEDUP)")
plt.ylabel("Taxa (%)")
plt.tight_layout()
plt.savefig(REPORTS / "fig_boxplot_taxa_tag_DEDUP.png", dpi=200)
plt.close()

# =========================
# PRINTS NO TERMINAL
# =========================
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)

print("\n=== DON'T GO POR TAG (DEDUP) - TABELA COMPLETA (TOP 10 por qtd) ===")
df_print = df.copy()
df_print["taxa_dontgo"] = df_print["taxa_dontgo"].round(6)
print(df_print[["TAG", "total_eventos", "dontgo", "taxa_dontgo"]].head(10).to_string(index=True))

print("\n=== TOP 10 TAGs (DEDUP) - QUANTIDADE de DON'T GO ===")
top_qtd_print = top_qtd.copy()
top_qtd_print["taxa_dontgo"] = top_qtd_print["taxa_dontgo"].round(6)
print(top_qtd_print[["TAG", "total_eventos", "dontgo", "taxa_dontgo"]].to_string(index=False))

print(f"\n(Filtro de robustez p/ taxa: total_eventos >= {MIN_EVENTOS})")
print("\n=== TOP 10 TAGs (DEDUP) - TAXA de DON'T GO (>= MIN_EVENTOS) ===")
top_taxa_print = top_taxa.copy()
top_taxa_print["taxa_dontgo"] = top_taxa_print["taxa_dontgo"].round(6)
print(top_taxa_print[["TAG", "total_eventos", "dontgo", "taxa_dontgo"]].to_string(index=False))

print("\n=== QUANTIS DA TAXA (DEDUP) ===")
print("Baixo <= {:.4f}% | Médio <= {:.4f}% | Alto > {:.4f}%".format(q_low*100, q_high*100, q_high*100))

print("\n✅ Arquivos gerados em reports/:")
print("-", out_all)
print("-", REPORTS / "eda_top10_tag_quantidade_DEDUP.csv")
print("-", REPORTS / "eda_top10_tag_taxa_DEDUP.csv")
print("-", REPORTS / "eda_tag_risco_baixo_medio_alto_DEDUP.csv")
