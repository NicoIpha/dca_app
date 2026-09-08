"""
Perfil de ahorro del usuario: cuánto le destina a ahorrar por mes.
Se usa para armar el panorama inicial en Home (comparar solo ahorrar vs.
invertir a tasa fija vs. S&P 500 histórico). Persiste en un JSON local
para no tener que preguntarlo cada vez que se abre la app.
"""
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict

PROFILE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "user_profile.json")

# rango -> (texto para mostrar, monto representativo por defecto)
BRACKETS: Dict[str, Dict[str, object]] = {
    "menos_50": {"label": "Menos de \\$50 por mes", "default_amount": 30},
    "50_200": {"label": "Entre \\$50 y \\$200 por mes", "default_amount": 125},
    "mas_200": {"label": "Más de \\$200 por mes", "default_amount": 300},
}


@dataclass
class UserProfile:
    bracket: str
    monto_mensual: float


def load_profile() -> Optional[UserProfile]:
    if not os.path.exists(PROFILE_FILE):
        return None
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return UserProfile(**raw)
    except Exception:
        return None


def save_profile(profile: UserProfile) -> None:
    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(profile), f, indent=2, ensure_ascii=False)
