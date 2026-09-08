"""
Objetivos de ahorro concretos, para la sección "🎯 Tu objetivo" del Home
(la tapa de la app). En vez de arrancar con un gráfico comparativo
abstracto a 10 años, mostramos algo tangible: cuántos años tardaría
cada estrategia (guardar la plata, plazo fijo, S&P 500) en juntar una
cifra real — el precio de un depto, un auto, etc. — dado lo que la
persona ahorra por mes.

Reutiliza el motor de core/simulation.py (simulate_dca_monthly_rate);
no duplica lógica financiera acá.
"""
from typing import Dict, List, Optional

from core.simulation import simulate_dca_monthly_rate

# Tope del horizonte de cálculo: si ni siquiera en 30 años se llega al
# objetivo (típicamente "guardar la plata" con un objetivo grande), no
# tiene sentido seguir calculando década tras década.
MAX_YEARS_HORIZONTE = 30
MAX_MONTHS_HORIZONTE = MAX_YEARS_HORIZONTE * 12

# Objetivos preestablecidos. `monto_fijo` es un valor de referencia fijo
# en USD; los que no tienen monto fijo (como el fondo de emergencia) se
# calculan como un múltiplo de lo que la persona ahorra por mes.
GOAL_PRESETS: List[Dict[str, object]] = [
    {
        "key": "depto",
        "label": "Un departamento",
        "monto_fijo": 100_000,
        "help": "Precio aproximado de un depto chico en muchas ciudades — ajustalo mentalmente según la tuya.",
    },
    {
        "key": "auto",
        "label": "Un auto",
        "monto_fijo": 20_000,
        "help": "Precio aproximado de un auto usado en buen estado.",
    },
    {
        "key": "emergencia",
        "label": "Fondo de emergencia",
        "monto_fijo": None,
        "multiplo_ahorro_mensual": 6,
        "help": "Una reserva para imprevistos: 6 veces lo que ahorrás por mes. Es una referencia simple, no un cálculo de tus gastos reales.",
    },
    {
        "key": "personalizado",
        "label": "Otro monto",
        "monto_fijo": None,
        "help": "Elegí vos la cifra que querés alcanzar.",
    },
]

GOAL_PRESETS_BY_KEY = {p["key"]: p for p in GOAL_PRESETS}


def resolve_goal_amount(
    preset_key: str, monto_mensual: float, monto_personalizado: Optional[float] = None
) -> float:
    """Calcula el monto objetivo en USD para el preset elegido."""
    preset = GOAL_PRESETS_BY_KEY.get(preset_key)
    if preset is None:
        return 0.0

    if preset_key == "personalizado":
        return float(monto_personalizado or 0)

    if preset.get("monto_fijo") is not None:
        return float(preset["monto_fijo"])

    multiplo = preset.get("multiplo_ahorro_mensual")
    if multiplo:
        return float(monto_mensual) * float(multiplo)

    return 0.0


def months_to_reach_goal(
    monthly_amount: float,
    goal_amount: float,
    monthly_rate: float,
    max_months: int = MAX_MONTHS_HORIZONTE,
) -> Optional[int]:
    """
    Cuántos meses hacen falta, ahorrando `monthly_amount` por mes a una
    tasa mensual constante `monthly_rate`, para que el valor acumulado
    alcance `goal_amount`. Devuelve None si no se alcanza dentro de
    `max_months` (evita simular décadas para una tasa muy baja o nula).
    """
    if monthly_amount <= 0 or goal_amount <= 0:
        return None

    resultado = simulate_dca_monthly_rate(monthly_amount, max_months, monthly_rate)
    for month, value in zip(resultado.months, resultado.portfolio_value):
        if value >= goal_amount:
            return month
    return None


def display_horizon_months(
    meses_por_estrategia: Dict[str, Optional[int]],
    min_months: int = 12,
    max_months: int = MAX_MONTHS_HORIZONTE,
) -> int:
    """
    Cuántos meses mostrar en el eje X del gráfico de una meta: lo
    suficiente para que se note dónde cruza la meta la estrategia más
    lenta de las que sí la alcanzan, con un margen. Si ninguna la
    alcanza dentro del tope, se muestra el horizonte completo (para que
    se vea que las curvas se quedan cortas).
    """
    alcanzados = [m for m in meses_por_estrategia.values() if m is not None]
    if not alcanzados:
        return max_months

    peor = max(alcanzados)
    con_margen = peor + max(6, round(peor * 0.15))
    return max(min_months, min(con_margen, max_months))


def build_progress_series(
    monthly_amount: float,
    horizon_months: int,
    monthly_rate_por_estrategia: Dict[str, Optional[float]],
) -> Dict[str, Optional[List[float]]]:
    """
    Para cada estrategia con una tasa mensual disponible (None = sin
    datos, ej. plazo fijo sin conexión al BCRA), simula la evolución de
    la cartera mes a mes durante `horizon_months`. Pensado para
    alimentar core.charts.build_goal_progress_figure.
    """
    series: Dict[str, Optional[List[float]]] = {}
    for key, tasa in monthly_rate_por_estrategia.items():
        if tasa is None or monthly_amount <= 0:
            series[key] = None
            continue
        resultado = simulate_dca_monthly_rate(monthly_amount, horizon_months, tasa)
        series[key] = resultado.portfolio_value
    return series


def format_years_months(months: Optional[int]) -> str:
    """Convierte una cantidad de meses en un texto tipo '3 años y 4 meses'."""
    if months is None:
        return f"más de {MAX_YEARS_HORIZONTE} años"

    years, rem_months = divmod(months, 12)
    partes = []
    if years:
        partes.append(f"{years} año" + ("s" if years != 1 else ""))
    if rem_months:
        partes.append(f"{rem_months} mes" + ("es" if rem_months != 1 else ""))
    if not partes:
        return "menos de 1 mes"
    return " y ".join(partes)
