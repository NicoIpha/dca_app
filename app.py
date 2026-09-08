"""
App de visualización de inversiones periódicas (DCA - Dollar Cost Averaging).

Ejecutar con:
    streamlit run app.py
"""
try:
    import streamlit as st
except ImportError as e:
    raise ImportError(
        "streamlit is not installed or could not be found. Install it with `pip install streamlit` "
        "and ensure your environment is correct. Original error: {}".format(e)
    )
import pandas as pd
import matplotlib.pyplot as plt

from core.simulation import (
    simulate_dca_fixed_rate,
    simulate_dca_from_prices,
    summarize_horizons,
)

st.set_page_config(page_title="Simulador de Inversiones DCA", layout="wide")

st.title("📈 Simulador de Inversiones Periódicas (DCA)")
st.caption(
    "Visualizá cuánto tendrías si invirtieras un monto fijo todos los meses "
    "en un activo, para distintos horizontes de tiempo."
)

# ---------------------------------------------------------------------------
# Sidebar: parámetros generales
# ---------------------------------------------------------------------------
st.sidebar.header("Parámetros")

modo = st.sidebar.radio(
    "Modo de simulación",
    ["Proyección (tasa asumida)", "Backtest histórico (datos reales)"],
    help=(
        "Proyección: usa una tasa de retorno anual que vos definís. "
        "Backtest: usa precios históricos reales de Yahoo Finance."
    ),
)

monto_mensual = st.sidebar.number_input(
    "Monto a invertir cada mes (USD)", min_value=1.0, value=200.0, step=10.0
)

horizontes_str = st.sidebar.text_input(
    "Horizontes en años (separados por coma)", value="1,2,5,10"
)
horizontes = sorted({int(h.strip()) for h in horizontes_str.split(",") if h.strip().isdigit()})

# ---------------------------------------------------------------------------
# Modo 1: Proyección con tasa fija asumida
# ---------------------------------------------------------------------------
if modo == "Proyección (tasa asumida)":
    tasa_anual = st.sidebar.slider(
        "Retorno anual asumido (%)", min_value=-20.0, max_value=60.0, value=15.0, step=0.5
    )

    st.subheader(f"Proyección invirtiendo ${monto_mensual:,.0f}/mes al {tasa_anual}% anual")

    resumen = summarize_horizons(monto_mensual, horizontes, tasa_anual)
    df_resumen = pd.DataFrame(resumen).T
    df_resumen.index.name = "Años"
    st.dataframe(
        df_resumen.style.format(
            {"invertido": "${:,.0f}", "valor_final": "${:,.0f}", "ganancia": "${:,.0f}", "retorno_%": "{:.1f}%"}
        ),
        use_container_width=True,
    )

    # Gráfico: evolución mes a mes para el horizonte más largo
    max_years = max(horizontes) if horizontes else 10
    res_full = simulate_dca_fixed_rate(monto_mensual, max_years * 12, tasa_anual)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(res_full.months, res_full.invested, label="Capital invertido", linestyle="--")
    ax.plot(res_full.months, res_full.portfolio_value, label="Valor de la cartera")
    ax.set_xlabel("Mes")
    ax.set_ylabel("USD")
    ax.set_title(f"Evolución a {max_years} años")
    ax.legend()
    ax.grid(alpha=0.3)
    st.pyplot(fig)

# ---------------------------------------------------------------------------
# Modo 2: Backtest histórico con datos reales (yfinance)
# ---------------------------------------------------------------------------
else:
    ticker = st.sidebar.text_input("Ticker (ej: NVDA, AAPL, SPY)", value="NVDA")
    max_years_disponibles = st.sidebar.slider(
        "Años de historia a descargar", min_value=1, max_value=20, value=10
    )

    st.subheader(f"Backtest histórico: ${monto_mensual:,.0f}/mes en {ticker.upper()}")

    if st.sidebar.button("Descargar datos y simular"):
        try:
            from core.data_fetcher import get_monthly_closes

            with st.spinner("Descargando datos de Yahoo Finance..."):
                fechas, precios = get_monthly_closes(ticker.upper(), max_years_disponibles)

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
                st.warning(
                    f"No hay suficiente historial ({len(precios)} meses) para los horizontes pedidos."
                )
            else:
                df_resumen = pd.DataFrame(resultados_por_horizonte).T
                df_resumen.index.name = "Años"
                st.dataframe(
                    df_resumen.style.format(
                        {"invertido": "${:,.0f}", "valor_final": "${:,.0f}", "ganancia": "${:,.0f}", "retorno_%": "{:.1f}%"}
                    ),
                    use_container_width=True,
                )

                # Gráfico completo con todo el histórico descargado
                res_full = simulate_dca_from_prices(monto_mensual, precios)
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(res_full.months, res_full.invested, label="Capital invertido", linestyle="--")
                ax.plot(res_full.months, res_full.portfolio_value, label="Valor de la cartera")
                ax.set_xlabel("Mes")
                ax.set_ylabel("USD")
                ax.set_title(f"Evolución histórica real - {ticker.upper()}")
                ax.legend()
                ax.grid(alpha=0.3)
                st.pyplot(fig)

        except ImportError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
    else:
        st.info("Configurá los parámetros en la barra lateral y hacé clic en 'Descargar datos y simular'.")

st.divider()
st.caption(
    "⚠️ Esta herramienta es solo para fines educativos/exploratorios. "
    "Los retornos pasados no garantizan resultados futuros, y toda proyección "
    "asume una tasa constante que en la realidad varía mes a mes."
)
