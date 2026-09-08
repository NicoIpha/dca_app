"""
Sección Mercado: noticias de tus propias posiciones (si estás invertido
en Apple, acá aparecen noticias de Apple), más el top 10 de acciones
más rentables por rubro para 1, 3 y 5 años, y un buscador para
consultar cualquier ticker que no esté en la lista curada.
"""
import streamlit as st
import pandas as pd

from core.market import SECTOR_KEYS, PERIODS_YEARS, top_n_by_sector, search_ticker_returns
from core.portfolio import load_portfolio, save_portfolio, add_holding
from core.news import get_news_for_tickers, render_news_list
from core.onboarding import mark_visited
from core.ticker_catalog import remember_ticker

try:
    from core.data_fetcher import get_current_price
except ImportError:
    get_current_price = None

st.set_page_config(page_title="Mercado", layout="wide")
mark_visited("mercado")
st.title("🏦 Mercado por Rubro")

# ---------------------------------------------------------------------------
# Noticias de tus propias posiciones: lo primero que se ve acá, porque es
# lo más relevante para vos — qué está pasando con lo que ya tenés
# invertido, no solo el mercado en general.
# ---------------------------------------------------------------------------
st.subheader("📰 Noticias de tus posiciones")

tickers_cartera = [h.ticker for h in load_portfolio()]

if not tickers_cartera:
    st.caption("Cargá posiciones en la sección **Perfil** para ver acá noticias de tus inversiones.")
else:
    with st.spinner("Buscando noticias de tu cartera..."):
        try:
            noticias_cartera = get_news_for_tickers(tickers_cartera, max_items_per_ticker=3)
        except ImportError as e:
            st.error(str(e))
            noticias_cartera = []

    render_news_list(noticias_cartera, max_items=10)
    st.caption("Para noticias generales del mercado, andá a la sección **Noticias**.")

st.divider()

# ---------------------------------------------------------------------------
# Top 10 por rubro + buscador
# ---------------------------------------------------------------------------
st.subheader("Top 10 por rubro")
st.caption(
    "El listado de empresas de cada rubro se trae en vivo desde Yahoo Finance "
    "(se cachea 24hs para que la app no se ponga lenta). "
    "Si buscás algo que no aparece en el top, usá el buscador de abajo."
)

col1, col2 = st.columns([2, 1])
sector = col1.selectbox("Elegí un rubro", list(SECTOR_KEYS.keys()))
years = col2.radio("Horizonte", PERIODS_YEARS, format_func=lambda y: f"Últimos {y} año(s)", horizontal=True)

with st.spinner("Calculando retornos..."):
    try:
        top10 = top_n_by_sector(sector, years, n=10)
    except ImportError as e:
        st.error(str(e))
        top10 = []

if top10:
    df = pd.DataFrame(top10)
    df.index = df.index + 1
    st.subheader(f"Top 10 - {sector} - últimos {years} año(s)")
    st.dataframe(df.style.format({"retorno_%": "{:.1f}%"}), use_container_width=True)
else:
    st.info("No se pudieron calcular retornos para este rubro (revisá tu conexión a internet).")

st.divider()
st.subheader("🔍 Buscar otra firma")
st.caption(
    "Si el ticker no está en la lista de arriba, buscalo acá — si existe en "
    "Yahoo Finance, después lo podés sumar directo a tu cartera real."
)
ticker_busqueda = st.text_input("Ticker (no hace falta que esté en la lista de arriba)", placeholder="ej: SPY")

if st.button("Buscar") and ticker_busqueda:
    ticker_norm = ticker_busqueda.upper().strip()
    with st.spinner(f"Buscando {ticker_norm}..."):
        try:
            resultado = search_ticker_returns(ticker_norm)
        except Exception as e:
            st.error(f"No se pudo obtener información: {e}")
            resultado = None

        precio_encontrado = None
        if resultado and get_current_price is not None:
            try:
                precio_encontrado = get_current_price(ticker_norm)
            except Exception:
                precio_encontrado = None

    if resultado:
        # se guarda en session_state para que sobreviva a los reruns que
        # disparan los number_input de más abajo (precio / monto a agregar)
        st.session_state.ticker_encontrado = {"ticker": resultado["ticker"], "precio": precio_encontrado}
        st.session_state.retornos_encontrados = resultado

if st.session_state.get("ticker_encontrado"):
    ticker_hallado = st.session_state.ticker_encontrado["ticker"]
    precio_hallado = st.session_state.ticker_encontrado["precio"]
    retornos = st.session_state.get("retornos_encontrados", {})

    cols = st.columns(len(PERIODS_YEARS) + 1)
    cols[0].metric("Ticker", ticker_hallado)
    for i, years_key in enumerate(PERIODS_YEARS, start=1):
        valor = retornos.get(f"{years_key}a_%")
        cols[i].metric(f"Retorno {years_key}a", f"{valor:.1f}%" if valor is not None else "N/D")

    if precio_hallado is None:
        st.warning(
            f"No pudimos confirmar que **{ticker_hallado}** exista en Yahoo Finance "
            "ahora mismo (puede ser el ticker o falta de conexión). Revisalo antes de agregarlo."
        )

    with st.expander(f"➕ Agregar {ticker_hallado} a mi cartera", expanded=True):
        if precio_hallado:
            st.caption(f"Precio de mercado actual de {ticker_hallado}: \\${precio_hallado:,.2f}")

        col_precio, col_monto = st.columns(2)
        precio_compra_busqueda = col_precio.number_input(
            "Precio de compra (USD)",
            min_value=0.0,
            step=1.0,
            value=float(precio_hallado) if precio_hallado else 0.0,
            key="precio_compra_busqueda",
        )
        monto_busqueda = col_monto.number_input(
            "Monto invertido (USD)", min_value=0.0, step=10.0, key="monto_busqueda"
        )

        col_agregar, col_cancelar = st.columns([1, 1])
        if col_agregar.button(f"Agregar {ticker_hallado} a mi cartera", type="primary"):
            if monto_busqueda <= 0 or precio_compra_busqueda <= 0:
                st.warning("Ingresá un monto invertido y un precio de compra mayores a 0.")
            else:
                shares = monto_busqueda / precio_compra_busqueda
                holdings = add_holding(load_portfolio(), ticker_hallado, shares, precio_compra_busqueda)
                save_portfolio(holdings)
                # queda guardado para el selector de Perfil de acá en adelante
                remember_ticker(ticker_hallado)
                st.success(
                    f"Posición en {ticker_hallado} guardada: \\${monto_busqueda:,.2f} invertidos "
                    f"(≈ {shares:.4f} acciones a \\${precio_compra_busqueda:,.2f}). "
                    "Ya la vas a ver en la sección **Perfil**."
                )
                del st.session_state["ticker_encontrado"]
                st.session_state.pop("retornos_encontrados", None)
                st.rerun()

        if col_cancelar.button("Cancelar búsqueda"):
            del st.session_state["ticker_encontrado"]
            st.session_state.pop("retornos_encontrados", None)
            st.rerun()
