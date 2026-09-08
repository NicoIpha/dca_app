"""
Noticias financieras: trae titulares con su resumen (la síntesis que
viene con la propia noticia), la imagen que trae el feed (si la trae)
y un link directo a la nota completa, usando feeds RSS públicos.
No inventa ni resume nada con IA: muestra tal cual lo que publica cada
fuente. La imagen se referencia por URL (no se descarga ni reprocesa
acá), así se mantiene la calidad original con el menor costo posible.
"""
import re
from typing import List, Dict, Optional

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    st = None
    def cache_data(*args, **kwargs):
        def wrapper(fn):
            return fn
        return wrapper

# Feeds generales de mercado (se pueden agregar más).
GENERAL_FEEDS = {
    "MarketWatch - Top Stories": "http://feeds.marketwatch.com/marketwatch/topstories/",
    "CNBC - Markets": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
}


def _ticker_feed_url(ticker: str) -> str:
    return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


def _extract_image_url(entry) -> str:
    """Busca la imagen que trae el propio item del feed, probando los
    lugares más comunes donde suele venir (sin descargarla)."""
    media_content = entry.get("media_content")
    if media_content:
        url = media_content[0].get("url")
        if url:
            return url

    media_thumb = entry.get("media_thumbnail")
    if media_thumb:
        url = media_thumb[0].get("url")
        if url:
            return url

    for enc in entry.get("enclosures", []) or []:
        tipo = enc.get("type", "") or ""
        href = enc.get("href") or enc.get("url")
        if href and (tipo.startswith("image") or not tipo):
            return href

    resumen_html = entry.get("summary", "") or ""
    match = re.search(r'<img[^>]+src="([^"]+)"', resumen_html)
    if match:
        return match.group(1)

    return ""


@cache_data(ttl=60 * 30)  # cachea 30 minutos
def get_news(feed_url: str, max_items: int = 8) -> List[Dict]:
    if feedparser is None:
        raise ImportError("Falta instalar feedparser. Corré: pip install feedparser")

    parsed = feedparser.parse(feed_url)
    items = []
    for entry in parsed.entries[:max_items]:
        items.append(
            {
                "titulo": entry.get("title", "(sin título)"),
                "resumen": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "fecha": entry.get("published", ""),
                "fuente": parsed.feed.get("title", ""),
                "imagen": _extract_image_url(entry),
            }
        )
    return items


def get_general_news(max_items_per_feed: int = 5) -> List[Dict]:
    todas = []
    for _, url in GENERAL_FEEDS.items():
        try:
            todas.extend(get_news(url, max_items_per_feed))
        except Exception:
            continue
    return todas


def get_news_for_tickers(tickers: List[str], max_items_per_ticker: int = 4) -> List[Dict]:
    todas = []
    for t in tickers:
        try:
            todas.extend(get_news(_ticker_feed_url(t), max_items_per_ticker))
        except Exception:
            continue
    return todas


def _render_texto_noticia(n: Dict) -> None:
    st.markdown(f"#### [{n['titulo']}]({n['link']})")
    meta = " · ".join(filter(None, [n.get("fuente"), n.get("fecha")]))
    if meta:
        st.caption(meta)
    if n.get("resumen"):
        st.write(n["resumen"])


def render_news_list(lista: List[Dict], max_items: Optional[int] = None) -> None:
    """Renderiza una lista de noticias en Streamlit: imagen (si la trae
    el feed) a la izquierda, título/resumen/link a la derecha. Se usa
    desde Home y desde la sección Noticias para no duplicar el layout."""
    if st is None:
        return
    if max_items:
        lista = lista[:max_items]
    if not lista:
        st.info("No se encontraron noticias en este momento.")
        return
    for n in lista:
        if n.get("imagen"):
            col_img, col_texto = st.columns([1, 4])
            with col_img:
                st.image(n["imagen"], use_container_width=True)
            with col_texto:
                _render_texto_noticia(n)
        else:
            _render_texto_noticia(n)
        st.divider()
