from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(".")
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# arquivo gerado no EDA 2
csv_path = REPORTS / "eda_dontgo_por_mes.csv"
df = pd.read_csv(csv_path)

# garantir formato da coluna de mês
df["mes"] = pd.to_datetime(df["mes"])
df["mes_str"] = df["mes"].dt.strftime("%Y-%m")

# 1) Gráfico de barras: quantidade de Don't Go por mês
plt.figure()
plt.bar(df["mes_str"], df["dontgo"])
plt.title("Quantidade de eventos 'Don't Go' por mês")
plt.xlabel("Mês")
plt.ylabel("Quantidade (Is_Dont_Go=1)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(REPORTS / "fig_dontgo_por_mes_quantidade.png", dpi=200)
plt.close()

# 2) Gráfico de linha: taxa de Don't Go por mês (em %)
plt.figure()
plt.plot(df["mes_str"], df["taxa_dontgo"] * 100, marker="o")
plt.title("Taxa de eventos 'Don't Go' por mês")
plt.xlabel("Mês")
plt.ylabel("Taxa (%)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(REPORTS / "fig_dontgo_por_mes_taxa.png", dpi=200)
plt.close()

print("✅ Gráficos salvos em:", REPORTS.resolve())
print("- fig_dontgo_por_mes_quantidade.png")
print("- fig_dontgo_por_mes_taxa.png")