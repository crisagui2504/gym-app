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
import plotly.io as pio
from dash import Dash, Input, Output, State, dash_table, dcc, html, callback

from config_usuario import cargar_config, guardar_config
from enfoques import ENFOQUES, SPLITS, MUSCULOS_PRIORIZABLES, EQUIPOS_FILTRABLES
from generador import generar_plan
import nutricion

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de diseño (paleta oscura que combina con la app Angular)
# ─────────────────────────────────────────────────────────────────────────────
CSV_PATH = pathlib.Path(__file__).resolve().parent / "historial.csv"

# ── Paletas de tema (oscuro / claro) ─────────────────────────────────────────
# Misma paleta y tipografias que la app del movil: violeta #7D51FE / #5920FF,
# lima #AAFF00, verde #7AB800, negro #141414, gris #333333, blanco #FFFFFF y
# gris claro #F2F2F3. Lima = accion / dato principal; violeta = estructura.
# En tema claro el lima no sirve como texto ni linea sobre blanco: alli el acento
# de texto es el violeta intenso y el lima se reserva para rellenos.
TEMAS = {
    "oscuro": dict(bg="#141414", card="#1e1e1e", card2="#2a2a2a", line="#333333",
                   text="#ffffff", muted="#a3a3ab", accent="#aaff00", accent2="#7d51fe",
                   danger="#ff6b6b", warn="#ffc043", grid="#2a2a2a", template="plotly_dark"),
    "claro":  dict(bg="#f2f2f3", card="#ffffff", card2="#ebebed", line="#e0e0e4",
                   text="#141414", muted="#5c5c66", accent="#5920ff", accent2="#7ab800",
                   danger="#e5484d", warn="#b26b00", grid="#e6e6ea", template="plotly_white"),
}
FUENTE_TEXTO = "Encode Sans, Segoe UI, sans-serif"
FUENTE_DISPLAY = "Anton, Impact, Arial Narrow, sans-serif"


# plantilla extra que se suma al tema: ejes fijos y sin arrastre en TODAS las graficas
pio.templates["gym_fijo"] = go.layout.Template(layout=dict(
    dragmode=False, xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True)))


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
        template=p["template"] + "+gym_fijo",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=p["text"], family=FUENTE_TEXTO, size=13),
        margin=dict(l=20, r=20, t=64, b=70),
        colorway=[p["accent"], p["accent2"], "#7ab800", "#5920ff", "#ff6b6b"],
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
# ─────────────────────────────────────────────────────────────────────────────
# MODO DEMO (oculto): enlace invisible en el titulo -> /demo pone una cookie y
# todo el dashboard usa los datos del atleta virtual (demo_motor.py, con el tipo de entreno que elijas). Nada se
# escribe: los callbacks que guardan devuelven un aviso. /demo/salir lo apaga.
# ─────────────────────────────────────────────────────────────────────────────
COOKIE_DEMO = "gym_demo"
COOKIE_DEMO_CFG = "gym_demo_cfg"     # el tipo de entreno elegido DENTRO de la demo


def _demo_cfg() -> dict:
    """Config de la demo (cookie "enfoque|split|duracion|prio1.prio2"). Nunca
    toca config_usuario.json. Sin comillas, comas ni espacios: asi la cookie
    se lee igual en cualquier navegador y version de werkzeug."""
    import demo_motor
    try:
        from flask import request
        partes = (request.cookies.get(COOKIE_DEMO_CFG) or "").split("|")
    except RuntimeError:          # sin peticion (arranque, pruebas)
        partes = []
    if len(partes) != 4:
        return demo_motor.normalizar({})
    return demo_motor.normalizar({"enfoque": partes[0], "split": partes[1], "duracion": partes[2],
                                  "prioridades": [x for x in partes[3].split(".") if x]})


def _cookie_demo_cfg(cfg: dict) -> str:
    return "|".join([cfg["enfoque"], cfg["split"], str(cfg["duracion_min"]), ".".join(cfg["prioridades"])])


def _es_demo() -> bool:
    try:
        from flask import request
        return request.cookies.get(COOKIE_DEMO) == "1"
    except RuntimeError:          # sin peticion (arranque, pruebas)
        return False


def _df_demo() -> pd.DataFrame:
    import demo_motor
    from planificar import sanear_historial
    return sanear_historial(demo_motor.historial_dashboard(_demo_cfg()))


def _aviso_demo(texto: str = "Modo demo: los datos son simulados y no se guarda nada.") -> html.Div:
    return html.Div(texto, style={"background": "rgba(125,81,254,0.14)", "color": TEXT, "padding": "10px 16px",
                                  "borderRadius": "10px", "fontSize": "13px", "marginBottom": "16px",
                                  "border": "1px dashed #7d51fe"})


