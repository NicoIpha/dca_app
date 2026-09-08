"""
Manejo de la cartera real del usuario (posiciones actuales).
Se persiste en un archivo JSON local (data/portfolio.json) para que
no se pierda entre sesiones de la app.
"""
import json
import os
from dataclasses import dataclass, asdict, field
from typing import List, Optional

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "portfolio.json")


@dataclass
class Holding:
    ticker: str
    shares: float
    avg_price: float  # precio promedio de compra
    note: Optional[str] = ""


def load_portfolio() -> List[Holding]:
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Holding(**h) for h in raw]


def save_portfolio(holdings: List[Holding]) -> None:
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump([asdict(h) for h in holdings], f, indent=2, ensure_ascii=False)


def add_holding(
    holdings: List[Holding], ticker: str, shares: float, avg_price: float, note: str = ""
) -> List[Holding]:
    """Agrega una posición nueva, o la combina (precio promedio ponderado)
    si el ticker ya existe en la cartera."""
    ticker = ticker.upper().strip()
    for h in holdings:
        if h.ticker == ticker:
            total_shares = h.shares + shares
            if total_shares > 0:
                h.avg_price = (h.avg_price * h.shares + avg_price * shares) / total_shares
            h.shares = total_shares
            return holdings
    holdings.append(Holding(ticker=ticker, shares=shares, avg_price=avg_price, note=note))
    return holdings


def remove_holding(holdings: List[Holding], ticker: str) -> List[Holding]:
    ticker = ticker.upper().strip()
    return [h for h in holdings if h.ticker != ticker]
