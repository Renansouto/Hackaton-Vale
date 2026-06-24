from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(".")
REPORTS = ROOT / "reports"
csv_path = REPORTS / "compare_month_raw_vs_dedup.csv"

if not csv_path.exists():
    raise FileNotFoundError(f"Não achei {csv_path}. Gere o CSV primeiro.")

df = pd.read_csv(csv_path)

# Colunas que queremos mostrar (tabela resumida e legível)
cols = [
    "mes",
    "total_eventos_raw", "total_eventos_dedup", "diff_total_%",
    "dontgo_raw", "dontgo_dedup", "diff_dontgo_%",
    "taxa_raw", "taxa_dedup", "diff_taxa_pp"
]
df = df[cols].copy()

# Formatar mês
df["mes"] = pd.to_datetime(df["mes"]).dt.strftime("%Y-%m")

# Formatar números para ficar bonito
def fmt_int(x):  # milhares com ponto
    return f"{int(x):,}".replace(",", ".")

def fmt_pct(x, dec=2):
    return f"{x:.{dec}f}%"

def fmt_rate(x):  # taxa em %
    return f"{x*100:.4f}%"

# Aplicar formatação
df["total_eventos_raw"] = df["total_eventos_raw"].apply(fmt_int)
df["total_eventos_dedup"] = df["total_eventos_dedup"].apply(fmt_int)
df["dontgo_raw"] = df["dontgo_raw"].astype(int).apply(fmt_int)
df["dontgo_dedup"] = df["dontgo_dedup"].astype(int).apply(fmt_int)

df["diff_total_%"] = df["diff_total_%"].apply(lambda v: fmt_pct(v, 2))
df["diff_dontgo_%"] = df["diff_dontgo_%"].apply(lambda v: fmt_pct(v, 2))

# taxa_raw e taxa_dedup estão em proporção (0.0004...), converte p/ %
df["taxa_raw"] = df["taxa_raw"].apply(fmt_rate)
df["taxa_dedup"] = df["taxa_dedup"].apply(fmt_rate)

# diff_taxa_pp já está em pontos percentuais (pp), então mantém como “pp”
df["diff_taxa_pp"] = df["diff_taxa_pp"].apply(lambda v: f"{v:.4f} pp")

# Renomear colunas para apresentação
df.columns = [
    "Mês",
    "Total RAW", "Total DEDUP", "Δ Total (%)",
    "Don’t Go RAW", "Don’t Go DEDUP", "Δ Don’t Go (%)",
    "Taxa RAW", "Taxa DEDUP", "Δ Taxa (pp)"
]

# ====== GERAR IMAGEM DA TABELA ======
fig, ax = plt.subplots(figsize=(14, 2.8))
ax.axis("off")

table = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    cellLoc="center",
    loc="center"
)

table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 1.4)

# Deixar cabeçalho em negrito e com cor leve
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_text_props(weight="bold", color="white")
        cell.set_facecolor("#2F5597")  # azul
    else:
        # zebra stripes
        cell.set_facecolor("#F2F2F2" if row % 2 == 0 else "white")

out_png = REPORTS / "fig_tabela_raw_vs_dedup.png"
plt.title("Comparação mensal: RAW vs DEDUP (telemetria)", fontsize=12, pad=12)
plt.tight_layout()
plt.savefig(out_png, dpi=200, bbox_inches="tight")
plt.close()

print("✅ Tabela em imagem salva em:", out_png.resolve())