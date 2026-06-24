from pathlib import Path
import pandas as pd

# Se não tiver matplotlib, instale:
# pip install matplotlib
import matplotlib.pyplot as plt

ROOT = Path(".")
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# Preferência 1: arquivo já com Pareto
pareto_path = REPORTS / "eda_pareto_dontgo_por_tag.csv"

# Preferência 2: se não existir, calcula Pareto a partir da tabela completa por TAG
tag_path = REPORTS / "eda_dontgo_por_tag_completo.csv"  # ou eda_dontgo_por_tag.csv

# Configurações do Pareto (ajuste aqui)
TOP_N = 10  # quantas TAGs mostrar antes de "Outros"
SAIDA_PNG = REPORTS / f"fig_pareto_top{TOP_N}_mais_outros.png"

# ---------------------------
# 1) Carregar dados
# ---------------------------
if pareto_path.exists():
    df = pd.read_csv(pareto_path)
    # Esperado: colunas TAG, dontgo, cum_pct_dontgo (ou cum_dontgo)
    if "cum_pct_dontgo" not in df.columns:
        # tenta calcular se veio só cum_dontgo
        if "cum_dontgo" in df.columns and "dontgo" in df.columns:
            total = df["dontgo"].sum()
            df["cum_pct_dontgo"] = df["cum_dontgo"] / (total if total > 0 else 1)
        else:
            raise ValueError("Arquivo Pareto não possui cum_pct_dontgo nem cum_dontgo.")
else:
    if not tag_path.exists():
        raise FileNotFoundError(
            "Não achei nenhum CSV para gerar Pareto.\n"
            f"Esperado: {pareto_path} OU {tag_path}"
        )
    tag_df = pd.read_csv(tag_path)
    if "TAG" not in tag_df.columns or "dontgo" not in tag_df.columns:
        raise ValueError("CSV de TAG precisa ter colunas TAG e dontgo.")
    df = tag_df.sort_values("dontgo", ascending=False).copy()
    df["cum_dontgo"] = df["dontgo"].cumsum()
    total = df["dontgo"].sum()
    df["cum_pct_dontgo"] = df["cum_dontgo"] / (total if total > 0 else 1)

# Garantir ordenação correta
df = df.sort_values("dontgo", ascending=False).reset_index(drop=True)

# ---------------------------
# 2) Montar Top N + Outros
# ---------------------------
top = df.head(TOP_N).copy()
resto = df.iloc[TOP_N:].copy()

if len(resto) > 0:
    outros_dontgo = resto["dontgo"].sum()
    # último cumulativo vira 100% com "Outros"
    top_total = top["dontgo"].sum()
    total_all = df["dontgo"].sum()
    cum_top = top["dontgo"].cumsum()
    top["cum_pct_dontgo"] = cum_top / (total_all if total_all > 0 else 1)

    outros = pd.DataFrame([{
        "TAG": "Outros",
        "dontgo": outros_dontgo,
        "cum_pct_dontgo": 1.0
    }])
    plot_df = pd.concat([top[["TAG", "dontgo", "cum_pct_dontgo"]], outros], ignore_index=True)
else:
    # se não existe resto, plota só top
    plot_df = top[["TAG", "dontgo", "cum_pct_dontgo"]].copy()

# ---------------------------
# 3) Plot Pareto (barras + linha cumulativa)
# ---------------------------
fig, ax1 = plt.subplots(figsize=(12, 5))

ax1.bar(plot_df["TAG"].astype(str), plot_df["dontgo"])
ax1.set_xlabel(f"TAG (Top {TOP_N} + Outros)")
ax1.set_ylabel("Quantidade de Don't Go (Is_Dont_Go=1)")

ax2 = ax1.twinx()
ax2.plot(
    plot_df["TAG"].astype(str),
    plot_df["cum_pct_dontgo"] * 100,
    color="red",
    marker="o"
)
ax2.set_ylabel("% cumulativo de Don't Go")
ax2.set_ylim(0, 100)

plt.title(f"Pareto: Concentração de 'Don't Go' por TAG (Top {TOP_N} + Outros)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(SAIDA_PNG, dpi=200)
plt.close()

print("✅ Pareto salvo em:", SAIDA_PNG.resolve())
