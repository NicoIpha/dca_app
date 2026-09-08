"""
Estilo visual compartido para los gráficos de línea de la app (Plotly).

El fondo de los gráficos es TRANSPARENTE a propósito: así se adaptan
solos tanto si Streamlit está en tema claro como oscuro (el tema
efectivo depende de la configuración de cada instalación — no hay
forma confiable de detectarlo desde el script), en vez de asumir un
tema fijo y verse mal en el otro. Se llama a los gráficos con
`st.plotly_chart(fig, theme="streamlit")` (el default) para que
Streamlit termine de adaptar tipografía y grilla a su tema activo.

Los 3 colores de las estrategias (guardar / plazo fijo / S&P 500) son
un orden fijo de una paleta categórica validada para daltonismo — se
usan siempre en el mismo orden, nunca se reasignan según el rango o el
gráfico, así "azul" significa siempre lo mismo en toda la app. Son los
tonos calibrados para fondo claro (más se usa el mismo tono sobre
fondo oscuro, se ve un poco menos saturado pero se sigue distinguiendo
bien).
"""
from typing import Dict, List, Optional

import plotly.graph_objects as go

GRID_COLOR = "rgba(128,128,128,0.25)"
MUTED_COLOR = "#888888"
META_COLOR = "#888888"  # línea de meta: gris neutro, no es una serie más

# Orden fijo (no cambiar el mapeo clave -> color; ver color-formula del
# criterio de diseño de gráficos: la identidad de una serie no cambia
# según qué tan larga sea la lista).
SERIES_COLORS: Dict[str, str] = {
    "guardar": "#2a78d6",  # azul
    "plazo_fijo": "#eb6834",  # naranja
    "sp500": "#1baf7a",  # aqua/verde
}

SERIES_LABELS: Dict[str, str] = {
    "guardar": "Guardar la plata",
    "plazo_fijo": "Plazo fijo (equiv. USD)",
    "sp500": "S&P 500",
}

SERIES_ORDER = ("guardar", "plazo_fijo", "sp500")


def legend_html() -> str:
    """Referencia de colores en HTML (mismo patrón que la leyenda de
    rubros en pages/1_Perfil.py), para mostrar una sola vez arriba de
    varios gráficos chicos que no necesitan repetir su propia leyenda."""
    puntos = " &nbsp;&nbsp; ".join(
        f'<span style="color:{SERIES_COLORS[k]};">●</span> {SERIES_LABELS[k]}' for k in SERIES_ORDER
    )
    return f'<div style="font-size:13px; color:#999;">{puntos}</div>'


def _base_layout(height: int, show_legend: bool, compact: bool) -> dict:
    """
    Fondo transparente a propósito (ver docstring del módulo): no se
    fuerza plot_bgcolor/paper_bgcolor/font.color acá, para que tanto el
    fondo de la página como el de `st.plotly_chart(fig,
    theme="streamlit")` terminen de adaptar tipografía y superficie al
    tema activo (claro u oscuro) de quien esté corriendo la app.
    """
    margin = dict(l=44, r=12, t=10, b=28) if compact else dict(l=56, r=16, t=16, b=40)
    return dict(
        height=height,
        margin=margin,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=GRID_COLOR, zeroline=False, color=MUTED_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, zeroline=False, color=MUTED_COLOR, tickprefix="$", separatethousands=True),
        hovermode="x unified",
    )


def build_goal_progress_figure(
    series: Dict[str, Optional[List[float]]],
    goal_amount: float,
    horizon_months: int,
    meses_llegada: Optional[Dict[str, Optional[int]]] = None,
    height: int = 230,
    show_legend: bool = False,
) -> go.Figure:
    """
    Gráfico chico "cuánto crece la plata hasta la meta" para una sola
    meta de ahorro. `series` trae, por estrategia, la lista de valores
    de cartera mes a mes (mes 1 en adelante); una estrategia sin datos
    (ej. plazo fijo sin conexión al BCRA) se omite pasando None.
    `meses_llegada` (opcional) marca con un punto en qué mes cada
    estrategia cruza la meta, si lo hace dentro de `horizon_months`.
    """
    fig = go.Figure()
    meses_llegada = meses_llegada or {}

    for key in SERIES_ORDER:
        valores = series.get(key)
        if not valores:
            continue
        meses_x = list(range(1, len(valores) + 1))
        fig.add_trace(
            go.Scatter(
                x=meses_x,
                y=valores,
                mode="lines",
                name=SERIES_LABELS[key],
                line=dict(color=SERIES_COLORS[key], width=2),
                hovertemplate="Mes %{x}: $%{y:,.0f}<extra>" + SERIES_LABELS[key] + "</extra>",
            )
        )

        mes_llega = meses_llegada.get(key)
        if mes_llega and mes_llega <= horizon_months:
            fig.add_trace(
                go.Scatter(
                    x=[mes_llega],
                    y=[goal_amount],
                    mode="markers",
                    marker=dict(color=SERIES_COLORS[key], size=9),
                    showlegend=False,
                    hovertemplate=f"Llega a la meta en el mes {mes_llega}<extra>{SERIES_LABELS[key]}</extra>",
                )
            )

    fig.add_hline(y=goal_amount, line=dict(color=META_COLOR, width=1.5, dash="dash"))

    fig.update_layout(**_base_layout(height, show_legend, compact=True))
    fig.update_xaxes(range=[0, horizon_months])
    return fig


def build_comparison_figure(
    res_ahorro,
    res_tasa_fija=None,
    tasa_fija_usd_anual: Optional[float] = None,
    res_sp500=None,
    height: int = 420,
) -> go.Figure:
    """Gráfico grande de "Tu panorama": capital aportado + las 3
    estrategias a lo largo del horizonte completo (ej. 10 años)."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=res_ahorro.months,
            y=res_ahorro.invested,
            mode="lines",
            name="Capital aportado",
            line=dict(color=MUTED_COLOR, width=1.5, dash="dot"),
            hovertemplate="Mes %{x}: $%{y:,.0f}<extra>Capital aportado</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=res_ahorro.months,
            y=res_ahorro.portfolio_value,
            mode="lines",
            name=SERIES_LABELS["guardar"],
            line=dict(color=SERIES_COLORS["guardar"], width=2),
            hovertemplate="Mes %{x}: $%{y:,.0f}<extra>" + SERIES_LABELS["guardar"] + "</extra>",
        )
    )

    if res_tasa_fija is not None:
        label = (
            f"Plazo fijo (equiv. USD, {tasa_fija_usd_anual:.1f}%/año)"
            if tasa_fija_usd_anual is not None
            else SERIES_LABELS["plazo_fijo"]
        )
        fig.add_trace(
            go.Scatter(
                x=res_tasa_fija.months,
                y=res_tasa_fija.portfolio_value,
                mode="lines",
                name=label,
                line=dict(color=SERIES_COLORS["plazo_fijo"], width=2),
                hovertemplate="Mes %{x}: $%{y:,.0f}<extra>" + label + "</extra>",
            )
        )

    if res_sp500 is not None:
        label_sp500 = "S&P 500 (histórico real)"
        fig.add_trace(
            go.Scatter(
                x=res_sp500.months,
                y=res_sp500.portfolio_value,
                mode="lines",
                name=label_sp500,
                line=dict(color=SERIES_COLORS["sp500"], width=2),
                hovertemplate="Mes %{x}: $%{y:,.0f}<extra>" + label_sp500 + "</extra>",
            )
        )

    fig.update_layout(**_base_layout(height, show_legend=True, compact=False))
    fig.update_xaxes(title_text="Mes")
    fig.update_yaxes(title_text="USD")
    return fig
