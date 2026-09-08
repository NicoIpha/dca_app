"""
Sección Perfil: cartera real del usuario.

Formulario para agregar una posición:
- Ticker: se elige de una lista de las ~50 empresas más conocidas, con
  búsqueda a medida que se escribe. También se puede cargar un ticker
  que no esté en esa lista.
- Precio de compra: se autocompleta con el precio de mercado actual,
  pero se puede editar.
- Monto invertido: el monto en USD que pusiste en esa posición (la
  cantidad de acciones se calcula sola).

Después se muestra la composición de la cartera en un gráfico de torta
interactivo (coloreado por rubro/industria: al pasar el mouse por un
ticker de la lista se resalta su porción en el gráfico), más el
resumen de invertido / valor actual / ganancia.
"""
import streamlit as st
import streamlit.components.v1 as components

from core.portfolio import load_portfolio, save_portfolio, add_holding, remove_holding
from core.ticker_catalog import get_display_options, parse_ticker_from_display, remember_ticker
from core.classification import get_category, get_color, CATEGORY_COLORS
from core.pie_chart import build_interactive_pie

try:
    from core.data_fetcher import get_current_price
except ImportError:
    get_current_price = None

st.set_page_config(page_title="Perfil - Cartera", layout="wide")
st.title("👤 Perfil de Inversor")
st.caption("Cargá tus posiciones reales para ver cómo está compuesta tu cartera hoy.")

if "holdings" not in st.session_state:
    st.session_state.holdings = load_portfolio()

# ---------------------------------------------------------------------------
# Formulario para agregar / actualizar una posición
# ---------------------------------------------------------------------------
st.subheader("Agregar posición")

OTRO_OPCION = "Otro (escribir ticker manualmente)"
opciones_ticker = [OTRO_OPCION] + get_display_options()

seleccion = st.selectbox(
    "Ticker",
    opciones_ticker,
    index=0,
    help="Escribí el ticker o el nombre de la empresa para filtrar la lista. También sirve para cripto (ej: BTC-USD), índices (ej: ^GSPC) o CEDEARs (ej: AAPL.BA) usando 'Otro'.",
)

if seleccion == OTRO_OPCION:
    ticker_input = st.text_input(
        "Escribí el ticker manualmente", placeholder="ej: PYPL, BTC-USD, ^GSPC, AAPL.BA"
    ).upper().strip()
else:
    ticker_input = parse_ticker_from_display(seleccion)

precio_mercado = None
if ticker_input and get_current_price is not None:
    try:
        with st.spinner(f"Consultando precio de mercado de {ticker_input}..."):
            precio_mercado = get_current_price(ticker_input)
        st.info(f"💲 Precio de mercado actual de **{ticker_input}**: \\${precio_mercado:,.2f}")
    except Exception:
        st.warning(f"No se pudo obtener el precio de mercado de {ticker_input} automáticamente.")
elif ticker_input and get_current_price is None:
    st.warning("Falta core.data_fetcher.get_current_price para autocompletar el precio.")

usar_otro_precio = st.checkbox(
    "Usar un precio distinto al de mercado actual (ej: el precio al que compraste en su momento)",
    value=(precio_mercado is None and bool(ticker_input)),
)

if usar_otro_precio or precio_mercado is None:
    precio_compra = st.number_input(
        "Precio de compra (USD)",
        min_value=0.0,
        step=1.0,
        value=float(precio_mercado) if precio_mercado else 0.0,
    )
else:
    precio_compra = precio_mercado
    st.caption(f"Se va a usar el precio de mercado actual: \\${precio_compra:,.2f}")

monto_invertido = st.number_input("Monto invertido (USD)", min_value=0.0, step=10.0)

if st.button("Agregar / actualizar posición"):
    if not ticker_input:
        st.warning("Ingresá un ticker válido.")
    elif monto_invertido <= 0:
        st.warning("Ingresá un monto invertido mayor a 0.")
    elif not precio_compra or precio_compra <= 0:
        st.warning("Ingresá o confirmá un precio de compra válido.")
    else:
        shares = monto_invertido / precio_compra
        st.session_state.holdings = add_holding(st.session_state.holdings, ticker_input, shares, precio_compra)
        save_portfolio(st.session_state.holdings)
        # si el ticker no estaba en la lista curada (se escribió a mano con
        # "Otro" y se encontró por Yahoo Finance), queda guardado para que
        # aparezca en el selector de acá en adelante.
        remember_ticker(ticker_input)
        st.success(
            f"Posición en {ticker_input} guardada: \\${monto_invertido:,.2f} invertidos "
            f"(≈ {shares:.4f} acciones a \\${precio_compra:,.2f})."
        )
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Tabla de posiciones
# ---------------------------------------------------------------------------
if not st.session_state.holdings:
    st.info("Todavía no cargaste ninguna posición. Usá el formulario de arriba para empezar.")
