from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(".")
DATA = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# Ajuste se quiser filtrar TAGs com pouco volume (evita distorção em taxa)
MIN_EVENTOS_PARA_TAXA = 100000

# Para quantis Baixo/Médio/Alto (você pode mudar p/ 0.2 e 0.8 se preferir)
Q_BAIXO = 0.33
Q_ALTO = 0.66

con = duckdb.connect(database=":memory:")

# Lê todos os arquivos telemetria_* diretamente (DuckDB aceita glob)
telemetry_glob = str(DATA / "telemetry_*.parquet")

# 1) Tabela completa por TAG: total, dontgo e taxa
df = con.execute(f"""
SELECT
  TAG,
  COUNT(*) AS total_eventos,
  SUM(CASE WHEN Is_Dont_Go = 1 THEN 1 ELSE 0 END) AS dontgo,
  SUM(CASE WHEN Is_Dont_Go = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS taxa_dontgo
FROM read_parquet('{telemetry_glob}')
GROUP BY TAG
ORDER BY dontgo DESC
""").fetchdf()

# Salvar tabela completa
df.to_csv(REPORTS / "eda_dontgo_por_tag_completo.csv", index=False)

# 2) Top 10 por QUANTIDADE
top_qtd = df.sort_values("dontgo", ascending=False).head(10).copy()
top_qtd.to_csv(REPORTS / "eda_top10_tag_por_dontgo_quantidade.csv", index=False)

# 3) Top 10 por TAXA (filtra por volume mínimo)
df_taxa = df[df["total_eventos"] >= MIN_EVENTOS_PARA_TAXA].copy()
top_taxa = df_taxa.sort_values("taxa_dontgo", ascending=False).head(10).copy()
top_taxa.to_csv(REPORTS / "eda_top10_tag_por_dontgo_taxa.csv", index=False)

# 4) Pareto (% cumulativo de Don’t Go por TAG)
pareto = df.sort_values("dontgo", ascending=False).copy()
pareto["cum_dontgo"] = pareto["dontgo"].cumsum()
total_dg = pareto["dontgo"].sum()
pareto["cum_pct_dontgo"] = pareto["cum_dontgo"] / (total_dg if total_dg > 0 else 1)

# Quantas TAGs fazem 80% dos don't go?
k80 = int((pareto["cum_pct_dontgo"] <= 0.8).sum()) + 1
pareto.to_csv(REPORTS / "eda_pareto_dontgo_por_tag.csv", index=False)

# 5) Quantis para Baixo/Médio/Alto (baseado na taxa_dontgo)
# Recomendação: usar apenas TAGs com volume mínimo
q_low = df_taxa["taxa_dontgo"].quantile(Q_BAIXO) if len(df_taxa) else None
q_high = df_taxa["taxa_dontgo"].quantile(Q_ALTO) if len(df_taxa) else None

def classificar_risco(row):
    if row["total_eventos"] < MIN_EVENTOS_PARA_TAXA:
        return "Volume insuficiente"
    if row["taxa_dontgo"] <= q_low:
        return "Baixo"
    elif row["taxa_dontgo"] <= q_high:
        return "Médio"
    else:
        return "Alto"

if q_low is not None and q_high is not None:
    df["risco_quantis"] = df.apply(classificar_risco, axis=1)
else:
    df["risco_quantis"] = "Não calculado"

df.to_csv(REPORTS / "eda_tag_com_risco_baixo_medio_alto.csv", index=False)

# 6) Gráficos (PNG): Top 10, Pareto, Histograma e Boxplot
# (precisa de matplotlib)
try:
    import matplotlib.pyplot as plt

    # --- Top 10 quantidade
    plt.figure(figsize=(10, 5))
    plt.bar(top_qtd["TAG"].astype(str), top_qtd["dontgo"])
    plt.title("Top 10 TAGs por quantidade de 'Don't Go'")
    plt.xlabel("TAG")
    plt.ylabel("Quantidade (Is_Dont_Go=1)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(REPORTS / "fig_top10_tag_dontgo_quantidade.png", dpi=200)
    plt.close()

    # --- Top 10 taxa (%)
    plt.figure(figsize=(10, 5))
    plt.bar(top_taxa["TAG"].astype(str), top_taxa["taxa_dontgo"] * 100)
    plt.title(f"Top 10 TAGs por taxa de 'Don't Go' (mín. {MIN_EVENTOS_PARA_TAXA} eventos)")
    plt.xlabel("TAG")
    plt.ylabel("Taxa (%)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(REPORTS / "fig_top10_tag_dontgo_taxa.png", dpi=200)
    plt.close()

   
    # --- Histograma taxa (%)
    plt.figure(figsize=(10, 5))
    plt.hist(df_taxa["taxa_dontgo"] * 100, bins=30)
    plt.title(f"Distribuição da taxa de 'Don't Go' por TAG (mín. {MIN_EVENTOS_PARA_TAXA} eventos)")
    plt.xlabel("Taxa de Don't Go (%)")
    plt.ylabel("Número de TAGs")
    plt.tight_layout()
    plt.savefig(REPORTS / "fig_hist_taxa_dontgo_por_tag.png", dpi=200)
    plt.close()

    # --- Boxplot taxa (%)
    plt.figure(figsize=(6, 5))
    plt.boxplot(df_taxa["taxa_dontgo"] * 100, vert=True)
    plt.title("Boxplot da taxa de 'Don't Go' por TAG (%)")
    plt.ylabel("Taxa de Don't Go (%)")
    plt.tight_layout()
    plt.savefig(REPORTS / "fig_boxplot_taxa_dontgo_por_tag.png", dpi=200)
    plt.close()

    print("\n✅ PNGs gerados em reports/")

except ModuleNotFoundError:
    print("\n⚠️ matplotlib não está instalado.")
    print("Instale com: pip install matplotlib")
    print("Depois rode o script novamente para gerar os PNGs.")

# 7) Resumo textual para colar no Trello
summary_lines = []
summary_lines.append("EDA 3 – Don’t Go por TAG (completo)")
summary_lines.append(f"- Total de TAGs: {df.shape[0]}")
summary_lines.append(f"- TAG com mais Don't Go (qtd): {top_qtd.iloc[0]['TAG']} ({int(top_qtd.iloc[0]['dontgo'])})")
summary_lines.append(f"- TAG com maior taxa (>= {MIN_EVENTOS_PARA_TAXA} eventos): {top_taxa.iloc[0]['TAG']} ({top_taxa.iloc[0]['taxa_dontgo']*100:.3f}%)")
summary_lines.append(f"- Concentração (Pareto): ~{k80} TAG(s) respondem por ~80% dos Don't Go")
if q_low is not None and q_high is not None:
    summary_lines.append(f"- Quantis (taxa): Baixo <= {q_low*100:.4f}% | Médio <= {q_high*100:.4f}% | Alto > {q_high*100:.4f}% (considerando TAGs com >= {MIN_EVENTOS_PARA_TAXA} eventos)")

summary_text = "\n".join(summary_lines)
(REPORTS / "eda_03_resumo_tag.txt").write_text(summary_text, encoding="utf-8")

print("\n=== RESUMO (para Trello) ===")
print(summary_text)

print(f"\n✅ CSVs/PNG/TXT salvos em: {REPORTS.resolve()}")