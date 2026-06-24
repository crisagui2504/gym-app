"""Panel de Inteligencia Deportiva — Sprint 5 (reemplaza Power BI).

Uso:
    python dashboard.py
    Abre http://127.0.0.1:8050

Fuente de datos: historial.csv generado por exportar_local.py o descargado
manualmente desde la app Angular (/sync → "Descargar Historial").
Si el CSV está vacío, carga datos de demostración automáticamente.
"""
from __future__ import annotations

import os
import pathlib
import random
import subprocess
import sys
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dash_table, dcc, html, callback

from config_usuario import cargar_config, guardar_config
from enfoques import ENFOQUES, SPLITS, MUSCULOS_PRIORIZABLES
from generador import generar_plan

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de diseño (paleta oscura que combina con la app Angular)
# ─────────────────────────────────────────────────────────────────────────────
CSV_PATH = pathlib.Path(__file__).resolve().parent / "historial.csv"

# ── Paletas de tema (oscuro / claro) ─────────────────────────────────────────
TEMAS = {
    "oscuro": dict(bg="#0b0d13", card="#161922", card2="#1e2230", line="#2a2f42",
                   text="#eef0f6", muted="#8b90a8", accent="#00e0b5", accent2="#18b3ff",
                   danger="#ff5d7a", warn="#ffc043", grid="#222740", template="plotly_dark"),
    "claro":  dict(bg="#f4f6fb", card="#ffffff", card2="#eef1f7", line="#dde2ee",
                   text="#1b1f2a", muted="#5a6072", accent="#00a98e", accent2="#1488d8",
                   danger="#e23d5c", warn="#c77f00", grid="#e3e7f0", template="plotly_white"),
}


def _aplicar_tema(tema: str) -> None:
    """Setea los colores globales y estilos derivados según el tema elegido."""
    global BG, CARD, CARD2, LINE, TEXT, MUTED, ACCENT, ACCENT2, DANGER, WARN, GRID
    global PLOTLY_THEME, _TAB_STYLE, _TAB_SELECTED_STYLE, _LABEL_STYLE
    p = TEMAS.get(tema, TEMAS["oscuro"])
    BG, CARD, CARD2, LINE = p["bg"], p["card"], p["card2"], p["line"]
    TEXT, MUTED = p["text"], p["muted"]
    ACCENT, ACCENT2 = p["accent"], p["accent2"]
    DANGER, WARN, GRID = p["danger"], p["warn"], p["grid"]
    PLOTLY_THEME = dict(
        template=p["template"],
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=p["text"], family="Inter, Segoe UI, sans-serif", size=13),
        margin=dict(l=20, r=20, t=64, b=70),
        colorway=[p["accent"], p["accent2"], "#a78bfa", "#ff9f6e", "#ff5d7a"],
    )
    _TAB_STYLE = {
        "backgroundColor": "transparent", "color": MUTED, "border": "none",
        "borderBottom": "2px solid transparent", "padding": "12px 18px",
        "fontWeight": "600", "fontSize": "13.5px",
    }
    _TAB_SELECTED_STYLE = {**_TAB_STYLE, "color": ACCENT,
                           "borderBottom": f"2px solid {ACCENT}"}
    _LABEL_STYLE = {"color": ACCENT, "fontSize": "11px", "fontWeight": "700",
                    "textTransform": "uppercase", "letterSpacing": "1px"}


_aplicar_tema(cargar_config().get("tema", "oscuro"))


# estilo de titulo (alineado a la izquierda, compacto) para pasar como title=...
def _titulo(texto: str) -> dict:
    return dict(text=texto, font=dict(size=15, color=TEXT), x=0.012, xanchor="left",
                y=0.97, yanchor="top")

# ─────────────────────────────────────────────────────────────────────────────
# Datos de demostración (se usan cuando historial.csv está vacío)
# ─────────────────────────────────────────────────────────────────────────────
_PESOS_BASE: dict[str, float] = {
    "Press Militar Mancuernas (Sentado)":  22.5,
    "Remo con Mancuerna a 1 Mano":         15.0,
    "Press de Banca con Barra":            40.0,
    "Jalon al Pecho Agarre Amplio":        42.5,
    "Sentadilla Libre con Barra":          60.0,
    "Peso Muerto Rumano con Mancuernas":   30.0,
    "Prensa de Piernas 45 grados":         80.0,
    "Zancadas con Mancuernas":             16.0,
    "Press Arnold con Mancuernas":         20.0,
    "Remo en Polea Baja Agarre Neutro":    35.0,
    "Face Pull Polea Alta":                20.0,
    "Hip Thrust con Barra":                70.0,
    "Curl de Isquios Tumbado (Maquina)":   25.0,
    "Elevaciones Laterales Polea Baja":     8.0,
    "Curl con Barra EZ":                   20.0,
    "Extension Triceps Polea Cuerda":      18.0,
    "Extensiones de Cuadriceps (Maquina)": 35.0,
    "Curl de Isquios Sentado (Maquina)":   30.0,
}

