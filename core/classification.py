"""
Clasificación de tickers por rubro/categoría, para colorear el gráfico
de torta de Perfil de forma consistente (mismo color = mismo rubro,
siempre). Soporta acciones (sector real de Yahoo Finance), cripto,
índices y CEDEARs.
"""
from typing import Optional

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    def cache_data(*args, **kwargs):
        def wrapper(fn):
            return fn
        return wrapper

# Sector tal como lo devuelve Yahoo Finance -> nombre en español
# (mismas categorías que se usan en la sección Mercado).
YAHOO_SECTOR_TO_LABEL = {
    "Technology": "Tecnología",
    "Energy": "Energía",
    "Healthcare": "Salud",
    "Financial Services": "Financiero",
    "Consumer Cyclical": "Consumo discrecional",
    "Consumer Defensive": "Consumo básico",
    "Industrials": "Industrial",
    "Communication Services": "Comunicaciones",
    "Basic Materials": "Materiales",
    "Real Estate": "Inmobiliario",
    "Utilities": "Utilities",
}

# Color fijo por categoría (se puede retocar la paleta libremente acá).
CATEGORY_COLORS = {
    "Tecnología": "#2f80ed",             # azul
    "Energía": "#f2c94c",                # amarillo
    "Salud": "#27ae60",                  # verde
    "Financiero": "#9b51e0",             # violeta
    "Consumo discrecional": "#f2994a",   # naranja
    "Consumo básico": "#56ccf2",         # celeste
    "Industrial": "#828282",             # gris
    "Comunicaciones": "#eb5757",         # rojo
    "Materiales": "#a0522d",             # marrón
    "Inmobiliario": "#219653",           # verde oscuro
    "Utilities": "#6fcf97",              # verde agua
    "Cripto": "#ff9f1c",                 # dorado
    "Índices": "#4f4f4f",                # gris oscuro
    "CEDEAR": "#bb6bd9",                 # lila
    "Otro": "#bdbdbd",                   # gris claro
}


@cache_data(ttl=60 * 60 * 24)
def get_category(ticker: str) -> str:
    """Devuelve la categoría/rubro de un ticker. Cripto e índices se
    detectan por el formato del símbolo; para acciones se consulta el
    sector real en Yahoo Finance."""
    t = ticker.upper().strip()

    if t.startswith("^"):
        return "Índices"
    if t.endswith("-USD") or t.endswith("-USDT"):
        return "Cripto"
    if t.endswith(".BA"):
        return "CEDEAR"

    if yf is None:
        return "Otro"

    try:
        info = yf.Ticker(t).info
        sector = info.get("sector")
        if not sector:
            return "Otro"
        return YAHOO_SECTOR_TO_LABEL.get(sector, sector)
    except Exception:
        return "Otro"


def get_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS["Otro"])
