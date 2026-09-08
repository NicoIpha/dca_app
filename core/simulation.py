"""
Núcleo de simulación de inversiones periódicas (DCA - Dollar Cost Averaging).
Sin dependencias externas pesadas: solo lógica pura, testeable.
"""
from dataclasses import dataclass, field
from typing import List, Optional
import math


@dataclass
class SimulationResult:
    months: List[int] = field(default_factory=list)
    invested: List[float] = field(default_factory=list)      # capital aportado acumulado
    portfolio_value: List[float] = field(default_factory=list)  # valor de la cartera
    shares: List[float] = field(default_factory=list)         # cantidad de acciones acumuladas

    @property
    def total_invested(self) -> float:
        return self.invested[-1] if self.invested else 0.0

    @property
    def final_value(self) -> float:
        return self.portfolio_value[-1] if self.portfolio_value else 0.0

    @property
    def total_return_pct(self) -> float:
        if not self.invested or self.invested[-1] == 0:
            return 0.0
        return (self.final_value - self.total_invested) / self.total_invested * 100

    @property
    def gain(self) -> float:
        return self.final_value - self.total_invested


def simulate_dca_monthly_rate(
    monthly_amount: float,
    months: int,
    monthly_rate: float,
) -> SimulationResult:
    """
    Motor de simulación DCA: invierte `monthly_amount` cada mes durante
    `months` meses, capitalizando cada mes a `monthly_rate` (tasa mensual
    ya calculada, como fracción, ej: 0.01625 para 1.625%).
    """
    result = SimulationResult()
    portfolio_value = 0.0
    invested_acc = 0.0

    for m in range(1, months + 1):
        # se invierte al principio del mes, y luego capitaliza
        portfolio_value += monthly_amount
        invested_acc += monthly_amount
        portfolio_value *= (1 + monthly_rate)

        result.months.append(m)
        result.invested.append(invested_acc)
        result.portfolio_value.append(portfolio_value)
        result.shares.append(float('nan'))  # no aplica en este modo

    return result


def annual_effective_to_monthly_rate(annual_return_pct: float) -> float:
    """
    Convierte una tasa anual EFECTIVA/compuesta (ej. el CAGR histórico de
    un ticker) a su equivalente mensual, vía raíz doceava. NO usar esto
    para una tasa NOMINAL anual (TNA, como la de plazo fijo) — ver el
    comentario de simulate_dca_fixed_rate.
    """
    return (1 + annual_return_pct / 100) ** (1 / 12) - 1


def simulate_dca_fixed_rate(
    monthly_amount: float,
    months: int,
    annual_return_pct: float,
) -> SimulationResult:
    """
    Proyección simple: asume una tasa de retorno anual EFECTIVA constante
    (compuesta), invirtiendo `monthly_amount` cada mes durante `months`
    meses. Para una tasa NOMINAL anual (TNA, como la de plazo fijo) no
    usar esta función: la conversión correcta es dividir por 12
    (ver simulate_dca_monthly_rate con annual_return_pct/100/12).
    """
    monthly_rate = annual_effective_to_monthly_rate(annual_return_pct)
    return simulate_dca_monthly_rate(monthly_amount, months, monthly_rate)


def simulate_dca_from_prices(
    monthly_amount: float,
    monthly_prices: List[float],
) -> SimulationResult:
    """
    Backtest histórico: dado un listado de precios de cierre mensuales
    (uno por mes, en orden cronológico), simula comprar `monthly_amount`
    en dólares de ese activo cada mes.
    """
    result = SimulationResult()
    shares_acc = 0.0
    invested_acc = 0.0

    for i, price in enumerate(monthly_prices, start=1):
        if price <= 0:
            continue
        shares_bought = monthly_amount / price
        shares_acc += shares_bought
        invested_acc += monthly_amount
        portfolio_value = shares_acc * price

        result.months.append(i)
        result.invested.append(invested_acc)
        result.portfolio_value.append(portfolio_value)
        result.shares.append(shares_acc)

    return result


def summarize_horizons(
    monthly_amount: float,
    horizons_years: List[int],
    annual_return_pct: float,
) -> dict:
    """Corre la proyección simple para varios horizontes (1, 2, 5, 10 años, etc.)."""
    summary = {}
    for years in horizons_years:
        res = simulate_dca_fixed_rate(monthly_amount, years * 12, annual_return_pct)
        summary[years] = {
            "invertido": round(res.total_invested, 2),
            "valor_final": round(res.final_value, 2),
            "ganancia": round(res.gain, 2),
            "retorno_%": round(res.total_return_pct, 2),
        }
    return summary
