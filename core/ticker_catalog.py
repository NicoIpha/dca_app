"""
Catálogo de tickers populares para facilitar la carga de una posición
nueva en Perfil. No es una lista exhaustiva del mercado (para eso está
el buscador de Mercado y la opción "Otro" del formulario): son ~50
acciones de las más conocidas/operadas, para que aparezcan sugerencias
apenas empezás a escribir el ticker o el nombre de la empresa.

Además de esta lista curada, `remember_ticker()` persiste en
data/known_tickers.json cualquier ticker que la persona haya buscado
por fuera de la lista (en Perfil con "Otro", o en el buscador de
Mercado) y confirmado que existe agregándolo a su cartera real. Así,
la próxima vez que abra el selector de Perfil, ese ticker ya aparece
sin tener que volver a escribirlo a mano.
"""
import json
import os
from typing import List, Tuple

KNOWN_TICKERS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "known_tickers.json")

# (ticker, nombre de la empresa)
POPULAR_TICKERS: List[Tuple[str, str]] = [
    ("AAPL", "Apple"),
    ("MSFT", "Microsoft"),
    ("NVDA", "NVIDIA"),
    ("AMZN", "Amazon"),
    ("GOOGL", "Alphabet (Google) Clase A"),
    ("GOOG", "Alphabet (Google) Clase C"),
    ("META", "Meta Platforms"),
    ("TSLA", "Tesla"),
    ("BRK-B", "Berkshire Hathaway"),
    ("LLY", "Eli Lilly"),
    ("AVGO", "Broadcom"),
    ("JPM", "JPMorgan Chase"),
    ("V", "Visa"),
    ("UNH", "UnitedHealth"),
    ("XOM", "Exxon Mobil"),
    ("WMT", "Walmart"),
    ("MA", "Mastercard"),
    ("PG", "Procter & Gamble"),
    ("JNJ", "Johnson & Johnson"),
    ("HD", "Home Depot"),
    ("MRK", "Merck"),
    ("COST", "Costco"),
    ("ABBV", "AbbVie"),
    ("CVX", "Chevron"),
    ("PEP", "PepsiCo"),
    ("KO", "Coca-Cola"),
    ("ADBE", "Adobe"),
    ("CRM", "Salesforce"),
    ("BAC", "Bank of America"),
    ("NFLX", "Netflix"),
    ("AMD", "Advanced Micro Devices"),
    ("TMO", "Thermo Fisher Scientific"),
    ("PFE", "Pfizer"),
    ("DIS", "Walt Disney"),
    ("CSCO", "Cisco"),
    ("ABT", "Abbott Laboratories"),
    ("ORCL", "Oracle"),
    ("ACN", "Accenture"),
    ("MCD", "McDonald's"),
    ("LIN", "Linde"),
    ("WFC", "Wells Fargo"),
    ("TXN", "Texas Instruments"),
    ("DHR", "Danaher"),
    ("NKE", "Nike"),
    ("PM", "Philip Morris International"),
    ("INTC", "Intel"),
    ("COP", "ConocoPhillips"),
    ("IBM", "IBM"),
    ("QCOM", "Qualcomm"),
    ("UPS", "United Parcel Service"),
]


def _load_known_tickers() -> List[Tuple[str, str]]:
    """Tickers que la persona buscó y confirmó (no están en la lista
    curada de arriba), persistidos en data/known_tickers.json."""
    if not os.path.exists(KNOWN_TICKERS_FILE):
        return []
    try:
        with open(KNOWN_TICKERS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [(item["ticker"], item.get("nombre", "")) for item in raw]
    except Exception:
        return []


def remember_ticker(ticker: str, nombre: str = "") -> None:
    """Guarda un ticker encontrado por búsqueda (en Perfil con "Otro", o
    en el buscador de Mercado) para que aparezca en el autocompletado de
    ahí en adelante. No hace nada si ya está en la lista curada o ya
    estaba guardado — se puede llamar sin culpa cada vez que se agrega
    una posición nueva, sea el ticker conocido o no."""
    ticker = ticker.upper().strip()
    if not ticker:
        return
    if ticker in {t for t, _ in POPULAR_TICKERS}:
        return

    conocidos = _load_known_tickers()
    if ticker in {t for t, _ in conocidos}:
        return

    conocidos.append((ticker, nombre))
    os.makedirs(os.path.dirname(KNOWN_TICKERS_FILE), exist_ok=True)
    with open(KNOWN_TICKERS_FILE, "w", encoding="utf-8") as f:
        json.dump([{"ticker": t, "nombre": n} for t, n in conocidos], f, indent=2, ensure_ascii=False)


def get_display_options() -> List[str]:
    """Devuelve strings para mostrar en el selector: la lista curada de
    ~50 populares, con su nombre, más los tickers que la persona fue
    encontrando por búsqueda y agregando a su cartera (sin nombre
    conocido, se muestran solo con el ticker). Streamlit filtra estas
    opciones a medida que el usuario escribe."""
    curados = [f"{t} - {n}" for t, n in POPULAR_TICKERS]
    aprendidos = [f"{t} - {n}" if n else t for t, n in _load_known_tickers()]
    return curados + aprendidos


def parse_ticker_from_display(display_value: str) -> str:
    """Extrae el ticker de un string con formato 'TICKER - Nombre'."""
    return display_value.split(" - ")[0].strip()
