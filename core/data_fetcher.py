"""
Obtención de precios históricos reales via yfinance.
Este módulo requiere conexión a internet (Yahoo Finance) y se ejecuta
en tu máquina local, no en el entorno de desarrollo.

Los resultados se cachean (mismo patrón que bcra.py / market.py /
news.py) porque Streamlit vuelve a correr el script de la página
completo en cada interacción, no solo al navegar entre páginas: sin
caché, cada click en Home o en Perfil dispararía una descarga nueva a
Yahoo Finance. Cacheado, la primera carga paga el costo de red y las
siguientes (moverse a otra página y volver, tocar otro control) salen
de memoria al toque.
"""
from typing import List, Tuple
import datetime as dt

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    yf = None
    pd = None

try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    # permite testear este módulo sin streamlit instalado
    def cache_data(*args, **kwargs):
        def wrapper(fn):
            return fn
        return wrapper


@cache_data(ttl=60 * 60 * 6)  # 6hs: precios de cierre mensuales no cambian más rápido que eso
def get_monthly_closes(ticker: str, years_back: int) -> Tuple[List[str], List[float]]:
    """
    Descarga precios de cierre mensuales (ajustados) de un ticker
    para los últimos `years_back` años.
    Devuelve (fechas_str, precios).
    """
    if yf is None:
        raise ImportError(
            "Falta instalar yfinance. Corré: pip install yfinance pandas"
        )

    end = dt.date.today()
    start = end.replace(year=end.year - years_back)

    data = yf.download(ticker, start=start, end=end, interval="1mo", progress=False, auto_adjust=True)

    if data.empty:
        raise ValueError(f"No se encontraron datos para el ticker '{ticker}'.")

    closes = data["Close"].dropna()
    fechas = [d.strftime("%Y-%m") for d in closes.index]
    precios = [float(p) for p in closes.values.flatten()]

    return fechas, precios


@cache_data(ttl=60 * 15)  # 15min: es un precio "actual", pero no hace falta pedirlo en cada rerun
def get_current_price(ticker: str) -> float:
    """Devuelve el último precio de cierre disponible para un ticker."""
    if yf is None:
        raise ImportError(
            "Falta instalar yfinance. Corré: pip install yfinance pandas"
        )
    data = yf.Ticker(ticker).history(period="5d")
    if data.empty:
        raise ValueError(f"No se pudo obtener precio actual para '{ticker}'.")
    return float(data["Close"].iloc[-1])


@cache_data(ttl=60 * 60 * 6)
def get_annualized_historical_return(ticker: str, years_back: int) -> float:
    """
    Calcula el retorno anualizado (CAGR) histórico de un ticker,
    útil como referencia para setear una tasa de proyección "realista".
    """
    fechas, precios = get_monthly_closes(ticker, years_back)
    if len(precios) < 2:
        raise ValueError("No hay suficientes datos históricos.")

    total_return = precios[-1] / precios[0]
    years = len(precios) / 12
    cagr = (total_return ** (1 / years) - 1) * 100
    return cagr
