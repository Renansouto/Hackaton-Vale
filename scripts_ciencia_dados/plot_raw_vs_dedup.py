from pathlib import Path
import pandas as pd

# Se faltar matplotlib:
# pip install matplotlib
import matplotlib.pyplot as plt

ROOT = Path(".")
REPORTS = ROOT / "reports"
csv_path = REPORTS / "compare_month_raw_vs_dedup.csv"

if not csv_path.exists():
    raise FileNotFoundError(f"Não achei {csv_path}. Rode o comparativo RAW vs DEDUP primeiro.")

df = pd.read_csv(csv_path)

# Garantir ordenação por mês
df["mes"] = pd.to_datetime(df["mes"])
df = df.sort_values("mes")
df["mes_str"] = df["mes"].dt.strftime("%Y-%m")

# Converter taxas para %
df["taxa_raw_pct"] = df["taxa_raw"] * 100
df["taxa_dedup_pct"] = df["taxa_dedup"] * 100

# ---------------------------
# Gráfico 1: Taxa RAW vs DEDUP + diff_total_% (eixo secundário)
# ---------------------------
fig, ax1 = plt.subplots(figsize=(12, 5))

# Linhas (taxa em %)
ax1.plot(df["mes_str"], df["taxa_raw_pct"], marker="o", label="Taxa RAW (%)")
ax1.plot(df["mes_str"], df["taxa_dedup_pct"], marker="o", label="Taxa DEDUP (%)")
ax1.set_xlabel("Mês")
ax1.set_ylabel("Taxa de Don’t Go (%)")
ax1.grid(True, axis="y", alpha=0.3)

# Eixo secundário com barras de diff_total_%
ax2 = ax1.twinx()
ax2.bar(df["mes_str"], df["diff_total_%"], alpha=0.25, color="gray", label="Diff total eventos (%)")
ax2.set_ylabel("Diferença no total de eventos (DEDUP vs RAW) (%)")

# Título e legenda combinada
plt.title("RAW vs DEDUP: Taxa de Don’t Go (%) e impacto no total de eventos")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

plt.xticks(rotation=45, ha="right")
plt.tight_layout()

out_png = REPORTS / "fig_raw_vs_dedup_taxa_e_diff_total.png"
plt.savefig(out_png, dpi=200)
plt.close()

# ---------------------------
# Gráfico 2 (opcional, mas útil): Total de eventos RAW vs DEDUP
# ---------------------------
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df["mes_str"], df["total_eventos_raw"], marker="o", label="Total eventos RAW")
ax.plot(df["mes_str"], df["total_eventos_dedup"], marker="o", label="Total eventos DEDUP")
ax.set_title("RAW vs DEDUP: Total de eventos por mês")
ax.set_xlabel("Mês")
ax.set_ylabel("Total de eventos")
ax.grid(True, axis="y", alpha=0.3)
ax.legend(loc="upper left")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()

out_png2 = REPORTS / "fig_raw_vs_dedup_total_eventos.png"
plt.savefig(out_png2, dpi=200)
plt.close()

print("✅ Gráficos gerados em reports/:")
print("-", out_png.name)
print("-", out_png2.name)