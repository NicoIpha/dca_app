"""
Cuestionario de perfil de riesgo: unas pocas preguntas para estimar qué
tan cómoda está la persona con la volatilidad y el horizonte de su
inversión, y así sugerirle una de las 3 carteras modelo (ver
core/model_portfolios.py) como punto de partida.

Persiste el resultado en data/risk_profile.json para no tener que
repetir el cuestionario cada vez que se abre la app (igual criterio que
core/user_profile.py y core/portfolio.py).
"""
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

RISK_PROFILE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "risk_profile.json")

# Cada pregunta: texto + opciones, cada opción con su puntaje (1 = más
# conservador, 4 = más agresivo). El puntaje total (suma de las 5
# preguntas, entre 5 y 20) determina el perfil final.
QUESTIONS: List[Dict[str, object]] = [
    {
        "texto": "¿Cuál es tu horizonte de inversión (cuánto tiempo pensás dejar esta plata invertida sin tocarla)?",
        "opciones": [
            ("Menos de 1 año", 1),
            ("Entre 1 y 3 años", 2),
            ("Entre 3 y 7 años", 3),
            ("Más de 7 años", 4),
        ],
    },
    {
        "texto": "Si el valor de tu cartera cayera un 20% en un mes malo, ¿qué harías?",
        "opciones": [
            ("Vendo todo, no soporto ver pérdidas", 1),
            ("Vendo una parte para cubrirme", 2),
            ("No hago nada, espero a que se recupere", 3),
            ("Aprovecho para comprar más, está más barato", 4),
        ],
    },
    {
        "texto": "¿Para qué vas a usar esta plata?",
        "opciones": [
            ("La necesito para algo puntual pronto (viaje, casa, etc.)", 1),
            ("Es un fondo de emergencia / colchón", 2),
            ("Es ahorro de mediano plazo, sin un uso definido todavía", 3),
            ("Es ahorro de largo plazo (jubilación, patrimonio)", 4),
        ],
    },
    {
        "texto": "¿Cuánta experiencia tenés invirtiendo?",
        "opciones": [
            ("Ninguna, es la primera vez", 1),
            ("Un poco, alguna vez compré algo", 2),
            ("Bastante, sigo el mercado con cierta regularidad", 3),
            ("Mucha, invierto hace años y entiendo los riesgos", 4),
        ],
    },
    {
        "texto": "¿Qué porción de tus ahorros totales representa el dinero que vas a invertir?",
        "opciones": [
            ("Prácticamente todos mis ahorros", 1),
            ("Más de la mitad", 2),
            ("Una parte, tengo otros ahorros aparte", 3),
            ("Una porción chica, tengo bien cubierto el resto", 4),
        ],
    },
]

# (puntaje mínimo, puntaje máximo, perfil) — el puntaje total va de 5 a 20.
SCORE_RANGES: List[Tuple[int, int, str]] = [
    (5, 9, "conservador"),
    (10, 15, "moderado"),
    (16, 20, "agresivo"),
]


@dataclass
class RiskProfileResult:
    respuestas: List[int]  # puntaje elegido en cada pregunta, en orden
    score: int
    perfil: str


def score_to_profile(score: int) -> str:
    for lo, hi, perfil in SCORE_RANGES:
        if lo <= score <= hi:
            return perfil
    return "moderado"


def compute_result(respuestas: List[int]) -> RiskProfileResult:
    score = sum(respuestas)
    return RiskProfileResult(respuestas=respuestas, score=score, perfil=score_to_profile(score))


def load_result() -> Optional[RiskProfileResult]:
    if not os.path.exists(RISK_PROFILE_FILE):
        return None
    try:
        with open(RISK_PROFILE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return RiskProfileResult(**raw)
    except Exception:
        return None


def save_result(result: RiskProfileResult) -> None:
    os.makedirs(os.path.dirname(RISK_PROFILE_FILE), exist_ok=True)
    with open(RISK_PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)
