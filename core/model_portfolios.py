"""
Carteras modelo preestablecidas por perfil de riesgo.

Son un punto de partida para alguien que recién empieza y no sabe en
qué poner su dinero: una distribución por CLASE de activo (no tickers
puntuales), para que cada persona la implemente después con los
instrumentos concretos que tenga a mano (ver ejemplos ilustrativos en
ASSET_CLASS_EXAMPLES). El perfil que le corresponde a cada persona se
calcula en core/risk_profile.py a partir de un cuestionario corto.
"""
from dataclasses import dataclass
from typing import Dict

# Color fijo por clase de activo. Es un mapeo aparte de CATEGORY_COLORS
# (classification.py), que clasifica tickers puntuales por rubro/industria
# — acá clasificamos por clase de activo a nivel de cartera modelo.
ASSET_CLASS_COLORS: Dict[str, str] = {
    "Acciones / ETFs": "#2f80ed",
    "Bonos": "#27ae60",
    "Efectivo / Plazo fijo": "#828282",
    "Cripto": "#ff9f1c",
}

# Ejemplos ilustrativos por clase de activo. No son una recomendación de
# instrumentos puntuales, son solo para que alguien nuevo entienda a qué
# se parece cada clase.
ASSET_CLASS_EXAMPLES: Dict[str, str] = {
    "Acciones / ETFs": "ej: un ETF del S&P 500, o algunas de las empresas de la sección Mercado",
    "Bonos": "ej: bonos soberanos o corporativos de bajo riesgo",
    "Efectivo / Plazo fijo": "ej: plazo fijo, cuenta remunerada, fondo money market",
    "Cripto": "ej: Bitcoin, Ethereum — la porción más volátil de la cartera",
}


@dataclass
class ModelPortfolio:
    key: str
    nombre: str
    resumen: str
    horizonte_sugerido: str
    allocation: Dict[str, float]  # clase de activo -> % (suma 100)


MODEL_PORTFOLIOS: Dict[str, ModelPortfolio] = {
    "conservador": ModelPortfolio(
        key="conservador",
        nombre="Conservador",
        resumen=(
            "Prioriza cuidar el capital por sobre hacerlo crecer rápido. "
            "Menos sobresaltos en el camino, pero también menos rendimiento "
            "esperado en el largo plazo."
        ),
        horizonte_sugerido="Corto a mediano plazo (podés llegar a necesitar la plata pronto)",
        allocation={
            "Efectivo / Plazo fijo": 50,
            "Bonos": 35,
            "Acciones / ETFs": 15,
            "Cripto": 0,
        },
    ),
    "moderado": ModelPortfolio(
        key="moderado",
        nombre="Moderado",
        resumen=(
            "Un balance entre crecimiento y estabilidad: acepta algo de "
            "volatilidad a cambio de mejores rendimientos esperados en el "
            "mediano/largo plazo."
        ),
        horizonte_sugerido="Mediano a largo plazo (3 a 7+ años)",
        allocation={
            "Efectivo / Plazo fijo": 20,
            "Bonos": 30,
            "Acciones / ETFs": 45,
            "Cripto": 5,
        },
    ),
    "agresivo": ModelPortfolio(
        key="agresivo",
        nombre="Agresivo",
        resumen=(
            "Prioriza el crecimiento del capital y tolera caídas fuertes en "
            "el camino. Pensada para quien no va a necesitar esta plata en "
            "mucho tiempo."
        ),
        horizonte_sugerido="Largo plazo (7+ años)",
        allocation={
            "Efectivo / Plazo fijo": 5,
            "Bonos": 10,
            "Acciones / ETFs": 70,
            "Cripto": 15,
        },
    ),
}


def get_portfolio(key: str) -> ModelPortfolio:
    return MODEL_PORTFOLIOS[key]