else:
    st.subheader("Tus posiciones")
    for h in list(st.session_state.holdings):
        monto_original = h.shares * h.avg_price
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(f"**{h.ticker}**")
        c2.write(f"${monto_original:,.2f} invertidos")
        c3.write(f"≈ {h.shares:.4f} acciones a \\${h.avg_price:,.2f}")
        if c4.button("🗑️", key=f"del_{h.ticker}"):
            st.session_state.holdings = remove_holding(st.session_state.holdings, h.ticker)
            save_portfolio(st.session_state.holdings)
            st.rerun()

    st.divider()
    st.subheader("Distribución de la cartera")

    if get_current_price is None:
        st.warning("Falta core.data_fetcher.get_current_price para calcular valores actuales.")
    else:
        valores = {}
        errores = []
        for h in st.session_state.holdings:
            try:
                precio_actual = get_current_price(h.ticker)
                valores[h.ticker] = precio_actual * h.shares
            except Exception:
                errores.append(h.ticker)

        if errores:
            st.warning(f"No se pudo obtener precio actual para: {', '.join(errores)}")

        if valores:
            # categoría de cada ticker (una sola vez, antes de filtrar/mostrar nada)
            categoria_por_ticker = {t: get_category(t) for t in valores}
            categorias_presentes = sorted(set(categoria_por_ticker.values()))

            if "filtro_categoria" not in st.session_state:
                st.session_state.filtro_categoria = None

            st.write("**Filtrar por rubro** (clic de nuevo en el mismo para volver a ver todo):")
            cols_filtro = st.columns(len(categorias_presentes) + 1)

            if cols_filtro[0].button(
                "Todos",
                type="primary" if st.session_state.filtro_categoria is None else "secondary",
                use_container_width=True,
            ):
                st.session_state.filtro_categoria = None
                st.rerun()

            for i, cat in enumerate(categorias_presentes, start=1):
                activo = st.session_state.filtro_categoria == cat
                if cols_filtro[i].button(cat, type="primary" if activo else "secondary", use_container_width=True):
                    st.session_state.filtro_categoria = None if activo else cat
                    st.rerun()

            filtro = st.session_state.filtro_categoria

            if filtro:
                valores_mostrados = {t: v for t, v in valores.items() if categoria_por_ticker[t] == filtro}
                holdings_mostrados = [
                    h for h in st.session_state.holdings if categoria_por_ticker.get(h.ticker) == filtro
                ]
                st.caption(f"Mostrando solo: **{filtro}**")
            else:
                valores_mostrados = valores
                holdings_mostrados = st.session_state.holdings

            total_valor = sum(valores_mostrados.values())
            total_invertido = sum(h.shares * h.avg_price for h in holdings_mostrados)
            ganancia = total_valor - total_invertido
            retorno_pct = (ganancia / total_invertido * 100) if total_invertido else 0

            col_metricas, col_grafico = st.columns([1, 2])

            with col_metricas:
                st.metric("Invertido", f"${total_invertido:,.0f}")
                st.metric("Valor actual", f"${total_valor:,.0f}")
                st.metric("Ganancia / Pérdida", f"${ganancia:,.0f}", delta=f"{retorno_pct:.1f}%")

            with col_grafico:
                items = [
                    {"ticker": t, "value": v, "color": get_color(categoria_por_ticker[t])}
                    for t, v in valores_mostrados.items()
                ]
                html = build_interactive_pie(items, size=280)
                components.html(html, height=max(300, 60 * len(items)), scrolling=False)

                # referencia de colores por rubro presentes en la cartera completa
                referencia = " &nbsp;&nbsp; ".join(
                    f'<span style="color:{CATEGORY_COLORS.get(cat, "#bdbdbd")};">●</span> {cat}'
                    for cat in categorias_presentes
                )
                st.markdown(
                    f'<div style="font-size:13px; color:#999;">{referencia}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No se pudo calcular el valor actual de ninguna posición.")