def _cargar_df() -> tuple[pd.DataFrame, str]:
    """Devuelve (df, estado) con estado in {"real", "vacio", "demo"}.

    - "real":  hay datos en historial.csv.
    - "vacio": no hay datos todavía (se muestra un estado vacío, no demo).
    - "demo":  solo si se arranca con la variable de entorno GYM_DEMO=1.
    """
    if _es_demo():
        return _df_demo(), "demo"
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        for col in ("peso_kg", "reps_hechas", "rpe", "tonelaje_serie"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["fecha_entreno"] = pd.to_datetime(df["fecha_entreno"], errors="coerce")
        df = df.dropna(subset=["fecha_entreno", "ejercicio"])
        # mismo saneamiento que el motor: sin el, un typo (300 en vez de 30)
        # disparaba la grafica de tonelaje y los "Descanso Activo" registrados
        # contaban como sesiones en los KPI
        from planificar import sanear_historial
        df = sanear_historial(df)
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


def _con_e1rm(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega la columna e1RM (Epley: peso × (1 + reps/30)), la medida real de
    fuerza: 27.5 kg × 8 es más fuerza que 30 kg × 4 aunque pese menos."""
    out = df.copy()
    reps = out["reps_hechas"].clip(upper=15)  # Epley pierde precisión a reps altas
    out["e1rm"] = out["peso_kg"] * (1 + reps / 30)
    out.loc[out["peso_kg"] <= 0, "e1rm"] = 0.0  # peso corporal: sin e1RM
    return out


def _fig_progresion(df: pd.DataFrame, ejercicio: str) -> go.Figure:
    if df.empty or not ejercicio:
        return _fig_vacia("Elige un ejercicio para ver su progresión")
    sub = _con_e1rm(df[df["ejercicio"] == ejercicio].copy())
    sub["semana"] = sub["fecha_entreno"].dt.to_period("W").dt.start_time
    ton  = sub.groupby("semana")["tonelaje_serie"].sum().reset_index()
    pmax = sub.groupby("semana")["peso_kg"].max().reset_index()
    emax = sub.groupby("semana")["e1rm"].max().reset_index()

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
    if emax["e1rm"].max() > 0:
        fig.add_trace(go.Scatter(
            x=emax["semana"], y=emax["e1rm"],
            name="e1RM estimado (Epley)",
            line=dict(color=WARN, width=2.5, dash="dot", shape="spline"),
            mode="lines+markers", marker=dict(size=7, color=WARN),
        ))
    xaxis = dict(tickformat="%d/%m", gridcolor="rgba(0,0,0,0)")
    if len(ton) == 1:           # una sola semana: si no, plotly abre el eje a milisegundos
        x0 = ton["semana"].iloc[0]
        xaxis.update(range=[x0 - pd.Timedelta(days=5), x0 + pd.Timedelta(days=5)], dtick=86400000 * 7)
    fig.update_layout(
        **PLOTLY_THEME,
        title=_titulo(f"Progresión — {ejercicio}"),
        xaxis=xaxis,
        yaxis=dict(title="kg (peso máx / e1RM)", gridcolor=GRID, zeroline=False, rangemode="tozero"),
        yaxis2=dict(title="Tonelaje (kg)", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)", zeroline=False, rangemode="tozero"),
        legend=_LEGEND_BOTTOM,
        hovermode="x unified",
    )
    if sub["peso_kg"].max() <= 0:
        fig.add_annotation(text="Sus series están guardadas con 0 kg: registra el peso en la app<br>"
                                "para ver la progresión.", xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(color=MUTED, size=12))
    return fig


def _fig_records(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _fig_vacia()
    de = _con_e1rm(df)
    de = de[(de["e1rm"] > 0) & (de["reps_hechas"] > 0)]   # una serie de 0 reps no es un record
    if de.empty:
        return _fig_vacia()
    prs = de.groupby("ejercicio")["e1rm"].max().sort_values().tail(14)
    # detalle de la mejor serie que produjo cada e1RM
    idx = de.groupby("ejercicio")["e1rm"].idxmax()
    detalle = de.loc[idx].set_index("ejercicio")
    maxv = prs.max() if len(prs) else 0
    colors = [ACCENT if v == maxv and maxv > 0 else "#7d51fe" for v in prs.values]
    textos = []
    for ej, v in prs.items():
        d = detalle.loc[ej]
        textos.append(f"{v:.1f} kg · {d['peso_kg']:g}×{int(d['reps_hechas'])}")
    # el nombre va ENCIMA de cada barra (no como etiqueta del eje): asi se lee
    # completo en cualquier ancho, tambien en el celular
    prs, textos = prs.iloc[::-1], textos[::-1]          # el mejor arriba
    colors = colors[::-1]
    fig = go.Figure(go.Bar(
        x=prs.values, y=list(range(len(prs))), orientation="h", width=0.5,
        marker_color=colors, marker_line_width=0,
        text=textos, textposition="inside", insidetextanchor="end",
        textfont=dict(color=["#141414" if c == "#aaff00" else "#ffffff" for c in colors], size=12),
        cliponaxis=False,
        customdata=list(prs.index), hovertemplate="%{customdata}: %{x:.1f} kg<extra></extra>",
    ))
    for i, ej in enumerate(prs.index):
        fig.add_annotation(x=0, y=i, yshift=17, xref="paper", yref="y", text=ej, showarrow=False,
                           xanchor="left", yanchor="bottom", font=dict(size=12, color=TEXT))
    fig.update_layout(
        **{**PLOTLY_THEME, "margin": dict(l=10, r=10, t=56, b=10)},
        title=_titulo("Records personales · e1RM estimado"),
        height=80 + 46 * len(prs),
        uniformtext=dict(minsize=9, mode="show"),
        xaxis=dict(visible=False, range=[0, maxv * 1.02]),
        yaxis=dict(visible=False, autorange="reversed", range=None),
        bargap=0.5,
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
    fig.add_hrect(y0=7.5, y1=9.0, fillcolor="rgba(170,255,0,0.06)", line_width=0,
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
        title=_titulo("Fatiga percibida — RPE promedio semanal"),
        yaxis=dict(title="RPE", range=[6, 11], dtick=1, gridcolor=GRID),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Volumen por músculo (series efectivas/semana vs landmarks MEV-MAV-MRV)
# ─────────────────────────────────────────────────────────────────────────────
def _fig_volumen_musculo(df: pd.DataFrame, hoy: date | None = None) -> go.Figure:
    import volumen as vol
    hoy = hoy or date.today()
    pasada, esta, proxima = vol.semanas_recientes(hoy)
    s_pas = vol.series_por_grupo(df, pasada, esta)
    s_act = vol.series_por_grupo(df, esta, proxima)
    grupos = list(vol.GRUPOS)
    fig = go.Figure()
    # banda MAV (rango productivo) y marcas de MEV / MRV por fila
    for i, g in enumerate(grupos):
        mev, lo, hi, mrv = vol.LANDMARKS[g]
        fig.add_shape(type="rect", xref="x", yref="y", x0=lo, x1=hi, y0=i - 0.42, y1=i + 0.42,
                      fillcolor="rgba(170,255,0,0.10)", line_width=0, layer="below")
        for x, c in ((mev, MUTED), (mrv, DANGER)):
            fig.add_shape(type="line", xref="x", yref="y", x0=x, x1=x, y0=i - 0.42, y1=i + 0.42,
                          line=dict(color=c, width=2, dash="dot"), layer="below")
    colores = {"bajo": MUTED, "mínimo": WARN, "productivo": ACCENT, "alto": ACCENT2, "sobre MRV": DANGER}
    fig.add_trace(go.Bar(
        y=grupos, x=[s_pas[g] for g in grupos], orientation="h", name="Semana pasada",
        marker_color=[colores[vol.zona(g, s_pas[g])] for g in grupos], marker_line_width=0,
        text=[f"{s_pas[g]:g}" for g in grupos], textposition="outside",
        textfont=dict(color=TEXT, size=11),
        hovertemplate="%{y}: %{x} series (semana pasada)<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=grupos, x=[s_act[g] for g in grupos], orientation="h", name="Esta semana (en curso)",
        marker_color="rgba(125,81,254,0.55)", marker_line_width=0,
        hovertemplate="%{y}: %{x} series (esta semana)<extra></extra>",
    ))
    fig.update_layout(
        **{**PLOTLY_THEME, "margin": dict(l=20, r=30, t=64, b=40)},
        title=_titulo("Series efectivas por músculo · semana"),
        barmode="group", bargap=0.25, height=620,
        xaxis=dict(title="series / semana", gridcolor=GRID, rangemode="tozero"),
        yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=-0.08, x=0),
    )
    return fig


def _panel_encuesta() -> html.Div | None:
    """Que cambio el motor por la encuesta de la sesion (si hay respuestas)."""
    if _es_demo():
        return None
    try:
        import feedback as fbk
        from planificar import lunes_objetivo
        from dotenv import load_dotenv
        load_dotenv()
        objetivo = lunes_objetivo()
        inicio = date.fromisoformat(os.getenv("MES_INICIO") or objetivo.isoformat())
        ajustes, dolor = fbk.ajustes_para(fbk.leer_csv(CSV_PATH.parent), objetivo, inicio)
    except Exception:  # noqa: BLE001
        return None
    if not ajustes and not dolor:
        texto = [html.P("Sin ajustes todavía: responde la encuesta al terminar cada entreno "
                        "(y el dolor muscular al empezar) y el motor moverá tus series músculo por músculo.",
                        style={"color": MUTED, "fontSize": "13px", "margin": "0"})]
    else:
        texto = [html.P(f"{'▲' if k > 0 else '▼'} {m.capitalize()}: {k:+d} series/semana",
                        style={"color": ACCENT if k > 0 else WARN, "fontWeight": "700",
                               "fontSize": "13.5px", "margin": "2px 0"})
                 for m, k in sorted(ajustes.items())]
        texto += [html.P(f"⚠ {e}: dolor articular en {n} sesión(es)"
                         + (" → se cambia por otro ejercicio" if n >= fbk.DOLOR_PARA_CAMBIAR else ""),
                         style={"color": DANGER, "fontSize": "13px", "margin": "2px 0"})
                  for e, n in sorted(dolor.items())]
    return _card([html.Div("🧭 Ajustes por tu encuesta (próxima semana)", style={
        "color": ACCENT, "fontWeight": "700", "fontSize": "14px", "marginBottom": "6px"}), *texto],
        {"marginBottom": "16px"})


# ─────────────────────────────────────────────────────────────────────────────
# Peso corporal — registro local + tendencia (la báscula pilota las kcal)
# ─────────────────────────────────────────────────────────────────────────────
PESO_CSV = pathlib.Path(__file__).resolve().parent / "peso_corporal.csv"


def _cargar_peso() -> pd.DataFrame:
    if not PESO_CSV.exists():
        return pd.DataFrame(columns=["fecha", "peso", "cintura"])
    df = pd.read_csv(PESO_CSV)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["peso"] = pd.to_numeric(df["peso"], errors="coerce")
    if "cintura" not in df:
        df["cintura"] = pd.NA
    df["cintura"] = pd.to_numeric(df["cintura"], errors="coerce")
    return (df.dropna(subset=["fecha", "peso"])
              .sort_values("fecha").drop_duplicates("fecha", keep="last"))


def _registrar_peso(peso: float, cintura: float | None = None) -> None:
    df = _cargar_peso()
    hoy = pd.Timestamp(date.today())
    previa = df.loc[df["fecha"] == hoy, "cintura"]
    if cintura is None and len(previa):
        cintura = previa.iloc[0]  # conserva la cintura ya registrada hoy
    df = df[df["fecha"] != hoy]
    df = pd.concat([df, pd.DataFrame([{"fecha": hoy, "peso": float(peso),
                                       "cintura": cintura}])], ignore_index=True)
    df.sort_values("fecha").to_csv(PESO_CSV, index=False, date_format="%Y-%m-%d")


def _fig_peso(dfp: pd.DataFrame) -> go.Figure:
    if dfp.empty:
        return _fig_vacia("Registra tu primer peso para empezar")
    ma = dfp.set_index("fecha")["peso"].rolling("7D", min_periods=3).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dfp["fecha"], y=dfp["peso"], mode="markers",
                             name="Pesaje diario",
                             marker=dict(size=7, color=MUTED, opacity=0.55)))
    fig.add_trace(go.Scatter(x=ma.index, y=ma.values, mode="lines",
                             name="Tendencia (media 7 días)",
                             line=dict(color=ACCENT, width=3, shape="spline")))
    cin = dfp.dropna(subset=["cintura"]) if "cintura" in dfp else dfp.iloc[0:0]
    if len(cin):
        fig.add_trace(go.Scatter(x=cin["fecha"], y=cin["cintura"],
                                 mode="lines+markers", name="Cintura (cm)",
                                 yaxis="y2", line=dict(color=ACCENT2, width=2, dash="dot"),
                                 marker=dict(size=6, color=ACCENT2)))
    fig.update_layout(
        **PLOTLY_THEME,
        title=_titulo("Peso y cintura — la pareja que detecta la recomposición"),
        yaxis=dict(title="kg", gridcolor=GRID),
        yaxis2=dict(title="cintura (cm)", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)", zeroline=False),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=1.12),
    )
    return fig


def _tendencia_cintura(dfp: pd.DataFrame) -> float | None:
    """Cambio de cintura (cm/semana) sobre los registros de los últimos 21 días."""
    cin = dfp.dropna(subset=["cintura"]) if "cintura" in dfp else dfp.iloc[0:0]
    if len(cin) < 3:
        return None
    cin = cin[cin["fecha"] >= cin["fecha"].max() - pd.Timedelta(days=21)]
    if len(cin) < 3:
        return None
    dias = (cin["fecha"].max() - cin["fecha"].min()).days
    if dias < 7:
        return None
    return float((cin["cintura"].iloc[-1] - cin["cintura"].iloc[0]) / dias * 7)


def _tendencia_semanal(dfp: pd.DataFrame) -> float | None:
    """Cambio de la media móvil de 7 días en la última semana, en % del peso."""
    if len(dfp) < 8:
        return None
    s = dfp.set_index("fecha")["peso"].rolling("7D", min_periods=3).mean().dropna()
    if s.empty:
        return None
    previo = s.asof(s.index[-1] - pd.Timedelta(days=7))
    if pd.isna(previo):
        return None
    return float((s.iloc[-1] - previo) / s.iloc[-1] * 100)


def _panel_peso() -> list:
    if _es_demo():
        return [_aviso_demo("Modo demo: el registro de peso corporal está oculto (es un dato personal).")]
    return _panel_peso_real()


def _panel_peso_real() -> list:
    cfg = cargar_config()
    dfp = _cargar_peso()
    tc = _tendencia_cintura(dfp)
    return [
        _card(dcc.Graph(figure=_fig_peso(dfp), config={"displayModeBar": False})),
        html.Div(_card_calorias(cfg, dfp, tc), style={"marginTop": "16px"}),
        html.Div(_card_proteina(cfg), style={"marginTop": "16px"}),
    ]


def _card_calorias(cfg: dict, dfp: pd.DataFrame, tc: float | None) -> html.Div:
    """Calorias ADAPTATIVAS: punto de partida del enfoque y ajuste segun la
    tendencia real del peso (nutricion.evaluar)."""
    enf = ENFOQUES.get(cfg.get("enfoque"), ENFOQUES["recomposicion"])
    m = nutricion.metas(cfg)
    ev = nutricion.evaluar(cfg, dfp, tc)
    lo, hi = ev["objetivo"]
    t = ev["tendencia"]
    rango = f"{lo:+.2f}% a {hi:+.2f}%"
    estado = ev["estado"]
    boton = []
    if estado == "pocos_datos":
        color = MUTED
        msg = ("Pésate (idealmente a diario, en ayunas) durante ~10 días para que la tendencia "
               f"sea confiable. Objetivo para {enf.nombre}: entre {rango} de tu peso por semana. "
               "La cintura (opcional, 1-2 veces por semana) detecta la recomposición cuando la "
               "báscula se queda quieta.")
    elif estado == "esperando":
        color = ACCENT2
        msg = (f"Tendencia {t:+.2f}%/semana. Aplicaste un ajuste hace poco: espera "
               f"{ev['dias_restantes']} día(s) más para que se vea en la báscula antes de cambiar otra vez.")
    elif estado == "recomposicion":
        color = ACCENT
        msg = (f"RECOMPOSICIÓN EN MARCHA 🎯: peso casi plano ({t:+.2f}%/sem) pero la cintura baja "
               f"{tc:+.1f} cm/sem: estás perdiendo grasa y ganando músculo a la vez. No cambies nada.")
    elif estado == "en_rango":
        color = ACCENT
        msg = f"Tendencia {t:+.2f}%/semana, dentro del objetivo ({rango}). No cambies nada: así va bien."
    else:
        color = WARN
        d = ev["kcal_delta"]
        lado = "por DEBAJO" if d > 0 else "por ENCIMA"
        msg = (f"Tendencia {t:+.2f}%/semana, {lado} del objetivo ({rango}). Sugerencia: "
               f"{d:+d} kcal/día (≈ {d / 4:+.0f} g de carbohidratos; 100 kcal ≈ 1½ tortillas "
               "o ½ taza de arroz).")
        boton = [dcc.Store(id="kcal-delta", data=d),
                 html.Button(f"Aplicar {d:+d} kcal", id="kcal-aplicar", n_clicks=0,
                             className="gym-btn", style={"marginTop": "12px"})]
    if tc is not None and estado not in ("recomposicion", "pocos_datos"):
        msg += f" Cintura: {tc:+.1f} cm/semana."
    ajuste = (f" (punto de partida {m['kcal_base']:,} {m['kcal_ajuste']:+d} de ajustes)"
              if m["kcal_ajuste"] else " (punto de partida de tu enfoque)")
    return _card([
        html.Div("🔥 Calorías adaptativas", style={"color": color, "fontWeight": "700",
                                                  "fontSize": "14px", "marginBottom": "6px"}),
        html.Div([html.Span(f"~{m['kcal']:,} kcal/día", style={"fontWeight": "800", "fontSize": "18px"}),
                  html.Span(ajuste, style={"color": MUTED, "fontSize": "12px"})],
                 style={"color": TEXT, "marginBottom": "8px"}),
        html.P(msg, style={"color": TEXT, "fontSize": "13px", "margin": "0"}),
        *boton,
        html.P("Se ajusta de a poco (100-300 kcal) y se reevalúa cada 2 semanas: el peso de un día "
               "varía 1-2 kg por agua y comida; lo que cuenta es la tendencia.",
               style={"color": MUTED, "fontSize": "11px", "margin": "10px 0 0"}),
    ])


def _card_proteina(cfg: dict) -> html.Div:
    """Proteina registrada en la app (ultimos 7 dias) contra la meta del enfoque."""
    m = nutricion.metas(cfg)
    enf = ENFOQUES.get(cfg.get("enfoque"), ENFOQUES["recomposicion"])
    a = nutricion.adherencia(nutricion.leer_nutricion_csv(), m["proteina_min"])
    meta = f"{m['proteina_min']}-{m['proteina_max']} g/día ({enf.prot_g_kg[0]:g}-{enf.prot_g_kg[1]:g} g/kg)"
    if not a["dias_registrados"]:
        color, msg = MUTED, (f"Tu meta: {meta}. Regístrala en la app con el botón 🍗 Proteína: "
                             "se anota por porciones (un huevo, una taza de frijol…), sin pesar nada.")
    else:
        prom = a["promedio"]
        color = ACCENT if prom >= m["proteina_min"] else WARN
        msg = (f"Últimos 7 días: promedio {prom:.0f} g/día en {a['dias_registrados']} día(s) registrados, "
               f"{a['dias_en_meta']} en meta. Tu meta: {meta}.")
        if prom < m["proteina_min"]:
            msg += (f" Te faltan ~{m['proteina_min'] - prom:.0f} g/día: 1 lata de atún ≈ 24 g, "
                    "4 huevos ≈ 25 g, 1½ tazas de frijol ≈ 23 g.")
    return _card([
        html.Div("🍗 Proteína", style={"color": color, "fontWeight": "700", "fontSize": "14px",
                                      "marginBottom": "6px"}),
        html.P(msg, style={"color": TEXT, "fontSize": "13px", "margin": "0"}),
    ])


def _panel_nutricion(cfg: dict) -> html.Div:
    """Macros del enfoque convertidos a gramos usando el peso corporal real."""
    enf = ENFOQUES.get(cfg.get("enfoque"), ENFOQUES["recomposicion"])
    peso = float(cfg.get("peso_corporal", 75) or 75)

    def col(nombre: str, rango: tuple, emoji: str) -> html.Div:
        lo, hi = rango
        txt = f"{lo * peso:.0f} g" if lo == hi else f"{lo * peso:.0f}–{hi * peso:.0f} g"
        return html.Div([
            html.Div(f"{emoji} {nombre}", style={"color": MUTED, "fontSize": "12px"}),
            html.Div(f"{txt}/día", style={"color": TEXT, "fontWeight": "700", "fontSize": "16px"}),
        ], style={"minWidth": "140px"})

    return _card([
        html.Div(f"🥗 Tus macros de hoy ({peso:.0f} kg · {enf.nombre})",
                 style={"color": TEXT, "fontWeight": "700", "fontSize": "15px",
                        "marginBottom": "12px"}),
        html.Div([
            col("Proteína", enf.prot_g_kg, "🍗"),
            col("Carbohidratos", enf.carb_g_kg, "🍚"),
            col("Grasas", enf.grasa_g_kg, "🥑"),
            html.Div([
                html.Div("🔥 Calorías", style={"color": MUTED, "fontSize": "12px"}),
                html.Div(f"~{nutricion.metas(cfg)['kcal']:,} kcal/día",
                         style={"color": TEXT, "fontWeight": "700", "fontSize": "16px"}),
            ], style={"minWidth": "140px"}),
        ], style={"display": "flex", "gap": "28px", "flexWrap": "wrap"}),
        html.P(f"Reparte la proteína en 3–5 comidas de ~{0.4 * peso:.0f}–{0.55 * peso:.0f} g, "
               "con una en las ±2 h del entrenamiento. Creatina 3–5 g/día, a cualquier hora, "
               "todos los días (también los de descanso).",
               style={"color": MUTED, "fontSize": "12px", "marginTop": "12px",
                      "marginBottom": "0"}),
    ], {"marginTop": "16px"})


def _mensaje_calibracion(df: pd.DataFrame):
    """Chequeo simple de calibracion del RPE en el tiempo (unico usuario).
    Cruza la tendencia del e1RM con el RPE reportado para detectar si te estas
    subestimando (RPE bajo pero sin progreso) o sobre-entrenando (RPE alto sin
    progreso). Devuelve (color, texto) o None."""
    if df.empty or "rpe" not in df or df["rpe"].notna().sum() == 0:
        return None
    de = _con_e1rm(df)
    de = de[de["e1rm"] > 0].copy()
    if de.empty:
        return None
    de["semana"] = de["fecha_entreno"].dt.to_period("W").dt.start_time
    sem_e1 = de.groupby("semana")["e1rm"].max()
    if len(sem_e1) < 3:
        return None
    ult3 = sem_e1.tail(3)
    subio = ult3.iloc[-1] > ult3.iloc[0] * 1.01  # >1% de mejora en 3 semanas
    rpe_reciente = float(de[de["semana"] >= ult3.index[0]]["rpe"].mean())
    if subio:
        return None
    if rpe_reciente < 8:
        return (WARN, "Tu fuerza estimada (e1RM) lleva ~3 semanas sin subir pero reportas "
                f"RPE bajo (~{rpe_reciente:.1f}). Puede que estés subestimando el esfuerzo: "
                "si te quedan más reps de las que marcas, el motor no sube el peso. "
                "Sé honesto con el RPE o acércate un poco más al límite.")
    if rpe_reciente >= 9:
        return (DANGER, f"Entrenas muy duro (RPE ~{rpe_reciente:.1f}) pero la fuerza no sube en "
                "~3 semanas: señal de fatiga acumulada. Considera un deload, dormir más o "
                "comer un poco más.")
    return None


# Prioridades que comparten patron de Bloque A (se fatigan entre si)
_GRUPO_PATRON = {"pecho": "empuje", "hombros": "empuje",
                 "dorsales": "tiron", "espalda": "tiron"}


def _aviso_sinergia(prioridades: list[str]) -> str | None:
    """Aviso si dos prioridades comparten patron biomecanico (p. ej. pecho y
    hombros, ambos de empuje): no se pueden dar al 100% el mismo dia."""
    grupos = [g for m in prioridades if (g := _GRUPO_PATRON.get(m))]
    for g in set(grupos):
        share = [m for m in prioridades if _GRUPO_PATRON.get(m) == g]
        if len(share) >= 2:
            return (f"⚠ Marcaste {' y '.join(share)}, que comparten el patrón de {g}. "
                    "No puedes dar el 100% a los dos el mismo día (uno fatiga al otro). "
                    "El motor alterna cuál va primero entre los días A y B, pero si uno es "
                    "tu verdadero punto débil, prioriza solo ese para mejores resultados.")
    return None


def _fig_tonelaje_semana(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _fig_vacia()
    df2 = df.copy()
    df2["semana"] = df2["fecha_entreno"].dt.to_period("W").dt.start_time
    ton = df2.groupby("semana")["tonelaje_serie"].sum().reset_index()
    fig = go.Figure(go.Scatter(
        x=ton["semana"], y=ton["tonelaje_serie"],
        mode="lines+markers", fill="tozeroy",
        fillcolor="rgba(125,81,254,0.22)",
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
def _tabla_plan_demo(df: pd.DataFrame, objetivo: date) -> dash_table.DataTable | html.Div:
    """Plan de la demo: la S1 del escenario (tipo de entreno elegido en la demo)."""
    import demo_motor
    semanas = demo_motor.escenario(_demo_cfg())["semanas"]
    return _tabla_de_filas([f for d in range(1, 8) for f in semanas[1][d]])


def _tabla_plan(df: pd.DataFrame) -> dash_table.DataTable | html.Div:
    try:
        from planificar import generar_filas, ultimas_y_records, lunes_objetivo, decidir_semana
        from dotenv import load_dotenv

        load_dotenv()
        inicio_env = os.getenv("MES_INICIO")
        objetivo = (
            date.fromisoformat(os.environ["SEMANA_SIGUIENTE"])
            if os.getenv("SEMANA_SIGUIENTE")
            else lunes_objetivo()
        )
        inicio = date.fromisoformat(inicio_env) if inicio_env else objetivo
        if _es_demo():
            return _tabla_plan_demo(df, objetivo)
        # misma decision que planificar.py (rampa de reingreso + deload reactivo):
        # antes el dashboard calculaba solo la semana del calendario y mostraba un
        # plan distinto del que se subia al telefono
        # la encuesta (series por musculo + bienestar) igual que en el motor
        import feedback as _fbk
        _enc = _fbk.leer_csv(CSV_PATH.parent)
        semana, reingreso, _avisos = decidir_semana(df, objetivo, inicio, _enc)
        ajustes, dolor = _fbk.ajustes_para(_enc, objetivo, inicio)
        filas = generar_filas(df, objetivo.isoformat(), semana, reingreso=reingreso,
                              ajustes=ajustes, dolor=dolor,
                              preferencias=_fbk.leer_preferencias_csv(CSV_PATH.parent))
    except Exception as exc:
        return html.Div([
            html.P(f"No se pudo calcular el plan: {exc}",
                   style={"color": WARN, "marginBottom": "8px"}),
            html.P("Asegurate de que .env tenga API_BASE_URL y MES_INICIO, "
                   "o que historial.csv tenga datos reales.",
                   style={"color": MUTED, "fontSize": "13px"}),
        ])

    return _tabla_de_filas(filas)


def _tabla_de_filas(filas: list[dict]) -> dash_table.DataTable:
    cols = ["dia_semana", "nombre_dia", "bloque", "ejercicio", "tecnica",
            "series_objetivo", "reps_min", "reps_max", "descanso_seg", "peso_sugerido", "notas"]
    df_plan = pd.DataFrame(filas)[cols]

    return dash_table.DataTable(
        id="tabla-plan",
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


_MESO_NOMBRE = {
    1: "S1 · Base", 2: "S2 · Rotación", 3: "S3 · Superar S1",
    4: "S4 · Pico", 5: "S5 · Deload",
}


def _tabla_mesociclo(df: pd.DataFrame):
    """Las 5 semanas del mesociclo actual, una tras otra. La ESTRUCTURA
    (ejercicios, series, reps, tecnicas) es exacta; los PESOS son la
    proyeccion del motor con tu historial de hoy y se reajustan cada semana
    con tu rendimiento real."""
    try:
        from datetime import timedelta
        from planificar import generar_filas, lunes_objetivo
        from generador import ciclo_mesociclo
        from dotenv import load_dotenv

        load_dotenv()
        inicio_env = os.getenv("MES_INICIO")
        objetivo = (
            date.fromisoformat(os.environ["SEMANA_SIGUIENTE"])
            if os.getenv("SEMANA_SIGUIENTE") else lunes_objetivo()
        )
        inicio = date.fromisoformat(inicio_env) if inicio_env else objetivo
        ciclo = ciclo_mesociclo(objetivo)
        cycle_start = inicio + timedelta(days=ciclo * 35)
        demo_semanas = None
        if _es_demo():
            # demo: las 5 semanas del escenario (tipo de entreno elegido en la demo)
            import demo_motor
            demo_semanas = demo_motor.escenario(_demo_cfg())["semanas"]

        filas_all: list[dict] = []
        for sem in (1, 2, 3, 4, 5):
            fecha = cycle_start + timedelta(days=(sem - 1) * 7)
            filas_sem = ([f for d in range(1, 8) for f in demo_semanas[sem][d]] if demo_semanas
                         else generar_filas(df, fecha.isoformat(), sem))
            for f in filas_sem:
                if not f.get("tecnica"):
                    continue
                filas_all.append({
                    "semana": _MESO_NOMBRE[sem],
                    "dia_semana": f["dia_semana"],
                    "nombre_dia": f["nombre_dia"],
                    "bloque": f["bloque"],
                    "ejercicio": f["ejercicio"],
                    "tecnica": f["tecnica"],
                    "series_objetivo": f["series_objetivo"],
                    "reps": f'{f["reps_min"] or ""}-{f["reps_max"] or ""}'.strip("-"),
                    "peso_sugerido": f["peso_sugerido"],
                })
    except Exception as exc:  # noqa: BLE001
        return html.Div([
            html.P(f"No se pudo calcular el mesociclo: {exc}",
                   style={"color": WARN, "marginBottom": "8px"}),
            html.P("Revisa que .env tenga MES_INICIO y que historial.csv tenga datos.",
                   style={"color": MUTED, "fontSize": "13px"}),
        ])

    cols = ["semana", "dia_semana", "nombre_dia", "bloque", "ejercicio",
            "tecnica", "series_objetivo", "reps", "peso_sugerido"]
    df_meso = pd.DataFrame(filas_all)[cols]

    return dash_table.DataTable(
        id="tabla-meso",
        data=df_meso.to_dict("records"),
        columns=[{"name": c.replace("_", " ").title(), "id": c} for c in cols],
        filter_action="native",
        sort_action="native",
        page_action="native",
        page_size=30,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": CARD2, "color": ACCENT,
                      "fontWeight": "600", "border": "1px solid #2a2d3e"},
        style_cell={"backgroundColor": CARD, "color": TEXT,
                    "border": "1px solid #2a2d3e", "fontSize": "13px",
                    "padding": "8px 12px"},
        style_data_conditional=[
            {"if": {"filter_query": '{semana} contains "Deload"'},
             "backgroundColor": "rgba(24,179,255,0.10)"},
            {"if": {"filter_query": '{semana} contains "Pico"'},
             "backgroundColor": "rgba(255,192,67,0.10)"},
            {"if": {"filter_query": '{tecnica} contains "Top Set"'},
             "color": ACCENT, "fontWeight": "600"},
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
        html.Div(icono, className="gym-kpi-ico", style={"fontSize": "22px", "marginBottom": "8px", "opacity": 0.9}),
        html.Div(valor, className="gym-kpi-val", style={"fontSize": "34px", "fontFamily": FUENTE_DISPLAY,
                                "fontWeight": "400", "color": TEXT, "lineHeight": "1",
                                "letterSpacing": "0.5px"}),
        html.Div(titulo, className="gym-kpi-lbl", style={"fontSize": "10.5px", "color": MUTED, "marginTop": "8px",
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
    if _es_demo():
        # demo: el mismo formulario, con la config DE LA DEMO; guardar no toca tu archivo
        d = _demo_cfg()
        cfg = {"enfoque": d["enfoque"], "split": d["split"], "prioridades": d["prioridades"],
               "duracion_min": d["duracion_min"], "peso_corporal": 75, "equipo_excluido": []}
    else:
        cfg = cargar_config()
    return html.Div([
        *([_aviso_demo("Modo demo: prueba cualquier tipo de entreno. Se guarda solo en esta demo "
                       "(una cookie de tu navegador); tu configuración real no se toca.")] if _es_demo() else []),
        _card([
            html.Div("Configura tu entrenamiento",
                     style={"color": TEXT, "fontWeight": "700", "fontSize": "16px",
                            "marginBottom": "4px"}),
            html.Div("Elige el enfoque, el split y tus músculos rezagados. El plan se "
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

            html.Label("Equipo que tu gym NO tiene (usa alternativas del mismo patrón)",
                       style={**_LABEL_STYLE, "marginTop": "18px", "display": "block"}),
            dcc.Checklist(
                id="cfg-equipo",
                options=[{"label": f" 🚫 {lbl}", "value": eq} for eq, lbl in EQUIPOS_FILTRABLES],
                value=cfg.get("equipo_excluido", []),
                inline=True,
                style={"fontSize": "14px", "marginTop": "10px",
                       "display": "flex", "flexWrap": "wrap", "gap": "8px 4px"},
                labelStyle={"color": TEXT, "marginRight": "16px", "cursor": "pointer",
                            "display": "inline-flex", "alignItems": "center", "gap": "5px"},
            ),

            html.Button("Generar y guardar plan", id="cfg-guardar", n_clicks=0,
                        className="gym-btn", style={"marginTop": "26px"}),
        ]),

        _panel_nutricion(cfg),

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
        *([html.P(aviso, style={"color": WARN, "fontSize": "12px", "marginTop": "10px",
                                "padding": "8px 10px", "background": "rgba(255,192,67,0.10)",
                                "borderRadius": "6px", "border": "1px solid rgba(255,192,67,0.3)"})]
          if (aviso := _aviso_sinergia(cfg.get("prioridades", []))) else []),
        html.P("El nuevo plan ya está activo. Mira la pestaña «Plan semana» para verlo completo. "
               "La próxima vez que corras el motor (planificar.py) usará este enfoque.",
               style={"color": MUTED, "fontSize": "12px", "marginTop": "12px"}),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Menú semanal barato (menu.py): rico, sano y barato con comida mexicana
# ─────────────────────────────────────────────────────────────────────────────
_ETIQ_TIEMPO = {"desayuno": "Desayuno", "comida": "Comida", "colacion": "Colación", "cena": "Cena"}
_EXCLUIR_OPC = [("carnes", "Carnes (pollo, res, cerdo)"), ("pescado", "Pescado (atún, sardina)"),
                ("lacteos", "Lácteos"), ("huevo", "Huevo")]


def _menu_cfg() -> dict:
    if _es_demo():
        d = _demo_cfg()
        return {"enfoque": d["enfoque"], "peso_corporal": 75}
    return cargar_config()


def _en_segundo_plano(fn, *args) -> None:
    import threading
    threading.Thread(target=fn, args=args, daemon=True).start()


def _menu_actual(forzar: bool = False):
    """El menu de la semana objetivo: el guardado si sigue vigente (misma semana y
    misma meta); si no, uno nuevo. En demo nunca se guarda nada."""
    import menu as mnu
    from planificar import lunes_objetivo
    cfg = _menu_cfg()
    lunes = lunes_objetivo()
    meta = nutricion.metas(cfg)
    if not _es_demo() and not forzar:
        m = mnu.leer_local()
        if (m and m.get("semana_inicio") == lunes.isoformat()
                and m.get("meta", {}).get("kcal") == meta["kcal"]
                and m.get("meta", {}).get("proteina_min") == meta["proteina_min"]):
            return m
    try:
        m = mnu.generar_menu(cfg, lunes)
    except ValueError as e:
        return str(e)
    if not _es_demo():
        mnu.guardar_local(m)
    return m


def _menu_vista(m) -> html.Div:
    if isinstance(m, str) or not m:
        return _card(html.P(m or "No se pudo generar el menú.", style={"color": WARN, "margin": "0"}))
    meta = m["meta"]
    resumen = _card([
        html.Div(f"🍽️ Menú de la semana del {m['semana_inicio']}",
                 style={"color": TEXT, "fontWeight": "700", "fontSize": "15px", "marginBottom": "6px"}),
        html.Div([html.Span(f"${m['costo_semana']:,.0f} a la semana",
                            style={"fontWeight": "800", "fontSize": "20px", "color": ACCENT}),
                  html.Span(f"  ·  ~${m['costo_dia']:,.0f} al día", style={"color": MUTED, "fontSize": "13px"})]),
        html.P(f"Promedio: {m['kcal_prom']:,} kcal y {m['prot_prom']} g de proteína al día "
               f"(tu meta: {meta['kcal']:,} kcal y {meta['proteina_min']}-{meta['proteina_max']} g).",
               style={"color": TEXT, "fontSize": "13px", "margin": "8px 0 0"}),
        *[html.P(a, style={"color": WARN, "fontSize": "12px", "margin": "6px 0 0"}) for a in m.get("avisos", [])],
        html.P(m.get("nota", ""), style={"color": MUTED, "fontSize": "11px", "margin": "8px 0 0"}),
    ])
    dias = []
    for d in m["dias"]:
        comidas = []
        for c in d["comidas"]:
            comidas.append(html.Div([
                html.Div(_ETIQ_TIEMPO.get(c["tiempo"], c["tiempo"]).upper(),
                         style={"color": ACCENT, "fontSize": "10px", "fontWeight": "800", "letterSpacing": "1px"}),
                html.Div([html.Span(c["nombre"], style={"fontWeight": "700"}),
                          html.Span(f"  {c['kcal']} kcal · {c['prot']:.0f} g", style={"color": MUTED, "fontSize": "12px"})],
                         style={"color": TEXT, "fontSize": "13.5px"}),
                html.Div(", ".join(i["texto"] for i in c["ingredientes"]),
                         style={"color": MUTED, "fontSize": "12px", "marginTop": "2px"}),
                *([html.Div(c["como"], style={"color": MUTED, "fontSize": "11px", "fontStyle": "italic",
                                               "marginTop": "2px"})] if c.get("como") else []),
            ], style={"padding": "8px 0", "borderTop": f"1px solid {LINE}"}))
        dias.append(_card([
            html.Div([html.Span(d["nombre"], style={"fontWeight": "800", "fontSize": "15px"}),
                      html.Span(f"{d['kcal']:,} kcal · {d['prot']} g · ${d['costo']:.0f}",
                                style={"color": MUTED, "fontSize": "12px"})],
                     style={"display": "flex", "justifyContent": "space-between", "alignItems": "baseline",
                            "color": TEXT, "marginBottom": "4px", "gap": "8px"}),
            *comidas,
        ], {"padding": "16px"}))
    lista = dash_table.DataTable(
        data=[{"alimento": f["nombre"], "cantidad": f["compra"], "costo": f"${f['costo']:.0f}",
               "precio": f["fuente"]} for f in m["lista"]],
        columns=[{"name": "Alimento", "id": "alimento"}, {"name": "Comprar", "id": "cantidad"},
                 {"name": "≈ Costo", "id": "costo"}, {"name": "Precio", "id": "precio"}],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": CARD2, "color": ACCENT, "fontWeight": "600", "border": f"1px solid {LINE}"},
        style_cell={"backgroundColor": CARD, "color": TEXT, "border": f"1px solid {LINE}", "fontSize": "13px",
                    "padding": "8px 12px", "textAlign": "left"},
    )
    return html.Div([
        resumen,
        html.Div(dias, className="menu-dias", style={"marginTop": "16px"}),
        _card([html.Div(f"🛒 Lista del súper (≈ ${m['costo_semana']:,.0f})",
                        style={"color": TEXT, "fontWeight": "700", "fontSize": "15px", "marginBottom": "10px"}),
               lista], {"marginTop": "16px"}),
    ])


def _tab_menu_children() -> html.Div:
    import alimentos_mx as alx
    cfg = _menu_cfg()
    precios = alx.precios()
    tabla_precios = dash_table.DataTable(
        id="precios-tabla",
        data=[{"id": a.id, "alimento": a.nombre, "precio": precios[a.id],
               "fuente": "tu precio" if precios[a.id] != a.precio_kg else a.fuente}
              for a in alx.ALIMENTOS.values()],
        columns=[{"name": "Alimento", "id": "alimento", "editable": False},
                 {"name": "$ por kg o L", "id": "precio", "type": "numeric", "editable": True},
                 {"name": "Fuente", "id": "fuente", "editable": False}],
        editable=True, page_size=12, style_table={"overflowX": "auto"},
        style_header={"backgroundColor": CARD2, "color": ACCENT, "fontWeight": "600", "border": f"1px solid {LINE}"},
        style_cell={"backgroundColor": CARD, "color": TEXT, "border": f"1px solid {LINE}", "fontSize": "13px",
                    "padding": "8px 12px", "textAlign": "left"},
        style_data_conditional=[{"if": {"column_id": "precio"}, "fontWeight": "700", "color": ACCENT}],
    )
    controles = _card([
        html.Div("Comida mexicana de diario que llega a tus calorías y a tu proteína al menor costo. "
                 "Si algo no te gusta o no lo comes, quítalo y genera otro.",
                 style={"color": MUTED, "fontSize": "13px", "marginBottom": "12px"}),
        html.Label("No como", style=_LABEL_STYLE),
        dcc.Checklist(id="menu-excluir", options=[{"label": f" {t}", "value": v} for v, t in _EXCLUIR_OPC],
                      value=[x for x in (cfg.get("alimentos_excluidos") or []) if x in dict(_EXCLUIR_OPC)],
                      inline=True, style={"fontSize": "14px", "marginTop": "8px", "display": "flex",
                                          "flexWrap": "wrap", "gap": "8px 4px"},
                      labelStyle={"color": TEXT, "marginRight": "16px", "display": "inline-flex",
                                  "alignItems": "center", "gap": "5px"}),
        dcc.Checklist(id="menu-supl", options=[{"label": " Permitir proteína en polvo (solo si con comida no llego)",
                                                "value": "si"}],
                      value=["si"] if cfg.get("menu_suplementos") else [],
                      style={"fontSize": "14px", "marginTop": "10px"},
                      labelStyle={"color": TEXT, "display": "inline-flex", "alignItems": "center", "gap": "5px"}),
        html.Button("🔄 Generar otro menú", id="menu-generar", n_clicks=0, className="gym-btn",
                    style={"marginTop": "16px"}),
    ])
    precios_card = _card([
        html.Div("💲 Tus precios", style={"color": TEXT, "fontWeight": "700", "fontSize": "15px", "marginBottom": "4px"}),
        html.P("Profeco 2026 donde hay dato; el resto es estimado. Cambia el precio de lo que compras "
               "(doble clic en la celda) y guarda: el menú se recalcula con lo que de verdad pagas.",
               style={"color": MUTED, "fontSize": "12px", "marginBottom": "10px"}),
        tabla_precios,
        html.Button("Guardar precios", id="precios-guardar", n_clicks=0, className="gym-btn-ghost",
                    style={"marginTop": "12px"}),
        html.Div(id="precios-estado", style={"marginTop": "8px", "fontSize": "13px", "color": ACCENT}),
    ], {"marginTop": "16px"})
    return html.Div([
        *([_aviso_demo("Modo demo: menú del atleta virtual (75 kg). Puedes generar otros; nada se guarda.")]
          if _es_demo() else []),
        controles,
        html.Div(id="menu-contenido", children=_menu_vista(_menu_actual()), style={"marginTop": "16px"}),
        precios_card,
    ], style={"padding": "16px 0"})


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
        banner = html.Div([
            html.Span("DEMO ", style={"fontWeight": "800", "color": "#ad94ff"}),
            html.Span("Datos de un atleta virtual (simulador del motor). Nada de esto es real y no se guarda nada. "),
            html.A("Salir de la demo", href="/demo/salir", style={"color": ACCENT, "fontWeight": "700"}),
        ], style={"background": "rgba(125,81,254,0.14)", "color": TEXT, "padding": "10px 16px",
                  "fontSize": "13px", "borderRadius": "10px", "marginBottom": "16px",
                  "border": "1px dashed #7d51fe"})
    elif vacio:
        banner = html.Div([
            html.Span("Sin datos todavía. ", style={"fontWeight": "700", "color": TEXT}),
            html.Span("Registra entrenos en la app y presiona «🔄 Actualizar datos» para traerlos del servidor.",
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
    ], className="gym-kpis", style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "22px"})

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
                        style={"width": "100%", "maxWidth": "420px"},
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
                _card(dcc.Graph(figure=_fig_records(df), config={"displayModeBar": False})),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab 4: Fatiga percibida (RPE) ───────────────────────────────────
        dcc.Tab(label="Fatiga (RPE)", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                *([_card([
                    html.Div("🎯 Calibración de tu RPE", style={"color": _cal[0], "fontWeight": "700",
                             "fontSize": "14px", "marginBottom": "6px"}),
                    html.P(_cal[1], style={"color": TEXT, "fontSize": "13px", "margin": "0"}),
                  ], {"marginBottom": "16px", "border": f"1px solid {_cal[0]}"})]
                  if (_cal := _mensaje_calibracion(df)) else []),
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
                        html.P("RPE sostenido por encima de 9 indica fatiga acumulada que se "
                               "come tu rendimiento y tu recuperación. Adelanta el deload: "
                               "misma intensidad, la mitad de volumen y cero series al fallo "
                               "durante una semana (es lo que hace la S5 del mesociclo).",
                               style={"color": MUTED, "fontSize": "13px"}),
                    ], {"flex": "1", "minWidth": "240px"}),
                ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap",
                          "marginTop": "16px"}),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab: Volumen por músculo (landmarks + encuesta) ─────────────────
        dcc.Tab(label="Volumen", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                *([_pe] if (_pe := _panel_encuesta()) else []),
                _card(dcc.Graph(figure=_fig_volumen_musculo(df), config={"displayModeBar": False})),
                _card([
                    html.Div("Cómo leerlo", style={"color": ACCENT, "fontWeight": "600", "marginBottom": "6px"}),
                    html.P("Barras = series efectivas (las indirectas cuentan la mitad). Franja verde = "
                           "rango productivo (MAV); línea gris = mínimo efectivo (MEV); línea roja = máximo "
                           "recuperable (MRV). Son rangos orientativos de población: la encuesta de la app "
                           "ajusta dónde estás tú.", style={"color": MUTED, "fontSize": "13px", "margin": "0"}),
                ], {"marginTop": "16px"}),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab 5: Logbook ──────────────────────────────────────────────────
        # ── Tab: Peso corporal (nutrición basada en la báscula) ─────────────
        dcc.Tab(label="Peso corporal", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                _card([
                    html.Div([
                        html.Div([
                            html.Label("Peso de hoy (kg)", style=_LABEL_STYLE),
                            dcc.Input(id="peso-input", type="number", min=30, max=250,
                                      step=0.1, placeholder="p. ej. 74.6",
                                      style={"padding": "9px 12px", "height": "42px",
                                             "boxSizing": "border-box", "width": "150px",
                                             "display": "block", "marginTop": "6px"}),
                        ]),
                        html.Div([
                            html.Label("Cintura (cm, opcional)", style=_LABEL_STYLE),
                            dcc.Input(id="cintura-input", type="number", min=40, max=200,
                                      step=0.5, placeholder="a la altura del ombligo",
                                      style={"padding": "9px 12px", "height": "42px",
                                             "boxSizing": "border-box", "width": "190px",
                                             "display": "block", "marginTop": "6px"}),
                        ]),
                        html.Button("Registrar", id="peso-guardar", n_clicks=0,
                                    className="gym-btn", style={"alignSelf": "flex-end"}),
                    ], className="gym-peso-campos", style={"display": "flex", "gap": "14px", "alignItems": "flex-end",
                              "flexWrap": "wrap"}),
                    html.P("Pésate en ayunas, después del baño y con la misma báscula; "
                           "la cintura 1-2 veces por semana, a la altura del ombligo y sin "
                           "apretar. En recomposición la báscula puede quedarse plana "
                           "mientras la cintura baja: eso es GANAR, no estancarte.",
                           style={"color": MUTED, "fontSize": "12px", "marginTop": "10px",
                                  "marginBottom": "0"}),
                ]),
                html.Div(id="peso-panel", children=_panel_peso(),
                         style={"marginTop": "16px"}),
            ], style={"padding": "16px 0"}),
        ),

        dcc.Tab(label="🍽️ Menú", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=_tab_menu_children(),
        ),

        dcc.Tab(label="Logbook", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                _card([
                    html.P("Puedes filtrar por cualquier columna haciendo clic en el "
                           "ícono de filtro. Ejemplo: escribe 'Press' en Ejercicio.",
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
                                        "marginBottom": "12px"}),
                        html.Div([
                            html.Button("⬆ Recalcular y subir plan al servidor",
                                        id="btn-subir-plan", n_clicks=0, className="gym-btn",
                                        style={"marginBottom": "8px", "marginRight": "10px"}),
                            html.Button("📋 Copiar tabla",
                                        id="btn-copiar-plan", n_clicks=0, className="gym-btn-ghost",
                                        style={"marginBottom": "8px"}),
                            html.Span(id="copiar-plan-status",
                                      style={"marginLeft": "10px", "fontSize": "13px",
                                             "color": ACCENT, "fontWeight": "600"}),
                        ], style={"display": "flex", "alignItems": "center", "flexWrap": "wrap"}),
                        html.Div("Corre el motor completo (historial → progresión → "
                                 "sube a MySQL). Tarda unos segundos. «Copiar tabla» "
                                 "copia todo el plan al portapapeles (pégalo en Notas, "
                                 "WhatsApp o Excel).",
                                 style={"color": MUTED, "fontSize": "11px",
                                        "marginBottom": "12px"}),
                        html.Div(id="subir-plan-status"),
                    ]),
                    _tabla_plan(df),
                ]),
            ], style={"padding": "16px 0"}),
        ),

        # ── Tab: Mesociclo completo (5 semanas) ─────────────────────────────
        dcc.Tab(label="Mesociclo (5 sem)", style=_TAB_STYLE, selected_style=_TAB_SELECTED_STYLE,
            children=html.Div([
                _card([
                    html.Div("El mesociclo completo — las 5 semanas de un vistazo",
                             style={"color": TEXT, "fontWeight": "600",
                                    "fontSize": "15px", "marginBottom": "4px"}),
                    html.Div([
                        html.Span("La ", style={"color": MUTED}),
                        html.Span("estructura", style={"color": TEXT, "fontWeight": "600"}),
                        html.Span(" (ejercicios, series, reps, técnicas) es exacta. Los ",
                                  style={"color": MUTED}),
                        html.Span("pesos", style={"color": TEXT, "fontWeight": "600"}),
                        html.Span(" son la proyección con tu historial de hoy y se "
                                  "reajustan cada semana con tu rendimiento real "
                                  "(sobrecarga progresiva). Filtra por «Semana» para "
                                  "ver una sola.", style={"color": MUTED}),
                    ], style={"fontSize": "12px", "marginBottom": "10px"}),
                    html.Div([
                        html.Button("📋 Copiar mesociclo",
                                    id="btn-copiar-meso", n_clicks=0, className="gym-btn-ghost"),
                        html.Span(id="copiar-meso-status",
                                  style={"marginLeft": "10px", "fontSize": "13px",
                                         "color": ACCENT, "fontWeight": "600"}),
                    ], style={"marginBottom": "12px"}),
                    _tabla_mesociclo(df),
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
                    # el titulo es un enlace INVISIBLE a la demo (y de vuelta si ya estas en ella)
                    html.A("Gym Tracker", href="/demo/salir" if _es_demo() else "/demo",
                           style={"color": TEXT, "margin": "0", "fontSize": "21px", "fontWeight": "800",
                                  "letterSpacing": "-0.5px", "lineHeight": "1", "display": "block",
                                  "textDecoration": "none", "cursor": "default"}),
                    html.Span("Panel de Inteligencia Deportiva", className="gym-subtitulo",
                              style={"color": MUTED, "fontSize": "12px"}),
                ]),
            ], className="gym-brand", style={"display": "flex", "alignItems": "center", "gap": "12px"}),

            html.Div([
                html.Button(btn_tema, id="btn-tema", n_clicks=0,
                            className="gym-btn-ghost", style={"marginRight": "10px"}),
                html.Button("🔄 Actualizar datos", id="btn-refresh", n_clicks=0,
                            className="gym-btn-ghost", style={"marginRight": "14px"}),
                html.Span(estado_chip[0], style={"color": estado_chip[1], "fontSize": "11px",
                                                  "fontWeight": "700", "letterSpacing": "0.5px"}),
            ], className="gym-actions", style={"display": "flex", "alignItems": "center", "flexWrap": "wrap"}),
        ], className="gym-header", style={
            "display": "flex", "justifyContent": "space-between", "alignItems": "center",
            "marginBottom": "22px", "paddingBottom": "18px",
            "borderBottom": f"1px solid {LINE}",
        }),

        html.Div(id="refresh-status"),

        banner,
        kpi_row,
        tabs,
    ], className="gym-shell", style={"padding": "24px 32px", "maxWidth": "1500px", "margin": "0 auto",
               "fontFamily": FUENTE_TEXTO})

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
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1, maximum-scale=1"}],
    suppress_callback_exceptions=True,
)
# Objeto WSGI para servirlo en produccion con gunicorn (VM): `gunicorn dashboard:server`.
# Nunca exponer a internet con app.run(debug=True): el depurador de Flask permite
# ejecutar codigo arbitrario en la maquina.
server = app.server


@server.route("/demo")
def _entrar_demo():
    from flask import make_response, redirect
    r = make_response(redirect("/"))
    r.set_cookie(COOKIE_DEMO, "1", max_age=3 * 3600, samesite="Lax")
    return r


@server.route("/demo/salir")
def _salir_demo():
    from flask import make_response, redirect
    r = make_response(redirect("/"))
    r.delete_cookie(COOKIE_DEMO)
    r.delete_cookie(COOKIE_DEMO_CFG)
    return r


# API PUBLICA de la demo: solo datos SIMULADOS (demo_motor), nunca los reales.
# La consume el modo demo de la app (otro origen: InfinityFree), de ahi el CORS.
def _json_demo(datos):
    from flask import jsonify
    r = jsonify(datos)
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Cache-Control"] = "public, max-age=600"
    return r


@server.route("/demo/api/opciones")
def _api_demo_opciones():
    import demo_motor
    return _json_demo(demo_motor.opciones())


@server.route("/demo/api/escenario")
def _api_demo_escenario():
    import demo_motor
    from flask import request
    return _json_demo(demo_motor.para_app(dict(request.args)))


def _calentar_demo() -> None:
    """Genera en segundo plano el escenario por defecto: la demo abre al instante."""
    try:
        import demo_motor
        demo_motor.escenario({})
    except Exception:  # noqa: BLE001  (la demo nunca debe tumbar el dashboard)
        pass


# en la copia de OTRA persona (GYM_INSTANCIA) no se precalcula: la VM tiene poca
# memoria y la demo igual funciona, solo tarda unos segundos la primera vez
if not os.getenv("GYM_INSTANCIA"):
    __import__("threading").Thread(target=_calentar_demo, daemon=True).start()


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
    if _es_demo():
        from dash import no_update
        return _aviso_demo(), no_update
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
        msg = html.Div(f"⚠ No se pudo actualizar: {exc}. Revisa tu conexión y el .env.",
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
    if _es_demo():
        from dash import no_update
        return no_update          # el tema vive en TU config: la demo no la toca
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
    State("cfg-equipo", "value"),
    prevent_initial_call=True,
)
def _guardar_enfoque(n_clicks, enfoque, split, prioridades, peso, duracion, equipo):
    if _es_demo():
        import demo_motor
        from dash import callback_context
        nueva = demo_motor.normalizar({"enfoque": enfoque, "split": split, "duracion": duracion,
                                       "prioridades": prioridades or []})
        demo_motor.escenario(nueva)          # se calcula ya (unos segundos) y queda en cache
        callback_context.response.set_cookie(COOKIE_DEMO_CFG, _cookie_demo_cfg(nueva),
                                             max_age=3 * 3600, samesite="Lax")
        return _aviso_demo([html.Span("✓ Demo cambiada a otro tipo de entreno. "),
                            html.A("Recargar para verla", href="/", style={"color": ACCENT, "fontWeight": "700"})])
    cfg = {
        "enfoque": enfoque,
        "split": split,
        "prioridades": prioridades or [],
        "peso_corporal": peso or 75,
        "duracion_min": duracion or 90,
        "equipo_excluido": equipo or [],
    }
    guardar_config(cfg)
    nutricion.subir_meta_en_segundo_plano()      # la app ve la meta nueva de proteina
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


@callback(
    Output("subir-plan-status", "children"),
    Input("btn-subir-plan", "n_clicks"),
    prevent_initial_call=True,
)
def _subir_plan(n_clicks):
    """Corre el motor completo (planificar.main) sin salir del dashboard."""
    if _es_demo():
        return _aviso_demo("Modo demo: no se sube ningún plan a tu app.")
    import contextlib
    import io
    try:
        import planificar
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            planificar.main()
        lineas = [ln for ln in buf.getvalue().strip().splitlines() if ln]
        detalle = lineas[-1] if lineas else "Plan sincronizado."
        extra = " · ".join(ln for ln in lineas if "DELOAD REACTIVO" in ln)
        return html.Div(
            [html.Div(f"✓ {detalle}", style={"fontWeight": "600"})] +
            ([html.Div(extra, style={"fontSize": "12px", "marginTop": "4px"})] if extra else []),
            style={"background": "rgba(0,224,181,0.12)", "color": ACCENT,
                   "padding": "10px 16px", "borderRadius": "10px", "marginBottom": "12px",
                   "fontSize": "13px", "border": "1px solid rgba(0,224,181,0.3)"})
    except Exception as exc:  # noqa: BLE001
        return html.Div(f"⚠ No se pudo subir el plan: {exc}. Revisa tu conexión y el .env.",
                        style={"background": "rgba(255,93,122,0.12)", "color": DANGER,
                               "padding": "10px 16px", "borderRadius": "10px",
                               "marginBottom": "12px", "fontSize": "13px",
                               "border": "1px solid rgba(255,93,122,0.3)"})


# Copiar toda la tabla del plan al portapapeles como texto tabulado (TSV).
# Respeta el filtro/orden activos: usa derived_virtual_data (lo que se ve).
app.clientside_callback(
    """
    function(n, cols, filas) {
        if (!n) { return ""; }
        if (!cols || !filas || !filas.length) { return "Sin datos para copiar"; }
        var encabezados = cols.map(function(c){ return c.name; });
        var ids = cols.map(function(c){ return c.id; });
        var lineas = [encabezados.join("\\t")];
        filas.forEach(function(fila){
            lineas.push(ids.map(function(id){
                var v = fila[id];
                return (v === null || v === undefined) ? "" : String(v);
            }).join("\\t"));
        });
        var texto = lineas.join("\\n");
        function ok(){ return "✓ Copiado (" + filas.length + " filas)"; }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(texto);
            return ok();
        }
        var ta = document.createElement("textarea");
        ta.value = texto; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); } catch (e) {}
        document.body.removeChild(ta);
        return ok();
    }
    """,
    Output("copiar-plan-status", "children"),
    Input("btn-copiar-plan", "n_clicks"),
    State("tabla-plan", "columns"),
    State("tabla-plan", "derived_virtual_data"),
    prevent_initial_call=True,
)

# Mismo copiado para la tabla del mesociclo completo.
app.clientside_callback(
    """
    function(n, cols, filas) {
        if (!n) { return ""; }
        if (!cols || !filas || !filas.length) { return "Sin datos para copiar"; }
        var ids = cols.map(function(c){ return c.id; });
        var lineas = [cols.map(function(c){ return c.name; }).join("\\t")];
        filas.forEach(function(fila){
            lineas.push(ids.map(function(id){
                var v = fila[id];
                return (v === null || v === undefined) ? "" : String(v);
            }).join("\\t"));
        });
        var texto = lineas.join("\\n");
        function ok(){ return "✓ Copiado (" + filas.length + " filas)"; }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(texto);
            return ok();
        }
        var ta = document.createElement("textarea");
        ta.value = texto; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); } catch (e) {}
        document.body.removeChild(ta);
        return ok();
    }
    """,
    Output("copiar-meso-status", "children"),
    Input("btn-copiar-meso", "n_clicks"),
    State("tabla-meso", "columns"),
    State("tabla-meso", "derived_virtual_data"),
    prevent_initial_call=True,
)


@callback(
    Output("peso-panel", "children"),
    Input("peso-guardar", "n_clicks"),
    State("peso-input", "value"),
    State("cintura-input", "value"),
    prevent_initial_call=True,
)
def _guardar_peso_cb(n_clicks, peso, cintura):
    if _es_demo():
        return _panel_peso()
    if peso and 30 <= float(peso) <= 250:
        cin = float(cintura) if cintura and 40 <= float(cintura) <= 200 else None
        _registrar_peso(float(peso), cin)
        # mantiene los macros (g/día) y el motor alineados con el peso real
        guardar_config({"peso_corporal": float(peso)})
        nutricion.subir_meta_en_segundo_plano()  # la meta de proteina sigue a tu peso
    return _panel_peso()


@callback(
    Output("peso-panel", "children", allow_duplicate=True),
    Input("kcal-aplicar", "n_clicks"),
    State("kcal-delta", "data"),
    prevent_initial_call=True,
)
def _aplicar_kcal(n_clicks, delta):
    """Acepta el ajuste sugerido: queda en tu config y se reevalua en 2 semanas."""
    from dash import no_update
    if _es_demo() or not n_clicks or not delta:
        return no_update
    actual = int(cargar_config().get("kcal_ajuste") or 0)
    guardar_config({"kcal_ajuste": max(-1000, min(1000, actual + int(delta))),
                    "kcal_ajuste_fecha": date.today().isoformat()})
    nutricion.subir_meta_en_segundo_plano()
    return _panel_peso()


@callback(
    Output("menu-contenido", "children"),
    Input("menu-generar", "n_clicks"),
    State("menu-excluir", "value"),
    State("menu-supl", "value"),
    prevent_initial_call=True,
)
def _generar_menu_cb(n_clicks, excluir, supl):
    """Otro menu (otra semilla) con lo que no comes. En demo no se guarda nada."""
    import random
    import menu as mnu
    from planificar import lunes_objetivo
    extra = {"alimentos_excluidos": excluir or [], "menu_suplementos": bool(supl)}
    if not _es_demo():
        guardar_config(extra)
    try:
        m = mnu.generar_menu({**_menu_cfg(), **extra}, lunes_objetivo(), random.randrange(10 ** 6))
    except ValueError as e:
        return _menu_vista(str(e))
    if not _es_demo():
        mnu.guardar_local(m)
        _en_segundo_plano(mnu.subir_menu, m)        # la app ve el menu nuevo
    return _menu_vista(m)


@callback(
    Output("menu-contenido", "children", allow_duplicate=True),
    Output("precios-estado", "children"),
    Input("precios-guardar", "n_clicks"),
    State("precios-tabla", "data"),
    prevent_initial_call=True,
)
def _guardar_precios_cb(n_clicks, filas):
    from dash import no_update
    if _es_demo():
        return no_update, _aviso_demo("Modo demo: los precios no se guardan.")
    import alimentos_mx as alx
    import menu as mnu
    nuevos = {}
    for f in filas or []:
        try:
            nuevos[f["id"]] = float(f["precio"])
        except (TypeError, ValueError, KeyError):
            continue
    alx.guardar_precios(nuevos)
    m = _menu_actual(forzar=True)
    if isinstance(m, dict):
        _en_segundo_plano(mnu.subir_menu, m)
    return _menu_vista(m), "✓ Precios guardados: el menú se recalculó con ellos."


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
