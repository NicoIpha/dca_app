"""
App de visualización de inversiones periódicas (DCA - Dollar Cost Averaging).

Ejecutar con:
    streamlit run Home.py
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from core.simulation import (
    simulate_dca_fixed_rate,
    simulate_dca_monthly_rate,
    simulate_dca_from_prices,
    summarize_horizons,
    annual_effective_to_monthly_rate,
)
from core.user_profile import load_profile, save_profile, UserProfile, BRACKETS
from core.risk_profile import load_result as load_risk_result
from core.portfolio import load_portfolio
from core.onboarding import (
    render_primeros_pasos,
    load_state as load_onboarding_state,
    save_state as save_onboarding_state,
)
from core.savings_goals import (
    GOAL_PRESETS,
    resolve_goal_amount,
    months_to_reach_goal,
    display_horizon_months,
    build_progress_series,
    format_years_months,
)
from core.charts import build_goal_progress_figure, build_comparison_figure, legend_html as series_legend_html

st.set_page_config(page_title="Simulador de Inversiones DCA", layout="wide")

st.title("📈 Simulador de Inversiones Periódicas (DCA)")
st.caption("Usá el menú de la izquierda para ir a Perfil de Riesgo, Perfil, Mercado o Noticias.")

# ---------------------------------------------------------------------------
# 🚀 Primeros pasos: guía para alguien que recién abre la app, con lo que
# ya hizo tildado solo. Se calcula perfil acá (antes de lo habitual) para
# saber si ese paso ya está completo.
# ---------------------------------------------------------------------------
perfil = load_profile()

render_primeros_pasos(
    tiene_perfil_riesgo=load_risk_result() is not None,
    tiene_monto_mensual=perfil is not None,
    tiene_cartera=len(load_portfolio()) > 0,
)

# ---------------------------------------------------------------------------
# Encuesta inicial: ¿cuánto le destina la persona a ahorrar por mes?
# Se persiste para no volver a preguntarla cada vez que se abre la app.
# ---------------------------------------------------------------------------

with st.expander("💰 ¿Cuánto le destinás a tus ahorros por mes?", expanded=(perfil is None)):
    st.caption(
        "No hace falta que sea exacto. Elegí el rango en el que más o menos entra "
        "lo que podés guardar cada mes, y lo vamos a usar para mostrarte un panorama."
    )

    claves_bracket = list(BRACKETS.keys())
    labels_bracket = [BRACKETS[k]["label"] for k in claves_bracket]
    index_default = claves_bracket.index(perfil.bracket) if perfil else 1

    label_elegido = st.radio("Elegí un rango", labels_bracket, index=index_default, horizontal=True)
    bracket_elegido = claves_bracket[labels_bracket.index(label_elegido)]

    monto_por_defecto = (
        perfil.monto_mensual
        if perfil and perfil.bracket == bracket_elegido
        else BRACKETS[bracket_elegido]["default_amount"]
    )

    monto_encuesta = st.number_input(
        "Ajustá el monto exacto si querés (USD por mes)",
        min_value=1.0,
        value=float(monto_por_defecto),
        step=5.0,
    )

    if st.button("Guardar y ver mi panorama"):
        save_profile(UserProfile(bracket=bracket_elegido, monto_mensual=monto_encuesta))
        st.rerun()

if perfil is None:
    st.info("👆 Elegí un rango arriba y guardá para ver tu panorama de ahorro vs. inversión.")
    st.stop()

# ---------------------------------------------------------------------------
# Datos de mercado compartidos: se traen de golpe, UNA SOLA VEZ POR SESIÓN
# (no en cada interacción), y se guardan en st.session_state. Se usan tanto
# en "Tu objetivo" como en el panorama de 10 años, más abajo.
# ---------------------------------------------------------------------------
HORIZONTE_ANIOS = 10


def _precargar_datos_de_mercado(horizonte_anios: int) -> dict:
    """Trae de una sola vez todos los datos externos que necesita Home
    (tasa de plazo fijo, dólar, devaluación histórica y precios del
    S&P 500). Se llama una única vez por sesión — ver el bloque de
    session_state más abajo — así que acá adentro no hay que preocuparse
    por cachear cada llamada por separado."""
    from core.bcra import get_tasa_plazo_fijo, get_dolar_actual, get_devaluacion_anual_historica
    from core.data_fetcher import get_monthly_closes

    datos = {
        "tasa_bcra": None,
        "error_bcra": None,
        "dolar_bcra": None,
        "devaluacion_bcra": None,
        "error_devaluacion": None,
        "tasa_mensual_pesos": None,
        "tasa_mensual_devaluacion": None,
        "tasa_mensual_usd": None,
        "tasa_fija_usd_anual": None,
        "sp500_disponible": False,
        "cagr_sp500": None,
        "error_sp500": None,
        "precios_sp500": None,
    }

    try:
        datos["tasa_bcra"] = get_tasa_plazo_fijo()
    except Exception as e:
        datos["error_bcra"] = str(e)

    try:
        datos["dolar_bcra"] = get_dolar_actual()
    except Exception:
        datos["dolar_bcra"] = None

    try:
        datos["devaluacion_bcra"] = get_devaluacion_anual_historica(5)
    except Exception as e:
        datos["error_devaluacion"] = str(e)

    plazo_fijo_disponible = datos["tasa_bcra"] is not None and datos["devaluacion_bcra"] is not None
    if plazo_fijo_disponible:
        # TNA es una tasa NOMINAL anual (lineal): el rendimiento mensual real
        # es simplemente TNA/12, no una raíz doceava (eso sería para una tasa
        # EFECTIVA/compuesta, que no es lo que informa el BCRA para plazo fijo).
        tasa_mensual_pesos = (datos["tasa_bcra"]["tasa"] / 100) / 12

        # la devaluación histórica sí es una tasa efectiva anual (CAGR), así
        # que su equivalente mensual sí se calcula con raíz doceava (compuesta).
        tasa_mensual_devaluacion = (1 + datos["devaluacion_bcra"] / 100) ** (1 / 12) - 1

        # cada mes, el rendimiento en pesos se "traduce" a dólares descontando
        # la devaluación de ese mismo mes
        tasa_mensual_usd = (1 + tasa_mensual_pesos) / (1 + tasa_mensual_devaluacion) - 1

        datos["tasa_mensual_pesos"] = tasa_mensual_pesos
        datos["tasa_mensual_devaluacion"] = tasa_mensual_devaluacion
        datos["tasa_mensual_usd"] = tasa_mensual_usd
        # solo a modo informativo para el texto: a qué % anual equivale esa tasa mensual
        datos["tasa_fija_usd_anual"] = ((1 + tasa_mensual_usd) ** 12 - 1) * 100

    # Precios históricos reales del S&P 500: se usan para el backtest del
    # panorama de 10 años, y también para estimar un CAGR de referencia
    # (misma descarga, sin pedirle los datos dos veces a Yahoo Finance).
    try:
        _, precios_sp500 = get_monthly_closes("^GSPC", horizonte_anios)
        datos["precios_sp500"] = precios_sp500
        datos["sp500_disponible"] = True
        if len(precios_sp500) >= 2:
            retorno_total = precios_sp500[-1] / precios_sp500[0]
            anios_datos = len(precios_sp500) / 12
            datos["cagr_sp500"] = (retorno_total ** (1 / anios_datos) - 1) * 100
    except Exception as e:
        datos["error_sp500"] = str(e)

    return datos


if "datos_mercado" not in st.session_state:
    with st.spinner("⏳ Cargando datos de mercado (tasa de plazo fijo, dólar y S&P 500)... esto pasa una sola vez por sesión."):
        st.session_state.datos_mercado = _precargar_datos_de_mercado(HORIZONTE_ANIOS)

datos_mercado = st.session_state.datos_mercado
tasa_bcra = datos_mercado["tasa_bcra"]
error_bcra = datos_mercado["error_bcra"]
dolar_bcra = datos_mercado["dolar_bcra"]
devaluacion_bcra = datos_mercado["devaluacion_bcra"]
error_devaluacion = datos_mercado["error_devaluacion"]
plazo_fijo_disponible = tasa_bcra is not None and devaluacion_bcra is not None
tasa_mensual_pesos = datos_mercado["tasa_mensual_pesos"]
tasa_mensual_devaluacion = datos_mercado["tasa_mensual_devaluacion"]
tasa_mensual_usd = datos_mercado["tasa_mensual_usd"]
tasa_fija_usd_anual = datos_mercado["tasa_fija_usd_anual"]
sp500_disponible = datos_mercado["sp500_disponible"]
cagr_sp500 = datos_mercado["cagr_sp500"]
error_sp500 = datos_mercado["error_sp500"]
precios_sp500 = datos_mercado["precios_sp500"]

# Esto sí se recalcula en cada rerun (no va en la precarga): es una cuenta
# local barata, sin red, que depende del monto mensual actual — que puede
# cambiar si la persona edita su ahorro mensual sin recargar la página.
if sp500_disponible:
    res_sp500 = simulate_dca_from_prices(perfil.monto_mensual, precios_sp500)

# ---------------------------------------------------------------------------
# 🎯 Tu objetivo: lo primero que se ve, para hacer tangible el ahorro.
# Un gráfico chico por cada meta típica, más un objetivo personalizado
# opcional, todos con la misma leyenda de colores (una sola vez arriba).
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🎯 Tu objetivo")
st.caption(
    f"Ahorrando \\${perfil.monto_mensual:,.0f} por mes, así de rápido llegarías a estas metas típicas "
    "con cada estrategia."
)
st.markdown(series_legend_html(), unsafe_allow_html=True)

tasa_mensual_sp500 = annual_effective_to_monthly_rate(cagr_sp500) if cagr_sp500 is not None else None
tasas_por_estrategia = {
    "guardar": 0.0,
    "plazo_fijo": tasa_mensual_usd if plazo_fijo_disponible else None,
    "sp500": tasa_mensual_sp500,
}


def _mostrar_objetivo(monto_objetivo: float, height: int = 230) -> None:
    if monto_objetivo <= 0:
        st.warning("Ingresá un monto mayor a 0 para ver cuánto tardarías en alcanzarlo.")
        return

    meses_por_estrategia = {
        key: months_to_reach_goal(perfil.monto_mensual, monto_objetivo, tasa) if tasa is not None else None
        for key, tasa in tasas_por_estrategia.items()
    }

    horizonte = display_horizon_months(meses_por_estrategia)
    series = build_progress_series(perfil.monto_mensual, horizonte, tasas_por_estrategia)

    fig = build_goal_progress_figure(series, monto_objetivo, horizonte, meses_llegada=meses_por_estrategia, height=height)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    resumen = " · ".join(
        f"{format_years_months(meses_por_estrategia[k])}"
        for k in ("guardar", "plazo_fijo", "sp500")
        if tasas_por_estrategia[k] is not None
    )
    st.caption(f"${monto_objetivo:,.0f} — {resumen}")


presets_fijos = [p for p in GOAL_PRESETS if p["key"] != "personalizado"]
cols_objetivos = st.columns(len(presets_fijos))
for col, preset in zip(cols_objetivos, presets_fijos):
    with col:
        st.markdown(f"**{preset['label']}**")
        monto = resolve_goal_amount(preset["key"], perfil.monto_mensual)
        _mostrar_objetivo(monto)

with st.expander("➕ Agregar un objetivo personalizado"):
    monto_personalizado = st.number_input("Monto objetivo (USD)", min_value=0.0, value=50_000.0, step=1_000.0)
    if monto_personalizado > 0:
        _mostrar_objetivo(monto_personalizado, height=280)

if cagr_sp500 is not None:
    st.caption(
        f"El número del S&P 500 asume que, de acá en adelante, repite el rendimiento anualizado "
        f"que tuvo en los últimos {HORIZONTE_ANIOS} años reales ({cagr_sp500:.1f}% anual) — no es una "
        f"promesa a futuro, los mercados varían mucho de una década a la otra."
    )

st.divider()

# ---------------------------------------------------------------------------
# Panorama inicial: 3 escenarios con el monto que la persona indicó
# ---------------------------------------------------------------------------
st.subheader(f"Tu panorama ahorrando \\${perfil.monto_mensual:,.0f} por mes")
st.caption(
    f"Comparamos tres caminos posibles para ese mismo dinero, guardado durante {HORIZONTE_ANIOS} años: "
    "guardarlo tal cual, ponerlo a una tasa de interés fija, o invertirlo en el S&P 500 "
    "(el índice de las 500 empresas más grandes de EE.UU.)."
)

MESES = HORIZONTE_ANIOS * 12

# Escenario 1: solo guardar el dinero (0% de rendimiento)
res_ahorro = simulate_dca_fixed_rate(perfil.monto_mensual, MESES, annual_return_pct=0)

# Escenario 2: plazo fijo tradicional en pesos (dato real vía ArgentinaDatos/BCRA),
# convertido a su equivalente en dólares para poder graficarlo junto a los otros
# escenarios, que están en USD. (tasa_bcra / dolar_bcra / devaluacion_bcra ya se
# buscaron más arriba, junto con el resto de los datos de mercado compartidos.)
col_dato1, col_dato2, col_dato3 = st.columns(3)
if tasa_bcra:
    col_dato1.metric(
        "Tasa de plazo fijo (30 días)",
        f"{tasa_bcra['tasa']:.2f}% TNA",
        help=f"Dato al {tasa_bcra['fecha']}. En pesos argentinos (ARS). {tasa_bcra['descripcion']}",
    )
else:
    col_dato1.metric("Tasa de plazo fijo (30 días)", "No disponible")
    if error_bcra:
        with st.expander("Ver detalle del error"):
            st.code(error_bcra)

if dolar_bcra:
    col_dato2.metric(
        "Dólar oficial (venta)",
        f"${dolar_bcra['cotizacion']:,.2f} ARS",
        help=f"Dato al {dolar_bcra['fecha']}.",
    )
else:
    col_dato2.metric("Dólar oficial (venta)", "No disponible")

if devaluacion_bcra is not None:
    col_dato3.metric(
        "Devaluación anual (últimos 5 años)",
        f"{devaluacion_bcra:.1f}%",
        help="Variación anualizada real del dólar oficial en los últimos 5 años.",
    )
else:
    col_dato3.metric("Devaluación anual (últimos 5 años)", "No disponible")
    if error_devaluacion:
        with st.expander("Ver detalle del error"):
            st.code(error_devaluacion)

if plazo_fijo_disponible:
    st.caption(
        f"➡️ TNA de plazo fijo {tasa_bcra['tasa']:.1f}% ÷ 12 = **{tasa_mensual_pesos*100:.2f}% mensual en pesos**. "
        f"Descontando la devaluación mensual equivalente ({tasa_mensual_devaluacion*100:.2f}%), "
        f"eso queda en **{tasa_mensual_usd*100:.2f}% mensual en dólares** "
        f"(≈ {tasa_fija_usd_anual:.1f}% anual equivalente)."
    )

    res_tasa_fija = simulate_dca_monthly_rate(perfil.monto_mensual, MESES, tasa_mensual_usd)
else:
    st.warning("No se pudo calcular el escenario de plazo fijo (faltan datos reales). Se muestran solo los otros dos escenarios.")

# Escenario 3: histórico real del S&P 500 (qué hubiese pasado invirtiendo los
# últimos 10 años). res_sp500 / sp500_disponible ya se calcularon más arriba.
if not sp500_disponible:
    st.warning(f"No se pudo traer el historial del S&P 500 ahora mismo ({error_sp500}). Mostrando los otros dos escenarios.")

fig_panorama = build_comparison_figure(
    res_ahorro,
    res_tasa_fija=res_tasa_fija if plazo_fijo_disponible else None,
    tasa_fija_usd_anual=tasa_fija_usd_anual if plazo_fijo_disponible else None,
    res_sp500=res_sp500 if sp500_disponible else None,
)
st.plotly_chart(fig_panorama, use_container_width=True, config={"displayModeBar": False})

# Tabla resumen a 1 / 5 / 10 años
horizontes_tabla = [1, 5, 10]
filas = []
for years in horizontes_tabla:
    idx = min(years * 12, len(res_ahorro.months)) - 1
    fila = {
        "Años": years,
        "Aportado": res_ahorro.invested[idx],
        "Solo ahorrar": res_ahorro.portfolio_value[idx],
    }
    if plazo_fijo_disponible:
        fila["Plazo fijo (equiv. USD)"] = res_tasa_fija.portfolio_value[idx]
    if sp500_disponible:
        idx_sp = min(idx, len(res_sp500.portfolio_value) - 1)
        fila["S&P 500"] = res_sp500.portfolio_value[idx_sp]
    filas.append(fila)

df_comparacion = pd.DataFrame(filas).set_index("Años")
st.dataframe(
    df_comparacion.style.format({col: "${:,.0f}" for col in df_comparacion.columns}),
    use_container_width=True,
)

st.caption(
    "⚠️ Los tres escenarios ya están expresados en dólares (USD) para poder compararlos en el mismo "
    "gráfico. El del plazo fijo surge de convertir la tasa real en pesos usando una devaluación "
    "esperada del peso que vos podés ajustar — es una estimación basada en el pasado, no una "
    "predicción. Además, el escenario del S&P 500 usa datos históricos reales, no una promesa a "
    "futuro: los retornos pasados no garantizan resultados futuros."
)

st.divider()

# ---------------------------------------------------------------------------
# Simulador avanzado (lo que antes era la página principal)
# ---------------------------------------------------------------------------
with st.expander("🔧 Simulador avanzado (elegí tasa, ticker y horizontes a mano)"):
    modo = st.radio(
        "Modo de simulación",
        ["Proyección (tasa asumida)", "Backtest histórico (datos reales)"],
        help=(
            "Proyección: usa una tasa de retorno anual que vos definís. "
            "Backtest: usa precios históricos reales de Yahoo Finance."
        ),
    )

    col1, col2 = st.columns(2)
    monto_mensual = col1.number_input(
        "Monto a invertir cada mes (USD)", min_value=1.0, value=float(perfil.monto_mensual), step=10.0
    )
    horizontes_str = col2.text_input("Horizontes en años (separados por coma)", value="1,2,5,10")
    horizontes = sorted({int(h.strip()) for h in horizontes_str.split(",") if h.strip().isdigit()})

    if modo == "Proyección (tasa asumida)":
        tasa_anual = st.slider(
            "Retorno anual asumido (%)", min_value=-20.0, max_value=60.0, value=15.0, step=0.5
        )

        st.subheader(f"Proyección invirtiendo \\${monto_mensual:,.0f}/mes al {tasa_anual}% anual")

        resumen = summarize_horizons(monto_mensual, horizontes, tasa_anual)
        df_resumen = pd.DataFrame(resumen).T
        df_resumen.index.name = "Años"
        st.dataframe(
            df_resumen.style.format(
                {"invertido": "${:,.0f}", "valor_final": "${:,.0f}", "ganancia": "${:,.0f}", "retorno_%": "{:.1f}%"}
            ),
            use_container_width=True,
        )

        max_years = max(horizontes) if horizontes else 10
        res_full = simulate_dca_fixed_rate(monto_mensual, max_years * 12, tasa_anual)

        fig2, ax2 = plt.subplots(figsize=(10, 5))
        ax2.plot(res_full.months, res_full.invested, label="Capital invertido", linestyle="--")
        ax2.plot(res_full.months, res_full.portfolio_value, label="Valor de la cartera")
        ax2.set_xlabel("Mes")
        ax2.set_ylabel("USD")
        ax2.set_title(f"Evolución a {max_years} años")
        ax2.legend()
        ax2.grid(alpha=0.3)
        st.pyplot(fig2)

    else:
        ticker = st.text_input("Ticker (ej: NVDA, AAPL, SPY)", value="NVDA")
        max_years_disponibles = st.slider("Años de historia a descargar", min_value=1, max_value=20, value=10)

        st.subheader(f"Backtest histórico: \\${monto_mensual:,.0f}/mes en {ticker.upper()}")

        if st.button("Descargar datos y simular"):
            try:
                from core.data_fetcher import get_monthly_closes as _get_monthly_closes

                with st.spinner("Descargando datos de Yahoo Finance..."):
                    fechas, precios = _get_monthly_closes(ticker.upper(), max_years_disponibles)

                resultados_por_horizonte = {}
                for years in horizontes:
                    n_meses = years * 12
                    if n_meses > len(precios):
                        continue
                    precios_recortados = precios[-n_meses:]
                    res = simulate_dca_from_prices(monto_mensual, precios_recortados)
                    resultados_por_horizonte[years] = {
                        "invertido": round(res.total_invested, 2),
                        "valor_final": round(res.final_value, 2),
                        "ganancia": round(res.gain, 2),
                        "retorno_%": round(res.total_return_pct, 2),
                    }

                if not resultados_por_horizonte:
                    st.warning(f"No hay suficiente historial ({len(precios)} meses) para los horizontes pedidos.")
                else:
                    df_resumen = pd.DataFrame(resultados_por_horizonte).T
                    df_resumen.index.name = "Años"
                    st.dataframe(
                        df_resumen.style.format(
                            {"invertido": "${:,.0f}", "valor_final": "${:,.0f}", "ganancia": "${:,.0f}", "retorno_%": "{:.1f}%"}
                        ),
                        use_container_width=True,
                    )

                    res_full = simulate_dca_from_prices(monto_mensual, precios)
                    fig3, ax3 = plt.subplots(figsize=(10, 5))
                    ax3.plot(res_full.months, res_full.invested, label="Capital invertido", linestyle="--")
                    ax3.plot(res_full.months, res_full.portfolio_value, label="Valor de la cartera")
                    ax3.set_xlabel("Mes")
                    ax3.set_ylabel("USD")
                    ax3.set_title(f"Evolución histórica real - {ticker.upper()}")
                    ax3.legend()
                    ax3.grid(alpha=0.3)
                    st.pyplot(fig3)

            except ImportError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
        else:
            st.info("Configurá los parámetros de arriba y hacé clic en 'Descargar datos y simular'.")

st.divider()
st.caption(
    "⚠️ Esta herramienta es solo para fines educativos/exploratorios. "
    "Los retornos pasados no garantizan resultados futuros, y toda proyección "
    "asume una tasa constante que en la realidad varía mes a mes."
)

estado_onboarding = load_onboarding_state()
if estado_onboarding.dismissed:
    if st.button("🔄 Volver a mostrar la guía de primeros pasos"):
        estado_onboarding.dismissed = False
        save_onboarding_state(estado_onboarding)
        st.rerun()
