"""
Sección Noticias: titulares con el resumen que trae la propia fuente
(no generado por IA) y link directo a la nota completa.
Se muestran noticias generales de mercado y, si hay posiciones cargadas
en Perfil, también noticias específicas de esos tickers.
"""
import streamlit as st

from core.news import get_general_news, get_news_for_tickers, render_news_list
from core.portfolio import load_portfolio
from core.onboarding import mark_visited

st.set_page_config(page_title="Noticias", layout="wide")
mark_visited("noticias")
st.title("📰 Noticias")
st.caption("Titulares, imagen y resumen tal cual los publica cada fuente, con link a la nota completa.")

tab_general, tab_cartera = st.tabs(["Mercado general", "De mi cartera"])

with tab_general:
    with st.spinner("Cargando noticias..."):
        try:
            noticias = get_general_news()
        except ImportError as e:
            st.error(str(e))
            noticias = []
    render_news_list(noticias)

with tab_cartera:
    holdings = load_portfolio()
    tickers = [h.ticker for h in holdings]
    if not tickers:
        st.info("Cargá posiciones en la sección **Perfil** para ver noticias específicas de tu cartera.")
    else:
        with st.spinner("Cargando noticias de tu cartera..."):
            try:
                noticias = get_news_for_tickers(tickers)
            except ImportError as e:
                st.error(str(e))
                noticias = []
        render_news_list(noticias)
