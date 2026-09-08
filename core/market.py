"""
Datos de mercado: trae el listado de empresas top por rubro directamente
desde Yahoo Finance (vía yfinance.Sector) y calcula retornos reales para
distintos horizontes de tiempo.

El listado de tickers se cachea 24hs (la composición de un rubro no
cambia de un día para el otro), así la app no se pone lenta ni golpea
la API de más.
"""
from typing import Dict, List
import datetime as dt

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    # permite testear este módulo sin streamlit instalado
    def cache_data(*args, **kwargs):
        def wrapper(fn):
            return fn
        return wrapper

# Nombre para mostrar -> clave de sector que usa yfinance/Yahoo Finance
SECTOR_KEYS: Dict[str, str] = {
    "Tecnología": "technology",
    "Salud": "healthcare",
    "Financiero": "financial-services",
    "Energía": "energy",
    "Consumo discrecional": "consumer-cyclical",
    "Consumo básico": "consumer-defensive",
    "Industrial": "industrials",
    "Comunicaciones": "communication-services",
    "Materiales": "basic-materials",
    "Inmobiliario": "real-estate",
    "Utilities": "utilities",
}

# Respaldo chico por si falla la consulta a Yahoo Finance
# (sin internet, o versión de yfinance vieja que no tiene Sector).
FALLBACK_TICKERS: Dict[str, List[str]] = {
    "Tecnología": ["AAPL", "MSFT", "NVDA", "GOOGL", "META"],
    "Salud": ["JNJ", "UNH", "PFE", "LLY", "ABBV"],
    "Financiero": ["JPM", "BAC", "WFC", "GS", "MS"],
    "Energía": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Consumo discrecional": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Consumo básico": ["PG", "KO", "PEP", "WMT", "COST"],
    "Industrial": ["CAT", "BA", "HON", "UPS", "GE"],
    "Comunicaciones": ["GOOG", "NFLX", "DIS", "CMCSA", "T"],
    "Materiales": ["LIN", "SHW", "APD", "ECL", "FCX"],
    "Inmobiliario": ["PLD", "AMT", "EQIX", "PSA", "O"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP"],
}

PERIODS_YEARS = [1, 3, 5]


@cache_data(ttl=60 * 60 * 24)  # 24hs
def get_sector_tickers(sector_display_name: str, limit: int = 20) -> List[str]:
    """Trae el listado real de empresas top de un rubro desde Yahoo Finance.
    Si falla (sin internet, yfinance desactualizado, etc.), usa un
    respaldo chico hardcodeado para que la app no se rompa."""
    sector_key = SECTOR_KEYS.get(sector_display_name)
    if yf is None or sector_key is None:
        return FALLBACK_TICKERS.get(sector_display_name, [])

    try:
        sector = yf.Sector(sector_key)
        df = sector.top_companies  # DataFrame indexado por ticker
        if df is None or df.empty:
            raise ValueError("Yahoo Finance no devolvió empresas para este rubro.")
        return list(df.index[:limit])
    except Exception:
        # Puede fallar por versión vieja de yfinance (Sector es relativamente
        # nuevo) o por problemas de red. Usamos el respaldo.
        return FALLBACK_TICKERS.get(sector_display_name, [])


@cache_data(ttl=60 * 60 * 6)  # 6hs
def get_return_pct(ticker: str, years: int) -> float:
    """Retorno total (%) de un ticker en los últimos `years` años."""
    if yf is None:
        raise ImportError("Falta instalar yfinance. Corré: pip install yfinance")

    end = dt.date.today()
    start = end.replace(year=end.year - years)
    hist = yf.download(ticker, start=start, end=end, interval="1d", progress=False, auto_adjust=True)
    if hist.empty or len(hist) < 2:
        raise ValueError(f"No hay datos suficientes para {ticker}")
    price_start = float(hist["Close"].iloc[0])
    price_end = float(hist["Close"].iloc[-1])
    return (price_end / price_start - 1) * 100


@cache_data(ttl=60 * 60 * 6)
def top_n_by_sector(sector_display_name: str, years: int, n: int = 10) -> List[dict]:
    """Top N empresas de un rubro (según el listado real de Yahoo Finance),
    ordenadas por retorno descendente en el horizonte pedido."""
    tickers = get_sector_tickers(sector_display_name)
    resultados = []
    for t in tickers:
        try:
            r = get_return_pct(t, years)
            resultados.append({"ticker": t, "retorno_%": round(r, 2)})
        except Exception:
            continue
    resultados.sort(key=lambda x: x["retorno_%"], reverse=True)
    return resultados[:n]


def search_ticker_returns(ticker: str) -> dict:
    """Retorno de un ticker arbitrario (no necesariamente en el universo
    de un rubro) para 1, 3 y 5 años."""
    ticker = ticker.upper().strip()
    out = {"ticker": ticker}
    for years in PERIODS_YEARS:
        try:
            out[f"{years}a_%"] = round(get_return_pct(ticker, years), 2)
        except Exception:
            out[f"{years}a_%"] = None
    return out