_SESIONES_DEMO = [
    (0, "Torso A - Fuerza",   "A - Fuerza maxima", [
        ("Press Militar Mancuernas (Sentado)", "Top Set",     1, 6, 8, 3),
        ("Press Militar Mancuernas (Sentado)", "Back-off",    2, 8, 12, 2),
        ("Remo con Mancuerna a 1 Mano",        "Top Set",     1, 6, 8, 3),
        ("Press de Banca con Barra",            "Tradicional", 3, 8, 12, 3),
        ("Jalon al Pecho Agarre Amplio",        "AMRAP",       1, 10, 12, 3),
        ("Elevaciones Laterales Polea Baja",    "Rest-Pause",  2, 12, 15, 2),
        ("Curl con Barra EZ",                   "Rest-Pause",  2, 12, 15, 2),
        ("Extension Triceps Polea Cuerda",      "Rest-Pause",  2, 12, 15, 2),
    ]),
    (1, "Pierna A - Fuerza",  "A - Fuerza maxima", [
        ("Sentadilla Libre con Barra",          "Top Set",     1, 5, 8, 3),
        ("Sentadilla Libre con Barra",          "Back-off",    2, 8, 12, 2),
        ("Peso Muerto Rumano con Mancuernas",   "Tradicional", 3, 10, 12, 3),
        ("Prensa de Piernas 45 grados",         "AMRAP",       3, 10, 15, 3),
        ("Zancadas con Mancuernas",             "Tradicional", 3, 12, 12, 3),
        ("Extensiones de Cuadriceps (Maquina)", "Rest-Pause",  2, 12, 15, 2),
        ("Curl de Isquios Sentado (Maquina)",   "Rest-Pause",  2, 12, 15, 2),
    ]),
    (4, "Torso Bombeo",       "B - Volumen", [
        ("Press Arnold con Mancuernas",         "Top Set",     1, 6, 8, 3),
        ("Press Arnold con Mancuernas",         "Back-off",    2, 10, 12, 2),
        ("Remo en Polea Baja Agarre Neutro",    "AMRAP",       3, 10, 12, 3),
        ("Face Pull Polea Alta",                "Tradicional", 3, 15, 15, 3),
    ]),
    (5, "Pierna Bombeo",      "B - Volumen", [
        ("Hip Thrust con Barra",                "Top Set",     1, 6, 8, 3),
        ("Peso Muerto Rumano con Mancuernas",   "Top Set",     1, 5, 8, 2),
        ("Prensa de Piernas 45 grados",         "Drop Set",    3, 10, 15, 3),
        ("Curl de Isquios Tumbado (Maquina)",   "Drop Set",    2, 12, 15, 2),
    ]),
]


def _generar_demo() -> pd.DataFrame:
    rng = random.Random(42)
    registros: list[dict] = []
    progreso = dict(_PESOS_BASE)
    id_c = 1
    lunes_inicio = date.today() - timedelta(weeks=8)
    lunes_inicio -= timedelta(days=lunes_inicio.weekday())

    for sem in range(8):
        lunes = lunes_inicio + timedelta(weeks=sem)
        sem_str = lunes.isoformat()
        for dia_off, nombre_dia, bloque, ejercicios in _SESIONES_DEMO:
            fecha = lunes + timedelta(days=dia_off)
            for ejercicio, tecnica, orden, rmin, rmax, nseries in ejercicios:
                peso = progreso.get(ejercicio, 10.0)
                for ns in range(1, nseries + 1):
                    reps = rng.randint(rmin, rmax)
                    rpe  = round(rng.uniform(7.2, 9.4), 1)
                    registros.append({
                        "id": id_c, "fecha_entreno": fecha.isoformat(),
                        "ejercicio": ejercicio, "tecnica": tecnica,
                        "numero_serie": ns, "peso_kg": round(peso, 2),
                        "reps_hechas": reps, "rpe": rpe,
                        "tonelaje_serie": round(peso * reps, 2),
                        "semana_inicio": sem_str, "dia_semana": dia_off + 1,
                        "nombre_dia": nombre_dia, "bloque": bloque,
                        "series_objetivo": nseries, "reps_min": rmin,
                        "reps_max": rmax, "peso_sugerido": round(peso + 1.25, 2),
                    })
                    id_c += 1
                # progresión semanal
                if rng.random() < 0.7:
                    micro = 2.5 if "Barra" in ejercicio or "Prensa" in ejercicio else 1.25
                    progreso[ejercicio] = round(progreso.get(ejercicio, 10.0) + micro, 2)
    return pd.DataFrame(registros)


