from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from src import apontamentos_analysis as ap_an
from src import dontgo_analysis as dg_an
from src import feature_engineering as fe
from src import loaders
from src import modeling
from src import reports
from src import telemetry_analysis as tel_an
from src import validators
from src.config import APP_ICON, APP_LAYOUT, APP_TITLE, FILE_TYPE_LABELS, RAW_DIR
from src.preprocessing import clean_apontamentos, filter_apontamentos
from src.utils import ensure_project_dirs, find_column, format_float, format_hours, format_int, unique_non_null
from src.visualizations import (
    bar_chart,
    boxplot,
    heatmap_hour_weekday,
    horizontal_bar,
    line_chart,
    matrix_heatmap,
    pareto_chart,
)

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout=APP_LAYOUT)
ensure_project_dirs()

CUSTOM_CSS = """
<style>
    .main .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e5e7eb;
        padding: 14px 16px;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
    }
    .status-card {
        padding: 1rem 1.1rem;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        background: #ffffff;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }
    .small-muted {color: #64748b; font-size: 0.92rem;}
    .ok-pill {background:#dcfce7;color:#166534;padding:4px 10px;border-radius:999px;font-weight:600;}
    .warn-pill {background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:999px;font-weight:600;}
    .bad-pill {background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:999px;font-weight:600;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cached_registry_from_raw() -> list[dict]:
    return loaders.scan_local_files(RAW_DIR)


def build_current_registry(uploaded_files) -> list[dict]:
    if uploaded_files:
        # Streamlit UploadedFile não é cacheável; salvamos em data/raw/uploads a cada alteração.
        return loaders.save_uploaded_files(uploaded_files)
    return cached_registry_from_raw()


@st.cache_data(show_spinner=False)
def cached_load_dictionary(path: str | None) -> pd.DataFrame:
    return loaders.load_data_dictionary(path) if path else pd.DataFrame()


@st.cache_data(show_spinner="Carregando apontamentos...")
def cached_load_apontamentos(paths_key: str) -> pd.DataFrame:
    registry = json.loads(paths_key)
    return clean_apontamentos(loaders.load_apontamentos(registry))


def registry_key(registry: list[dict]) -> str:
    # Preserva apenas o que impacta leitura.
    compact = [{"path": r["path"], "type": r["type"], "filename": r["filename"], "size_mb": r.get("size_mb")} for r in registry]
    return json.dumps(compact, sort_keys=True, ensure_ascii=False)


def get_apontamentos_df(registry: list[dict]) -> pd.DataFrame:
    if not registry:
        return pd.DataFrame()
    return cached_load_apontamentos(registry_key(registry))


def render_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.markdown(f"<p class='small-muted'>{subtitle}</p>", unsafe_allow_html=True)


def render_file_status(registry: list[dict]) -> None:
    df = loaders.registry_to_frame(registry)
    required_groups = {
        "Dicionário": bool(loaders.first_path_by_type(registry, "dictionary")),
        "Apontamentos": bool(loaders.paths_by_type(registry, "apontamentos_parquet") or loaders.first_path_by_type(registry, "apontamentos_excel")),
        "Telemetria": bool(loaders.telemetry_paths(registry)),
        "Don’t Go ref.": bool(loaders.first_path_by_type(registry, "dontgo_excel") or loaders.telemetry_paths(registry)),
    }
    cols = st.columns(len(required_groups))
    for col, (name, ok) in zip(cols, required_groups.items()):
        with col:
            st.markdown(
                f"<div class='status-card'><b>{name}</b><br><span class='{'ok-pill' if ok else 'warn-pill'}'>{'OK' if ok else 'Pendente'}</span></div>",
                unsafe_allow_html=True,
            )
    st.divider()
    st.subheader("Arquivos identificados")
    if df.empty:
        st.info("Nenhum arquivo carregado. Envie os arquivos pela barra lateral ou coloque-os em `data/raw/`.")
    else:
        display = df.copy()
        display["tipo_legivel"] = display["type"].map(FILE_TYPE_LABELS).fillna(display["type"])
        st.dataframe(display[["filename", "tipo_legivel", "suffix", "size_mb"]], use_container_width=True, hide_index=True)


def metric_grid(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(min(len(items), 4))
    for i, (label, value, help_text) in enumerate(items):
        with cols[i % len(cols)]:
            st.metric(label, value, help=help_text)


def telemetry_filter_ui(paths: list[str], key_prefix: str = "tel") -> dict:
    if not paths:
        return {}
    cmap = tel_an.telemetry_col_map(paths)
    dt_col = cmap.get("event_date")
    min_dt, max_dt = (None, None)
    if dt_col:
        from src.loaders import parquet_min_max_date
        min_dt, max_dt = parquet_min_max_date(paths, dt_col)

    filters: dict = {}
    with st.expander("Filtros de telemetria", expanded=False):
        if min_dt and max_dt:
            selected_range = st.date_input(
                "Período",
                value=(pd.to_datetime(min_dt).date(), pd.to_datetime(max_dt).date()),
                min_value=pd.to_datetime(min_dt).date(),
                max_value=pd.to_datetime(max_dt).date(),
                key=f"{key_prefix}_date",
            )
            if isinstance(selected_range, tuple) and len(selected_range) == 2:
                filters["date_start"], filters["date_end"] = selected_range
        col1, col2, col3 = st.columns(3)
        with col1:
            locations = tel_an.distinct_values(paths, "location", limit=100)
            filters["locations"] = st.multiselect("Localidade", locations, key=f"{key_prefix}_loc")
        with col2:
            criticidades = tel_an.distinct_values(paths, "severity", limit=100)
            filters["criticidades"] = st.multiselect("Criticidade", criticidades, key=f"{key_prefix}_crit")
        with col3:
            tipos = tel_an.distinct_values(paths, "tipo", limit=100)
            filters["tipos"] = st.multiselect("Tipo", tipos, key=f"{key_prefix}_tipo")
        col4, col5 = st.columns(2)
        with col4:
            tags = tel_an.distinct_values(paths, "tag", limit=250)
            filters["tags"] = st.multiselect("TAG / Equipamento", tags, key=f"{key_prefix}_tag")
        with col5:
            alarmes = tel_an.distinct_values(paths, "alarm", limit=250)
            filters["alarmes"] = st.multiselect("Alarme", alarmes, key=f"{key_prefix}_alarm")
    return filters


def page_home(registry: list[dict]) -> None:
    render_header(APP_TITLE, "MVP profissional para cruzar apontamentos operacionais, telemetria e eventos Don't Go.")
    st.markdown(
        """
        Esta aplicação permite carregar arquivos de **apontamentos**, **telemetria mensal em Parquet**,
        **dicionário de dados** e uma referência de **Don’t Go**, gerando diagnóstico, KPIs, gráficos,
        cruzamentos temporais, features analíticas e exportações.

        O MVP diferencia **hipóteses** de **conclusões**: rankings e precursores indicam pontos de investigação,
        não causalidade automática.
        """
    )
    render_file_status(registry)
    st.subheader("Fluxo recomendado")
    st.markdown(
        """
        1. Faça upload múltiplo dos arquivos na barra lateral.
        2. Acesse **Diagnóstico dos Dados** para validar schema, datas e volume.
        3. Analise **Apontamentos**, **Telemetria** e **Don’t Go**.
        4. Use **Cruzamento** e **Features** para hipóteses de eventos precursores.
        5. Exporte tabelas e relatório em **Relatórios**.
        """
    )


def page_diagnostics(registry: list[dict]) -> None:
    render_header("Diagnóstico dos Dados", "Validação inicial de volumes, colunas, tipos, datas, nulos e duplicidades.")
    render_file_status(registry)

    ap_df = get_apontamentos_df(registry)
    if not ap_df.empty:
        st.subheader("Apontamentos")
        profile = validators.profile_dataframe(ap_df, "apontamentos")
        metric_grid([
            ("Registros", format_int(profile["rows"]), None),
            ("Colunas", format_int(profile["columns"]), None),
            ("Duplicidades", format_int(profile["duplicates"]), None),
        ])
        st.write("Tipos de dados")
        st.dataframe(profile["dtypes"], use_container_width=True, hide_index=True)
        st.write("Nulos")
        st.dataframe(profile["nulls"], use_container_width=True, hide_index=True)
        if not profile["date_ranges"].empty:
            st.write("Períodos detectados")
            st.dataframe(profile["date_ranges"], use_container_width=True, hide_index=True)
        st.write("Validação de colunas mínimas")
        st.dataframe(validators.validate_required_columns(ap_df.columns, "apontamentos"), use_container_width=True, hide_index=True)
    else:
        st.warning("Base de apontamentos não encontrada.")

    paths = loaders.telemetry_paths(registry)
    if paths:
        st.subheader("Telemetria")
        with st.spinner("Consultando metadados da telemetria com DuckDB..."):
            profile = validators.profile_parquet(paths, "telemetria")
        metric_grid([
            ("Eventos", format_int(profile["rows"]), None),
            ("Arquivos Parquet", format_int(len(paths)), None),
            ("Colunas", format_int(len(profile["schema"])), None),
        ])
        st.write("Schema detectado")
        st.dataframe(profile["schema"], use_container_width=True, hide_index=True)
        if not profile["date_ranges"].empty:
            st.write("Período detectado")
            st.dataframe(profile["date_ranges"], use_container_width=True, hide_index=True)
        st.write("Amostra de nulos — colunas iniciais")
        st.dataframe(profile["nulls"], use_container_width=True, hide_index=True)
        st.write("Validação de colunas mínimas")
        st.dataframe(validators.validate_required_columns(profile["schema"]["column_name"].tolist(), "telemetria"), use_container_width=True, hide_index=True)
    else:
        st.warning("Arquivos Parquet de telemetria não encontrados.")


def page_dictionary(registry: list[dict]) -> None:
    render_header("Dicionário de Dados", "Comparação entre dicionário e colunas reais carregadas.")
    dict_path = loaders.first_path_by_type(registry, "dictionary")
    dictionary_df = cached_load_dictionary(dict_path)
    if dictionary_df.empty:
        st.warning("Dicionário de dados não encontrado ou vazio.")
        return
    st.dataframe(dictionary_df, use_container_width=True, hide_index=True)

    ap_df = get_apontamentos_df(registry)
    if not ap_df.empty:
        st.subheader("Comparação — Apontamentos")
        st.dataframe(validators.compare_dictionary_with_columns(dictionary_df, ap_df.columns, "Apontamentos"), use_container_width=True, hide_index=True)

    paths = loaders.telemetry_paths(registry)
    if paths:
        schema = loaders.describe_parquet(paths)
        st.subheader("Comparação — Telemetria")
        st.dataframe(validators.compare_dictionary_with_columns(dictionary_df, schema["column_name"].tolist(), "Telemetria"), use_container_width=True, hide_index=True)


def page_apontamentos(registry: list[dict]) -> None:
    render_header("Apontamentos", "KPIs, filtros e gráficos dos ciclos de apontamento operacional.")
    df = get_apontamentos_df(registry)
    if df.empty:
        st.warning("Nenhuma base de apontamentos carregada.")
        return

    start_col = find_column(df, logical_name="ap_start")
    tag_col = find_column(df, logical_name="ap_tag")
    frota_col = find_column(df, logical_name="ap_frota")
    tipo_col = find_column(df, logical_name="ap_tipo")
    classe_col = find_column(df, logical_name="ap_classe")

    with st.expander("Filtros de apontamentos", expanded=False):
        date_range = None
        if start_col:
            min_date = pd.to_datetime(df[start_col]).min().date()
            max_date = pd.to_datetime(df[start_col]).max().date()
            selected = st.date_input("Período", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="ap_date")
            if isinstance(selected, tuple) and len(selected) == 2:
                date_range = selected
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            tags = st.multiselect("TAG", unique_non_null(df, tag_col), key="ap_tags")
        with c2:
            frotas = st.multiselect("Frota", unique_non_null(df, frota_col), key="ap_frotas")
        with c3:
            tipos = st.multiselect("Tipo", unique_non_null(df, tipo_col), key="ap_tipos")
        with c4:
            classes = st.multiselect("Classe", unique_non_null(df, classe_col), key="ap_classes")
    filtered = filter_apontamentos(df, date_range, tags, frotas, tipos, classes)
    outputs = ap_an.all_apontamentos_outputs(filtered)
    k = outputs["kpis"]

    metric_grid([
        ("Total de apontamentos", format_int(k["total_apontamentos"]), None),
        ("Tempo total", format_hours(k["tempo_total_horas"]), None),
        ("Tempo médio", format_hours(k["tempo_medio_horas"]), None),
        ("Equipamentos", format_int(k["equipamentos"]), None),
    ])
    metric_grid([
        ("Frotas", format_int(k["frotas"]), None),
        ("Classes", format_int(k["classes"]), None),
        ("Tipos", format_int(k["tipos"]), None),
    ])

    tab1, tab2, tab3 = st.tabs(["Gráficos principais", "Tabelas", "Exportações"])
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(line_chart(outputs["mensal"], "AnoMes", "quantidade", "Apontamentos por mês"), use_container_width=True)
            st.plotly_chart(horizontal_bar(outputs["top_equipamentos_qtd"], "TAG", "qtd_apontamentos", "Top equipamentos por apontamentos"), use_container_width=True)
        with c2:
            st.plotly_chart(horizontal_bar(outputs["classes"], "Classe", "quantidade", "Apontamentos por classe"), use_container_width=True)
            st.plotly_chart(horizontal_bar(outputs["top_equipamentos_horas"], "TAG", "horas_apontadas", "Top equipamentos por horas apontadas"), use_container_width=True)
        st.plotly_chart(pareto_chart(outputs["pareto_classes"], "Classe", "qtd", "perc_acumulado", "Pareto de classes"), use_container_width=True)
        st.plotly_chart(boxplot(ap_an.duration_box_data(filtered), "Duracao_Horas", "Boxplot da duração dos apontamentos"), use_container_width=True)
    with tab2:
        for name, table in outputs.items():
            if isinstance(table, pd.DataFrame):
                with st.expander(name, expanded=False):
                    st.dataframe(table, use_container_width=True, hide_index=True)
    with tab3:
        export_tables = {k: v for k, v in outputs.items() if isinstance(v, pd.DataFrame)}
        st.download_button("Baixar tabelas de apontamentos em Excel", reports.excel_workbook_bytes(export_tables), "apontamentos_analise.xlsx")
        st.download_button("Baixar base filtrada em CSV", reports.csv_bytes(filtered), "apontamentos_filtrado.csv")


def page_telemetry(registry: list[dict]) -> None:
    render_header("Telemetria", "Consulta histórica dos Parquets mensais sem carregar tudo em memória.")
    paths = loaders.telemetry_paths(registry)
    if not paths:
        st.warning("Nenhum arquivo Parquet de telemetria carregado.")
        return
    filters = telemetry_filter_ui(paths, "telemetry")
    with st.spinner("Calculando KPIs e agregações em DuckDB..."):
        outputs = tel_an.telemetry_outputs(paths, filters)
    k = outputs["kpis"]
    metric_grid([
        ("Total de eventos", format_int(k.get("total_eventos", 0)), None),
        ("Equipamentos", format_int(k.get("equipamentos", 0)), None),
        ("Localidades", format_int(k.get("localidades", 0)), None),
        ("Alarmes", format_int(k.get("alarmes", 0)), None),
    ])
    metric_grid([
        ("Criticidades", format_int(k.get("criticidades", 0)), None),
        ("Don’t Go", format_int(k.get("dontgo_total", 0)), None),
        ("Taxa Don’t Go", f"{format_float(k.get('dontgo_rate', 0), 3)}%", None),
    ])

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_chart(outputs["mensal"], "AnoMes", "eventos", "Eventos por mês"), use_container_width=True)
        st.plotly_chart(horizontal_bar(outputs["top_alarmes"], "Alarme", "eventos", "Top alarmes"), use_container_width=True)
        st.plotly_chart(horizontal_bar(outputs["criticidades"], "Criticidade", "eventos", "Eventos por criticidade"), use_container_width=True)
    with c2:
        st.plotly_chart(line_chart(outputs["diario"], "Data", "eventos", "Eventos por dia"), use_container_width=True)
        st.plotly_chart(horizontal_bar(outputs["top_equipamentos"], "TAG", "eventos", "Top equipamentos por eventos"), use_container_width=True)
        st.plotly_chart(horizontal_bar(outputs["localidades"], "Localidade", "eventos", "Eventos por localidade"), use_container_width=True)
    st.plotly_chart(heatmap_hour_weekday(outputs["heatmap"]), use_container_width=True)

    with st.expander("Tabelas agregadas e exportação", expanded=False):
        export_tables = {k: v for k, v in outputs.items() if isinstance(v, pd.DataFrame)}
        for name, table in export_tables.items():
            st.write(name)
            st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button("Baixar agregações de telemetria em Excel", reports.excel_workbook_bytes(export_tables), "telemetria_agregacoes.xlsx")


def page_dontgo(registry: list[dict]) -> None:
    render_header("Don’t Go", "Foco em eventos Is_Dont_Go = 1, rankings e linha do tempo investigativa.")
    paths = loaders.telemetry_paths(registry)
    if not paths:
        st.warning("Nenhum arquivo Parquet de telemetria carregado.")
        return
    filters = telemetry_filter_ui(paths, "dontgo")
    with st.spinner("Analisando eventos Don’t Go..."):
        outputs = dg_an.dontgo_outputs(paths, filters)
    k = outputs["kpis"]
    metric_grid([
        ("Eventos Don’t Go", format_int(k.get("dontgo_total", 0)), None),
        ("Taxa sobre total", f"{format_float(k.get('dontgo_rate', 0), 3)}%", None),
        ("Equipamentos afetados", format_int(k.get("equipamentos_com_dontgo", 0)), None),
        ("Alarmes associados", format_int(k.get("alarmes_com_dontgo", 0)), None),
    ])

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_chart(outputs["mensal"], "AnoMes", "eventos", "Don’t Go por mês"), use_container_width=True)
        st.plotly_chart(horizontal_bar(outputs["equipamentos"], "TAG", "eventos", "Don’t Go por equipamento"), use_container_width=True)
        st.plotly_chart(horizontal_bar(outputs["criticidades"], "Criticidade", "eventos", "Don’t Go por criticidade"), use_container_width=True)
    with c2:
        st.plotly_chart(horizontal_bar(outputs["alarmes"], "Alarme", "eventos", "Don’t Go por alarme"), use_container_width=True)
        st.plotly_chart(horizontal_bar(outputs["localidades"], "Localidade", "eventos", "Don’t Go por localidade"), use_container_width=True)
        st.plotly_chart(horizontal_bar(outputs["turnos"], "Inicio_Turno", "eventos", "Don’t Go por turno/início de turno"), use_container_width=True)

    st.subheader("Investigação por evento")
    events = dg_an.list_dontgo_events(paths, filters, limit=500)
    if events.empty:
        st.info("Nenhum evento Don’t Go encontrado nos filtros atuais.")
        return
    events_display = events.copy()
    events_display.insert(0, "idx", range(len(events_display)))
    st.dataframe(events_display, use_container_width=True, hide_index=True)
    selected_idx = st.selectbox(
        "Selecione um evento para abrir a linha do tempo",
        options=events_display["idx"].tolist(),
        format_func=lambda i: f"{events_display.loc[events_display['idx'] == i, 'Data_Evento'].iloc[0]} — {events_display.loc[events_display['idx'] == i, 'TAG'].iloc[0]}",
    )
    hours = st.slider("Janela da linha do tempo ± horas", 1, 24, 2)
    ap_df = get_apontamentos_df(registry)
    timeline = dg_an.timeline_for_dontgo_event(paths, events.iloc[int(selected_idx)], ap_df, hours_before=hours, hours_after=hours)
    t1, t2 = st.tabs(["Telemetria na janela", "Apontamentos na janela"])
    with t1:
        st.dataframe(timeline["telemetria"], use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(timeline["apontamentos"], use_container_width=True, hide_index=True)


def page_crossing(registry: list[dict]) -> None:
    render_header("Cruzamento Apontamentos × Telemetria", "Eventos antes, durante e depois dos apontamentos, por TAG e janela temporal.")
    paths = loaders.telemetry_paths(registry)
    ap_df = get_apontamentos_df(registry)
    if not paths or ap_df.empty:
        st.warning("Carregue telemetria Parquet e apontamentos para executar o cruzamento.")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        before = st.number_input("Janela antes do apontamento (min)", min_value=5, max_value=1440, value=60, step=5)
    with col2:
        after = st.number_input("Janela depois do apontamento (min)", min_value=5, max_value=1440, value=60, step=5)
    with col3:
        max_ap = st.number_input("Máx. apontamentos no cruzamento", min_value=100, max_value=100_000, value=20_000, step=1000)

    st.info("Para manter o MVP responsivo, o cruzamento pode limitar a quantidade de apontamentos. Aumente o limite conforme a capacidade do computador.")
    if st.button("Executar cruzamento", type="primary"):
        with st.spinner("Cruzando bases em DuckDB..."):
            cross = tel_an.cross_events_with_apontamentos(paths, ap_df, int(before), int(after), int(max_ap))
        if cross.empty:
            st.warning("Não foi possível cruzar os dados. Verifique se TAG, Inicio/Fim e Data_Evento foram detectados.")
            return
        st.session_state["cross_result"] = cross

    cross = st.session_state.get("cross_result", pd.DataFrame())
    if not cross.empty:
        st.dataframe(cross, use_container_width=True, hide_index=True)
        st.plotly_chart(horizontal_bar(cross.groupby("TAG", as_index=False)["eventos"].sum().sort_values("eventos", ascending=False).head(25), "TAG", "eventos", "Equipamentos com mais eventos próximos de apontamentos"), use_container_width=True)
        st.plotly_chart(matrix_heatmap(cross, "TAG", "Classe", "eventos", "Matriz equipamento × classe"), use_container_width=True)
        st.download_button("Baixar cruzamento em CSV", reports.csv_bytes(cross), "cruzamento_apontamentos_telemetria.csv")


def page_features(registry: list[dict]) -> None:
    render_header("Engenharia de Features", "Dataset analítico para investigação e evolução de modelo preditivo.")
    paths = loaders.telemetry_paths(registry)
    if not paths:
        st.warning("Carregue arquivos Parquet de telemetria.")
        return
    ap_df = get_apontamentos_df(registry)
    max_dg = st.number_input("Máx. eventos Don’t Go para gerar features", min_value=100, max_value=20_000, value=2_000, step=100)
    if st.button("Gerar dataset de features", type="primary"):
        with st.spinner("Gerando features temporais por equipamento..."):
            features = fe.generate_dontgo_feature_dataset(paths, ap_df, max_dontgo=int(max_dg))
        st.session_state["features_df"] = features

    features = st.session_state.get("features_df", pd.DataFrame())
    if not features.empty:
        st.success(f"Dataset gerado com {len(features):,} linhas e {features.shape[1]} colunas.".replace(",", "."))
        st.dataframe(features, use_container_width=True, hide_index=True)
        st.download_button("Baixar features em CSV", reports.csv_bytes(features), "features_dontgo.csv")
        try:
            st.download_button("Baixar features em Parquet", reports.parquet_bytes(features), "features_dontgo.parquet")
        except Exception as exc:
            st.warning(f"Exportação Parquet indisponível. Instale pyarrow. Detalhe: {exc}")
    else:
        st.info("Gere o dataset para visualizar e exportar as features.")

    with st.expander("Criar amostras negativas por equipamento-hora", expanded=False):
        max_rows = st.number_input("Máx. linhas equipamento-hora", min_value=1_000, max_value=500_000, value=20_000, step=1_000)
        if st.button("Gerar base equipamento-hora"):
            with st.spinner("Agregando equipamento-hora..."):
                neg = fe.create_negative_samples_by_equipment_hour(paths, max_rows=int(max_rows))
            st.session_state["negative_hour_df"] = neg
        neg = st.session_state.get("negative_hour_df", pd.DataFrame())
        if not neg.empty:
            st.dataframe(neg, use_container_width=True, hide_index=True)
            st.download_button("Baixar equipamento-hora CSV", reports.csv_bytes(neg), "equipamento_hora_dataset.csv")


def page_modeling(registry: list[dict]) -> None:
    render_header("Modelo Preditivo Exploratória", "Baseline inicial para risco de Don’t Go, com limitações explícitas.")
    st.warning("Use este módulo apenas como protótipo. Para produção é obrigatório validar granularidade, exemplos negativos, corte temporal e data leakage.")
    df = st.session_state.get("negative_hour_df", pd.DataFrame())
    if df.empty:
        st.info("Gere antes uma base equipamento-hora na página Engenharia de Features.")
        return
    if st.button("Treinar baseline Random Forest", type="primary"):
        result = modeling.train_baseline_classifier(df, target_col="target_dontgo")
        st.session_state["model_result"] = result
    result = st.session_state.get("model_result")
    if result:
        if result.get("status") != "ok":
            st.warning(result.get("message", "Modelo não treinado."))
        else:
            metrics = result["metrics"]
            metric_grid([
                ("Precision", format_float(metrics["precision"], 3), None),
                ("Recall", format_float(metrics["recall"], 3), None),
                ("F1-score", format_float(metrics["f1"], 3), None),
                ("ROC-AUC", format_float(metrics.get("roc_auc") or 0, 3), None),
            ])
            st.write("Matriz de confusão")
            st.dataframe(pd.DataFrame(metrics["confusion_matrix"]), use_container_width=True)
            st.write("Relatório de classificação")
            st.json(metrics["classification_report"])


def page_reports(registry: list[dict]) -> None:
    render_header("Relatórios e Exportações", "Geração de Excel, CSV, Parquet e PDF executivo.")
    paths = loaders.telemetry_paths(registry)
    ap_df = get_apontamentos_df(registry)
    summary = {}
    tables: dict[str, pd.DataFrame] = {}

    if not ap_df.empty:
        ap_outputs = ap_an.all_apontamentos_outputs(ap_df)
        summary.update({f"ap_{k}": v for k, v in ap_outputs["kpis"].items()})
        tables.update({f"ap_{k}": v for k, v in ap_outputs.items() if isinstance(v, pd.DataFrame)})
    if paths:
        tel_kpis = tel_an.telemetry_kpis(paths)
        summary.update({f"tel_{k}": v for k, v in tel_kpis.items()})
        tables["tel_top_alarmes"] = tel_an.aggregate_top(paths, "alarm", "Alarme", top_n=30)
        tables["tel_top_equipamentos"] = tel_an.aggregate_top(paths, "tag", "TAG", top_n=30)
        tables["dontgo_top_alarmes"] = tel_an.aggregate_top(paths, "alarm", "Alarme", top_n=30, dontgo_only=True)
        tables["dontgo_top_equipamentos"] = tel_an.aggregate_top(paths, "tag", "TAG", top_n=30, dontgo_only=True)
    if st.session_state.get("cross_result") is not None:
        tables["cruzamento"] = st.session_state.get("cross_result")
    if st.session_state.get("features_df") is not None:
        tables["features"] = st.session_state.get("features_df")

    st.subheader("Resumo disponível")
    if summary:
        st.json(summary)
    else:
        st.info("Carregue os arquivos para gerar um resumo.")

    col1, col2 = st.columns(2)
    with col1:
        if tables:
            st.download_button("Baixar pacote Excel", reports.excel_workbook_bytes(tables), "dontgo_analyzer_tabelas.xlsx")
    with col2:
        pdf = reports.executive_pdf_bytes(summary, tables)
        st.download_button("Baixar relatório executivo PDF", pdf, "relatorio_executivo_dontgo.pdf")

    st.subheader("Tabelas incluídas")
    for name, df in tables.items():
        with st.expander(name):
            st.dataframe(df.head(500), use_container_width=True, hide_index=True)


def main() -> None:
    st.sidebar.title("🚦 Don't Go Analyzer")
    st.sidebar.caption("Upload múltiplo ou arquivos em data/raw/")
    uploaded_files = st.sidebar.file_uploader(
        "Anexe README, dicionário, apontamentos, Don’t Go e Parquets de telemetria",
        type=["xlsx", "xlsm", "xls", "parquet", "md"],
        accept_multiple_files=True,
    )
    registry = build_current_registry(uploaded_files)
    if st.sidebar.button("Recarregar data/raw"):
        cached_registry_from_raw.clear()
        st.rerun()

    pages = {
        "Página Inicial": page_home,
        "Diagnóstico dos Dados": page_diagnostics,
        "Dicionário de Dados": page_dictionary,
        "Apontamentos": page_apontamentos,
        "Telemetria": page_telemetry,
        "Don’t Go": page_dontgo,
        "Cruzamento": page_crossing,
        "Engenharia de Features": page_features,
        "Modelo Preditivo": page_modeling,
        "Relatórios e Exportações": page_reports,
    }
    selected_page = st.sidebar.radio("Navegação", list(pages.keys()))

    with st.sidebar.expander("Privacidade e governança", expanded=False):
        st.write("O app mantém operadores anonimizados e não possui rotina de reidentificação.")
        st.write("Rankings e precursores são hipóteses analíticas até validação operacional.")

    pages[selected_page](registry)


if __name__ == "__main__":
    main()