# ─────────────────────────────────────────────────────────────────────────────
# Carga de datos
# ─────────────────────────────────────────────────────────────────────────────
def _cargar_df() -> tuple[pd.DataFrame, str]:
    """Devuelve (df, estado) con estado in {"real", "vacio", "demo"}.

    - "real":  hay datos en historial.csv.
    - "vacio": no hay datos todavía (se muestra un estado vacío, no demo).
    - "demo":  solo si se arranca con la variable de entorno GYM_DEMO=1.
    """
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        for col in ("peso_kg", "reps_hechas", "rpe", "tonelaje_serie"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["fecha_entreno"] = pd.to_datetime(df["fecha_entreno"], errors="coerce")
        df = df.dropna(subset=["fecha_entreno", "ejercicio"])
        if not df.empty:
            return df, "real"

    if os.getenv("GYM_DEMO"):
        df = _generar_demo()
        df["fecha_entreno"] = pd.to_datetime(df["fecha_entreno"])
        return df, "demo"

    return pd.DataFrame(), "vacio"


# ─────────────────────────────────────────────────────────────────────────────
# Métricas
# ─────────────────────────────────────────────────────────────────────────────
def _kpis(df: pd.DataFrame) -> dict:
    sesiones   = int(df["fecha_entreno"].dt.date.nunique())
    tonelaje   = float(df["tonelaje_serie"].sum())
    rpe_prom   = float(df["rpe"].mean())
    ejercicios = int(df["ejercicio"].nunique())

    fechas = sorted(df["fecha_entreno"].dt.date.unique())
    racha  = 1
    for i in range(len(fechas) - 1, 0, -1):
        if (fechas[i] - fechas[i - 1]).days == 1:
            racha += 1
        else:
            break

    mejor_ej = df.groupby("ejercicio")["tonelaje_serie"].sum().idxmax() if not df.empty else "—"
    return dict(
        sesiones=sesiones,
        tonelaje=f"{tonelaje:,.0f} kg",
        rpe_prom=f"{rpe_prom:.1f} / 10",
        racha=racha,
        ejercicios=ejercicios,
        mejor_ej=mejor_ej,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Gráficos
# ─────────────────────────────────────────────────────────────────────────────
_LEGEND_BOTTOM = dict(orientation="h", yanchor="top", y=-0.18, x=0,
                      bgcolor="rgba(0,0,0,0)", font=dict(size=12))


def _fig_vacia(titulo: str = "Sin datos todavía") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=titulo, showarrow=False,
                       font=dict(size=14, color=MUTED), x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_layout(**{k: v for k, v in PLOTLY_THEME.items() if k != "title"},
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def _fig_progresion(df: pd.DataFrame, ejercicio: str) -> go.Figure:
    if df.empty or not ejercicio:
        return _fig_vacia("Elegí un ejercicio para ver su progresión")
    sub = df[df["ejercicio"] == ejercicio].copy()
    sub["semana"] = sub["fecha_entreno"].dt.to_period("W").dt.start_time
    ton  = sub.groupby("semana")["tonelaje_serie"].sum().reset_index()
    pmax = sub.groupby("semana")["peso_kg"].max().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ton["semana"], y=ton["tonelaje_serie"],
        name="Tonelaje semanal", marker_color=ACCENT2,
        yaxis="y2", opacity=0.35,
    ))
    fig.add_trace(go.Scatter(
        x=pmax["semana"], y=pmax["peso_kg"],
        name="Peso máximo",
        line=dict(color=ACCENT, width=3, shape="spline"),
        mode="lines+markers", marker=dict(size=9, color=ACCENT),
    ))
    fig.update_layout(
        **PLOTLY_THEME,
        title=_titulo(f"Progresión — {ejercicio}"),
        yaxis=dict(title="Peso máximo (kg)", gridcolor=GRID, zeroline=False),
        yaxis2=dict(title="Tonelaje (kg)", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)", zeroline=False),
        legend=_LEGEND_BOTTOM,
        hovermode="x unified",
    )
    return fig


def _fig_records(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _fig_vacia()
    prs = df.groupby("ejercicio")["peso_kg"].max().sort_values().tail(14)
    maxv = prs.max() if len(prs) else 0
    colors = [ACCENT if v == maxv and maxv > 0 else "#2c6f6a" for v in prs.values]
    fig = go.Figure(go.Bar(
        x=prs.values, y=prs.index, orientation="h",
        marker_color=colors, marker_line_width=0,
        text=[f"  {v:.1f} kg" for v in prs.values],
        textposition="outside", textfont=dict(color=TEXT),
    ))
    theme_records = {**PLOTLY_THEME, "margin": dict(l=20, r=90, t=64, b=30)}
    fig.update_layout(
        **theme_records,
        title=_titulo("Records Personales (PR) — peso máximo por ejercicio"),
        xaxis=dict(title="kg", gridcolor=GRID),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    return fig


def _fig_rpe(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _fig_vacia()
    df2 = df.copy()
    df2["semana"] = df2["fecha_entreno"].dt.to_period("W").dt.start_time
    sem = df2.groupby("semana")["rpe"].mean().reset_index()

    marker_colors = [
        DANGER if r >= 9.0 else (WARN if r >= 8.5 else ACCENT)
        for r in sem["rpe"]
    ]
    fig = go.Figure()
    fig.add_hrect(y0=9.0, y1=10.5, fillcolor="rgba(255,93,122,0.10)",
                  line_width=0, annotation_text="⚠ Zona deload",
                  annotation_position="top left",
                  annotation_font=dict(color=DANGER, size=11))
    fig.add_hrect(y0=7.5, y1=9.0, fillcolor="rgba(0,224,181,0.06)", line_width=0,
                  annotation_text="✓ Zona óptima",
                  annotation_position="bottom right",
                  annotation_font=dict(color=ACCENT, size=11))
    fig.add_trace(go.Scatter(
        x=sem["semana"], y=sem["rpe"],
        mode="lines+markers+text",
        line=dict(color=ACCENT, width=2.5, shape="spline"),
        marker=dict(size=11, color=marker_colors, line=dict(width=0)),
        text=[f"{v:.1f}" for v in sem["rpe"]],
        textposition="top center",
        textfont=dict(size=11, color=TEXT),
    ))
    fig.update_layout(
        **PLOTLY_THEME,
        title=_titulo("Estado del SNC — RPE promedio semanal"),
        yaxis=dict(title="RPE", range=[6, 11], dtick=1, gridcolor=GRID),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    return fig


def _fig_tonelaje_semana(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _fig_vacia()
    df2 = df.copy()
    df2["semana"] = df2["fecha_entreno"].dt.to_period("W").dt.start_time
    ton = df2.groupby("semana")["tonelaje_serie"].sum().reset_index()
    fig = go.Figure(go.Scatter(
        x=ton["semana"], y=ton["tonelaje_serie"],
        mode="lines+markers", fill="tozeroy",
        fillcolor="rgba(0,224,181,0.12)",
        line=dict(color=ACCENT, width=2.5, shape="spline"),
        marker=dict(size=7, color=ACCENT),
        text=[f"{v:,.0f} kg" for v in ton["tonelaje_serie"]],
        hovertemplate="%{x|%d %b}<br>Tonelaje: %{text}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_THEME,
        title=_titulo("Tonelaje total por semana"),
        yaxis=dict(title="kg", gridcolor=GRID),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    return fig


def _fig_volumen_bloque(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _fig_vacia()
    vol = (
        df.groupby("bloque")["tonelaje_serie"].sum()
        .sort_values(ascending=False)
    )
    palette = [ACCENT, ACCENT2, "#a78bfa", "#ff9f6e", "#ff5d7a"]
    fig = go.Figure(go.Bar(
        x=vol.index, y=vol.values,
        marker_color=palette[:len(vol)], marker_line_width=0,
        text=[f"{v:,.0f} kg" for v in vol.values],
        textposition="outside", textfont=dict(color=MUTED, size=11),
    ))
    fig.update_layout(
        **PLOTLY_THEME,
        title=_titulo("Distribución de volumen por bloque"),
        yaxis=dict(title="Tonelaje (kg)", gridcolor=GRID),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", tickangle=-15),
        showlegend=False,
    )
    return fig


def _fig_frecuencia(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _fig_vacia()
    df2 = df.copy()
    df2["semana"] = df2["fecha_entreno"].dt.to_period("W").dt.start_time
    frec = df2.groupby("semana")["fecha_entreno"].apply(
        lambda x: x.dt.date.nunique()
    ).reset_index()
    frec.columns = ["semana", "sesiones"]
    fig = go.Figure(go.Bar(
        x=frec["semana"], y=frec["sesiones"],
        marker_color=ACCENT, opacity=0.85, marker_line_width=0,
        text=frec["sesiones"], textposition="outside",
        textfont=dict(color=MUTED, size=11),
    ))
    fig.update_layout(
        **PLOTLY_THEME,
        title=_titulo("Frecuencia de entrenamiento semanal"),
        yaxis=dict(title="Sesiones", dtick=1, gridcolor=GRID),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Tabla de logbook
# ─────────────────────────────────────────────────────────────────────────────
def _tabla_logbook(df: pd.DataFrame):
    if df.empty:
        return html.Div("Sin entrenos registrados todavía.",
                        style={"color": MUTED, "fontSize": "13px", "padding": "8px 0"})
    cols_show = ["fecha_entreno", "nombre_dia", "bloque", "ejercicio", "tecnica",
                 "numero_serie", "peso_kg", "reps_hechas", "rpe", "tonelaje_serie"]
    cols_show = [c for c in cols_show if c in df.columns]
    df2 = df[cols_show].copy()
    df2["fecha_entreno"] = df2["fecha_entreno"].dt.strftime("%Y-%m-%d")

    return dash_table.DataTable(
        data=df2.to_dict("records"),
        columns=[{"name": c.replace("_", " ").title(), "id": c} for c in cols_show],
        filter_action="native",
        sort_action="native",
        page_action="native",
        page_size=20,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": CARD2, "color": ACCENT,
                      "fontWeight": "600", "border": "1px solid #2a2d3e"},
        style_cell={"backgroundColor": CARD, "color": TEXT,
                    "border": "1px solid #2a2d3e", "fontSize": "13px",
                    "padding": "8px 12px", "textAlign": "left"},
        style_filter={"backgroundColor": CARD2, "color": TEXT},
        style_data_conditional=[
            {"if": {"filter_query": "{rpe} >= 9"},
             "backgroundColor": "rgba(255,77,109,0.12)", "color": DANGER},
            {"if": {"row_index": "odd"},
             "backgroundColor": "#1d2133"},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tabla del plan próxima semana
# ─────────────────────────────────────────────────────────────────────────────
def _tabla_plan(df: pd.DataFrame) -> dash_table.DataTable | html.Div:
    try:
        from planificar import generar_filas, ultimas_y_records, lunes_objetivo, semana_mesociclo
        from dotenv import load_dotenv

        load_dotenv()
        inicio_env = os.getenv("MES_INICIO")
        objetivo = (
            date.fromisoformat(os.environ["SEMANA_SIGUIENTE"])
            if os.getenv("SEMANA_SIGUIENTE")
            else lunes_objetivo()
        )
        inicio = date.fromisoformat(inicio_env) if inicio_env else objetivo
        semana = semana_mesociclo(objetivo, inicio)
        filas = generar_filas(df, objetivo.isoformat(), semana)
    except Exception as exc:
        return html.Div([
            html.P(f"No se pudo calcular el plan: {exc}",
                   style={"color": WARN, "marginBottom": "8px"}),
            html.P("Asegurate de que .env tenga API_BASE_URL y MES_INICIO, "
                   "o que historial.csv tenga datos reales.",
                   style={"color": MUTED, "fontSize": "13px"}),
        ])

    cols = ["dia_semana", "nombre_dia", "bloque", "ejercicio", "tecnica",
            "series_objetivo", "reps_min", "reps_max", "descanso_seg", "peso_sugerido", "notas"]
    df_plan = pd.DataFrame(filas)[cols]

    return dash_table.DataTable(
        data=df_plan.to_dict("records"),
        columns=[{"name": c.replace("_", " ").title(), "id": c} for c in cols],
        filter_action="native",
        sort_action="native",
        page_action="native",
        page_size=25,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": CARD2, "color": ACCENT,
                      "fontWeight": "600", "border": "1px solid #2a2d3e"},
        style_cell={"backgroundColor": CARD, "color": TEXT,
                    "border": "1px solid #2a2d3e", "fontSize": "13px",
                    "padding": "8px 12px"},
        style_data_conditional=[
            {"if": {"filter_query": '{tecnica} contains "Top Set"'},
             "color": ACCENT, "fontWeight": "600"},
            {"if": {"row_index": "odd"},
             "backgroundColor": "#1d2133"},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Componentes de layout reutilizables
# ─────────────────────────────────────────────────────────────────────────────
def _card(children, style: dict | None = None) -> html.Div:
    base = {"padding": "22px"}
    if style:
        base.update(style)
    return html.Div(children, className="gym-card", style=base)


def _kpi_card(titulo: str, valor: str, icono: str = "") -> html.Div:
    return html.Div([
        html.Div(icono, style={"fontSize": "22px", "marginBottom": "8px", "opacity": 0.9}),
        html.Div(valor, style={"fontSize": "27px", "fontWeight": "800", "color": TEXT,
                                "letterSpacing": "-0.5px", "lineHeight": "1"}),
        html.Div(titulo, style={"fontSize": "10.5px", "color": MUTED, "marginTop": "8px",
                                 "textTransform": "uppercase", "letterSpacing": "1.2px",
                                 "fontWeight": "600"}),
    ], className="gym-kpi", style={
        "padding": "20px 22px", "textAlign": "center", "flex": "1", "minWidth": "140px",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Pestaña de configuración (cambiar enfoque sin tocar código)
# ─────────────────────────────────────────────────────────────────────────────
_DD_STYLE = {"marginTop": "6px"}


def _tab_config_children(estado: str = "real") -> html.Div:
    cfg = cargar_config()
    return html.Div([
        _card([
            html.Div("Configura tu entrenamiento",
                     style={"color": TEXT, "fontWeight": "700", "fontSize": "16px",
                            "marginBottom": "4px"}),
            html.Div("Elegí el enfoque, el split y tus músculos rezagados. El plan se "
                     "reconstruye con las reglas de la teoría (patrones, bloques A/B/C, "
                     "técnicas, descansos, prioridad de orden y rotación).",
                     style={"color": MUTED, "fontSize": "13px", "marginBottom": "20px"}),

            html.Div([
                # Enfoque
                html.Div([
                    html.Label("Enfoque (objetivo)", style=_LABEL_STYLE),
                    dcc.Dropdown(
                        id="cfg-enfoque", clearable=False, className="dash-dropdown",
                        style=_DD_STYLE,
                        options=[{"label": e.nombre, "value": k} for k, e in ENFOQUES.items()],
                        value=cfg["enfoque"],
                    ),
                ], style={"flex": "1", "minWidth": "240px"}),

                # Split
                html.Div([
                    html.Label("Split (distribución de días)", style=_LABEL_STYLE),
                    dcc.Dropdown(
                        id="cfg-split", clearable=False, className="dash-dropdown",
                        style=_DD_STYLE,
                        options=[{"label": s.nombre, "value": k} for k, s in SPLITS.items()],
                        value=cfg["split"],
                    ),
                ], style={"flex": "1", "minWidth": "240px"}),

                # Peso corporal
                html.Div([
                    html.Label("Peso corporal (kg)", style=_LABEL_STYLE),
                    dcc.Input(id="cfg-peso", type="number", value=cfg.get("peso_corporal", 75),
                              min=40, max=200, step=1,
                              style={"width": "100%", "padding": "9px 12px", "marginTop": "6px",
                                     "boxSizing": "border-box", "height": "42px"}),
                ], style={"flex": "1", "minWidth": "140px"}),

                # Duración objetivo
                html.Div([
                    html.Label("Duración por sesión", style=_LABEL_STYLE),
                    dcc.Dropdown(
                        id="cfg-duracion", clearable=False, className="dash-dropdown",
                        style=_DD_STYLE,
                        options=[
                            {"label": "~60 min (corto)", "value": 60},
                            {"label": "~75 min", "value": 75},
                            {"label": "~90 min", "value": 90},
                            {"label": "~120 min (completo)", "value": 120},
                        ],
                        value=cfg.get("duracion_min", 90),
                    ),
                ], style={"flex": "1", "minWidth": "180px"}),
            ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap",
                      "marginBottom": "22px"}),

            html.Label("Músculos prioritarios (rezagados → reciben el estímulo máximo)",
                       style=_LABEL_STYLE),
            dcc.Checklist(
                id="cfg-prioridades",
                options=[{"label": f" {lbl}", "value": mid} for mid, lbl in MUSCULOS_PRIORIZABLES],
                value=cfg.get("prioridades", []),
                inline=True,
                style={"fontSize": "14px", "marginTop": "10px",
                       "display": "flex", "flexWrap": "wrap", "gap": "8px 4px"},
                labelStyle={"color": TEXT, "marginRight": "16px", "cursor": "pointer",
                            "display": "inline-flex", "alignItems": "center", "gap": "5px"},
            ),

            html.Button("Generar y guardar plan", id="cfg-guardar", n_clicks=0,
                        className="gym-btn", style={"marginTop": "26px"}),
        ]),

        html.Div(id="cfg-resultado", style={"marginTop": "16px"}),
    ], style={"padding": "20px 0"})


def _resumen_enfoque(cfg: dict) -> html.Div:
    enf = ENFOQUES[cfg["enfoque"]]
    split = SPLITS[cfg["split"]]
    prioridades = ", ".join(
        lbl for mid, lbl in MUSCULOS_PRIORIZABLES if mid in cfg.get("prioridades", [])
    ) or "ninguno"
    return _card([
        html.Div(f"✓ Plan guardado: {enf.nombre}", style={"color": ACCENT, "fontWeight": "700",
                 "fontSize": "15px", "marginBottom": "8px"}),
        html.P(enf.descripcion, style={"color": TEXT, "fontSize": "13px", "marginBottom": "4px"}),
        html.P(f"Split: {split.nombre}", style={"color": MUTED, "fontSize": "13px", "margin": "2px 0"}),
        html.P(f"Prioridades: {prioridades}", style={"color": MUTED, "fontSize": "13px", "margin": "2px 0"}),
        html.Div([
            html.Span("🥗 Nutrición  ", style={"color": ACCENT, "fontWeight": "600", "fontSize": "12px"}),
            html.Span(enf.macros, style={"color": TEXT, "fontSize": "12px"}),
        ], style={"marginTop": "10px", "padding": "10px 12px", "background": CARD2,
                  "borderRadius": "6px"}),
        html.P(f"💡 {enf.nota}", style={"color": MUTED, "fontSize": "12px", "marginTop": "10px",
               "fontStyle": "italic"}),
        html.P("El nuevo plan ya está activo. Mirá la pestaña «Plan semana» para verlo completo. "
               "La próxima vez que corras el motor (planificar.py) usará este enfoque.",
               style={"color": MUTED, "fontSize": "12px", "marginTop": "12px"}),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Construcción de la app
# ─────────────────────────────────────────────────────────────────────────────
def _build_layout(df: pd.DataFrame, estado: str) -> html.Div:
    vacio = df.empty
    k = _kpis(df) if not vacio else dict(sesiones=0, tonelaje="0 kg", rpe_prom="—",
                                          racha=0, ejercicios=0, mejor_ej="—")
    ejercicios_opts = [{"label": e, "value": e} for e in sorted(df["ejercicio"].unique())] \
        if not vacio else []
    default_ej = ejercicios_opts[0]["value"] if ejercicios_opts else ""

    if estado == "demo":
        banner = html.Div("⚠ Modo demostración (GYM_DEMO) — datos de ejemplo",
                          style={"background": "rgba(255,192,67,0.14)", "color": WARN,
                                 "padding": "10px 16px", "fontSize": "13px", "borderRadius": "10px",
                                 "marginBottom": "16px", "border": "1px solid rgba(255,192,67,0.3)"})
    elif vacio:
        banner = html.Div([
            html.Span("Sin datos todavía. ", style={"fontWeight": "700", "color": TEXT}),
            html.Span("Registrá entrenos en la app y pulsá «🔄 Actualizar datos» para traerlos del servidor.",
                      style={"color": MUTED}),
        ], style={"background": "rgba(24,179,255,0.10)", "padding": "12px 16px", "fontSize": "13px",
                  "borderRadius": "10px", "marginBottom": "16px",
                  "border": "1px solid rgba(24,179,255,0.25)"})
    else:
        banner = html.Div()

    kpi_row = html.Div([
        _kpi_card("Sesiones",      str(k["sesiones"]),   "🏋️"),
        _kpi_card("Tonelaje Total", k["tonelaje"],        "📦"),
        _kpi_card("RPE Promedio",  k["rpe_prom"],        "💓"),
        _kpi_card("Racha",         f"{k['racha']} días",  "🔥"),
        _kpi_card("Ejercicios",    str(k["ejercicios"]), "📋"),
    ], style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "22px"})

    tabs = dcc.Tabs(mobile_breakpoint=0, children=[
        # ── Tab 1: Resumen ──────────────────────────────────────────────────
        dcc.Tab(label="Resumen", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                html.Div([
                    _card(dcc.Graph(figure=_fig_tonelaje_semana(df), config={"displayModeBar": False}),
                          {"flex": "2", "minWidth": "300px"}),
                    _card(dcc.Graph(figure=_fig_frecuencia(df), config={"displayModeBar": False}),
                          {"flex": "1", "minWidth": "250px"}),
                ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}),

                html.Div([
                    _card(dcc.Graph(figure=_fig_volumen_bloque(df), config={"displayModeBar": False}),
                          {"flex": "1", "minWidth": "300px"}),
                    _card(dcc.Graph(figure=_fig_rpe(df), config={"displayModeBar": False}),
                          {"flex": "1", "minWidth": "300px"}),
                ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginTop": "16px"}),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab 2: Progresión ───────────────────────────────────────────────
        dcc.Tab(label="Progresión", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                html.Div([
                    html.Label("Ejercicio:", style={"color": MUTED, "fontSize": "13px",
                                                     "marginRight": "10px"}),
                    dcc.Dropdown(
                        id="dd-ejercicio",
                        options=ejercicios_opts,
                        value=default_ej,
                        clearable=False,
                        className="dash-dropdown",
                        style={"width": "420px"},
                    ),
                ], style={"display": "flex", "alignItems": "center",
                          "marginBottom": "16px", "flexWrap": "wrap", "gap": "8px"}),
                _card(dcc.Graph(id="graph-progresion",
                                figure=_fig_progresion(df, default_ej),
                                config={"displayModeBar": False})),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab 3: Records ──────────────────────────────────────────────────
        dcc.Tab(label="Records (PRs)", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                _card(dcc.Graph(figure=_fig_records(df),
                                style={"height": "560px"},
                                config={"displayModeBar": False})),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab 4: Estado SNC ───────────────────────────────────────────────
        dcc.Tab(label="Estado SNC", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                _card(dcc.Graph(figure=_fig_rpe(df), config={"displayModeBar": False})),
                html.Div([
                    _card([
                        html.Div("Zona óptima (RPE 7.5 – 9.0)",
                                 style={"color": ACCENT, "fontWeight": "600", "marginBottom": "6px"}),
                        html.P("El RPE promedio semanal debería mantenerse entre 7.5 y 9.0. "
                               "Si supera 9.0 sostenidamente por 2+ semanas, es señal de "
                               "fatiga acumulada y es conveniente planificar una semana de "
                               "descarga (Deload).", style={"color": MUTED, "fontSize": "13px"}),
                    ], {"flex": "1", "minWidth": "240px"}),
                    _card([
                        html.Div("Zona de alerta (RPE ≥ 9.0)",
                                 style={"color": DANGER, "fontWeight": "600", "marginBottom": "6px"}),
                        html.P("RPE sostenido por encima de 9 indica que el sistema nervioso "
                               "central está sobrecargado. Reducir intensidad o volumen un 40% "
                               "durante una semana (Semana 4 del mesociclo).",
                               style={"color": MUTED, "fontSize": "13px"}),
                    ], {"flex": "1", "minWidth": "240px"}),
                ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap",
                          "marginTop": "16px"}),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab 5: Logbook ──────────────────────────────────────────────────
        dcc.Tab(label="Logbook", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                _card([
                    html.P("Podés filtrar por cualquier columna haciendo clic en el "
                           "ícono de filtro. Ejemplo: escribí 'Press' en Ejercicio.",
                           style={"color": MUTED, "fontSize": "12px", "marginBottom": "12px"}),
                    _tabla_logbook(df),
                ]),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab: Configuración (cambiar enfoque) ────────────────────────────
        dcc.Tab(label="⚙ Configuración", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=_tab_config_children(estado),
        ),

        # ── Tab: Plan próxima semana ────────────────────────────────────────
        dcc.Tab(label="Plan semana", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                _card([
                    html.Div([
                        html.Div("Plan calculado para la próxima semana",
                                 style={"color": TEXT, "fontWeight": "600",
                                        "fontSize": "15px", "marginBottom": "4px"}),
                        html.Div("Generado por el motor de sobrecarga progresiva "
                                 "(planificar.py) usando tu historial real.",
                                 style={"color": MUTED, "fontSize": "12px",
                                        "marginBottom": "16px"}),
                    ]),
                    _tabla_plan(df),
                ]),
            ], style={"padding": "16px 0"}),
        ),
    ], style={"display": "flex", "flexWrap": "wrap", "gap": "2px",
              "borderBottom": f"1px solid {LINE}", "marginBottom": "4px"})

    estado_chip = {
        "real": ("● EN VIVO", ACCENT),
        "demo": ("● DEMO", WARN),
        "vacio": ("● SIN DATOS", MUTED),
    }[estado]

    tema = cargar_config().get("tema", "oscuro")
    btn_tema = "☀️ Vista clara" if tema == "oscuro" else "🌙 Vista oscura"

    contenido = html.Div([
        dcc.Store(id="reload-trigger"),
        dcc.Store(id="tema-trigger"),
        html.Div(id="reload-dummy", style={"display": "none"}),
        html.Div(id="tema-dummy", style={"display": "none"}),

        # Header
        html.Div([
            html.Div([
                html.Div("🏋️", style={"fontSize": "26px",
                                       "background": f"linear-gradient(135deg,{ACCENT},{ACCENT2})",
                                       "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent"}),
                html.Div([
                    html.Div("Gym Tracker", style={"color": TEXT, "margin": "0",
                                                   "fontSize": "21px", "fontWeight": "800",
                                                   "letterSpacing": "-0.5px", "lineHeight": "1"}),
                    html.Span("Panel de Inteligencia Deportiva",
                              style={"color": MUTED, "fontSize": "12px"}),
                ]),
            ], style={"display": "flex", "alignItems": "center", "gap": "12px"}),

            html.Div([
                html.Button(btn_tema, id="btn-tema", n_clicks=0,
                            className="gym-btn-ghost", style={"marginRight": "10px"}),
                html.Button("🔄 Actualizar datos", id="btn-refresh", n_clicks=0,
                            className="gym-btn-ghost", style={"marginRight": "14px"}),
                html.Span(estado_chip[0], style={"color": estado_chip[1], "fontSize": "11px",
                                                  "fontWeight": "700", "letterSpacing": "0.5px"}),
            ], style={"display": "flex", "alignItems": "center", "flexWrap": "wrap"}),
        ], style={
            "display": "flex", "justifyContent": "space-between", "alignItems": "center",
            "marginBottom": "22px", "paddingBottom": "18px",
            "borderBottom": f"1px solid {LINE}",
        }),

        html.Div(id="refresh-status"),

        banner,
        kpi_row,
        tabs,
    ], style={"padding": "24px 32px", "maxWidth": "1500px", "margin": "0 auto",
               "fontFamily": "Inter, Segoe UI, sans-serif"})

    # Wrapper full-bleed: aplica el fondo del tema y la clase que cascadea las
    # variables CSS (.tema-claro) a todos los descendientes.
    return html.Div(contenido, className=f"tema-{tema}",
                    style={"backgroundColor": BG, "minHeight": "100vh"})


# ─────────────────────────────────────────────────────────────────────────────
# App Dash — layout como función: re-lee los datos en cada carga de página
# ─────────────────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    title="Gym Tracker — Dashboard",
    update_title=None,
    suppress_callback_exceptions=True,
)


def _serve_layout() -> html.Div:
    _aplicar_tema(cargar_config().get("tema", "oscuro"))
    df, estado = _cargar_df()
    return _build_layout(df, estado)


app.layout = _serve_layout


@callback(
    Output("graph-progresion", "figure"),
    Input("dd-ejercicio", "value"),
)
def _update_progresion(ejercicio: str) -> go.Figure:
    df, _ = _cargar_df()
    return _fig_progresion(df, ejercicio)


@callback(
    Output("refresh-status", "children"),
    Output("reload-trigger", "data"),
    Input("btn-refresh", "n_clicks"),
    prevent_initial_call=True,
)
def _refrescar_datos(n_clicks):
    """Descarga el historial real del servidor (mismo pipeline que exportar_local.py)."""
    import time
    try:
        import exportar_local
        exportar_local.main()
        df, estado = _cargar_df()
        msg = html.Div(f"✓ Datos actualizados: {len(df)} filas descargadas del servidor. Recargando…",
                       style={"background": "rgba(0,224,181,0.12)", "color": ACCENT,
                              "padding": "10px 16px", "borderRadius": "10px", "marginBottom": "16px",
                              "fontSize": "13px", "border": "1px solid rgba(0,224,181,0.3)"})
        return msg, time.time()
    except Exception as exc:  # noqa: BLE001
        msg = html.Div(f"⚠ No se pudo actualizar: {exc}. Revisá tu conexión y el .env.",
                       style={"background": "rgba(255,93,122,0.12)", "color": DANGER,
                              "padding": "10px 16px", "borderRadius": "10px", "marginBottom": "16px",
                              "fontSize": "13px", "border": "1px solid rgba(255,93,122,0.3)"})
        from dash import no_update
        return msg, no_update


# Recarga la página cuando el refresh trae datos nuevos (para repintar todos los gráficos)
app.clientside_callback(
    "function(t){ if(t){ setTimeout(function(){ window.location.reload(); }, 900); } return ''; }",
    Output("reload-dummy", "children"),
    Input("reload-trigger", "data"),
    prevent_initial_call=True,
)


@callback(
    Output("tema-trigger", "data"),
    Input("btn-tema", "n_clicks"),
    prevent_initial_call=True,
)
def _cambiar_tema(n_clicks):
    """Alterna entre tema oscuro y claro, lo guarda y dispara la recarga."""
    import time
    actual = cargar_config().get("tema", "oscuro")
    guardar_config({"tema": "claro" if actual == "oscuro" else "oscuro"})
    return time.time()


# Recarga inmediata al cambiar de tema
app.clientside_callback(
    "function(t){ if(t){ window.location.reload(); } return ''; }",
    Output("tema-dummy", "children"),
    Input("tema-trigger", "data"),
    prevent_initial_call=True,
)


@callback(
    Output("cfg-resultado", "children"),
    Input("cfg-guardar", "n_clicks"),
    State("cfg-enfoque", "value"),
    State("cfg-split", "value"),
    State("cfg-prioridades", "value"),
    State("cfg-peso", "value"),
    State("cfg-duracion", "value"),
    prevent_initial_call=True,
)
def _guardar_enfoque(n_clicks, enfoque, split, prioridades, peso, duracion):
    cfg = {
        "enfoque": enfoque,
        "split": split,
        "prioridades": prioridades or [],
        "peso_corporal": peso or 75,
        "duracion_min": duracion or 90,
    }
    guardar_config(cfg)
    # validar que el plan se genera sin errores con la nueva config
    try:
        plan = generar_plan(cfg)
        n_ej = len([f for f in plan if f.tecnica])
    except Exception as exc:  # noqa: BLE001
        return _card([html.Div(f"⚠ Error al generar el plan: {exc}",
                               style={"color": DANGER})])
    resumen = _resumen_enfoque(cfg)
    return html.Div([
        resumen,
        html.Div(f"Plan generado: {n_ej} ejercicios distribuidos en la semana.",
                 style={"color": MUTED, "fontSize": "12px", "marginTop": "10px",
                        "textAlign": "center"}),
    ])


def _abrir_navegador(url: str = "http://127.0.0.1:8050", retraso: float = 1.5) -> None:
    """Abre el navegador por defecto unos segundos despues, cuando el server ya esta listo."""
    import threading
    import webbrowser

    threading.Timer(retraso, lambda: webbrowser.open(url)).start()


if __name__ == "__main__":
    _df_init, _estado_init = _cargar_df()
    print(f"\n  Gym Tracker Dashboard")
    print(f"  Estado de datos: {_estado_init} ({len(_df_init)} filas)")
    print(f"  Abriendo en http://127.0.0.1:8050\n")
    _abrir_navegador()
    app.run(debug=False, host="127.0.0.1", port=8050)
