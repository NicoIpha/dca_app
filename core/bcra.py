"""
Datos financieros de Argentina (tasa de plazo fijo y cotización del
dólar), vía la API pública y gratuita ArgentinaDatos
(https://argentinadatos.com), que reprocesa datos oficiales del BCRA
en un formato mucho más simple y estable que la API cruda del BCRA
(que cambió de versión y de esquema varias veces).

Importante: la tasa de plazo fijo está expresada en PESOS ARGENTINOS
(ARS), no en dólares. Para poder compararla con escenarios en USD hay
que convertirla usando la cotización del dólar y una devaluación
esperada del peso (ver get_devaluacion_anual_historica).
"""
import datetime as dt
from typing import Dict

try:
    import requests
except ImportError:
    requests = None

try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    def cache_data(*args, **kwargs):
        def wrapper(fn):
            return fn
        return wrapper

BASE_URL = "https://api.argentinadatos.com/v1"


def _get(url: str, **kwargs):
    """GET con reintento sin verificación SSL, por si algún entorno
    (típicamente Windows corporativo) tiene problemas de certificado."""
    try:
        return requests.get(url, timeout=10, **kwargs)
    except requests.exceptions.SSLError:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return requests.get(url, timeout=10, verify=False, **kwargs)


@cache_data(ttl=60 * 60 * 12)  # 12hs: esta tasa no cambia varias veces por día
def get_tasa_plazo_fijo() -> Dict[str, object]:
    """Devuelve {'tasa': float (% TNA), 'fecha': 'YYYY-MM-DD', 'descripcion': str}
    con el último valor de la tasa de interés de depósitos a 30 días
    (fuente original: BCRA, vía ArgentinaDatos)."""
    if requests is None:
        raise ImportError("Falta instalar requests. Corré: pip install requests")

    resp = _get(f"{BASE_URL}/finanzas/tasas/depositos30Dias")
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise ValueError("La API de ArgentinaDatos no devolvió datos de tasa de depósitos a 30 días.")

    data_ordenada = sorted(data, key=lambda x: x.get("fecha", ""))
    ultimo = data_ordenada[-1]
    valor = float(ultimo["valor"])

    # sanity check: una TNA de plazo fijo, por más alta que sea la inflación,
    # no debería superar unos pocos cientos de %.
    if not (0 < valor <= 500):
        raise ValueError(f"El valor recibido ({valor}%) está fuera de un rango razonable para una tasa de interés.")

    return {
        "tasa": valor,
        "fecha": ultimo.get("fecha", ""),
        "descripcion": "Tasa de interés de depósitos a 30 días de plazo (fuente: BCRA, vía ArgentinaDatos)",
    }


@cache_data(ttl=60 * 60 * 12)
def get_dolar_actual() -> Dict[str, object]:
    """Devuelve {'cotizacion': float (ARS por USD), 'fecha': str} con la
    última cotización del dólar oficial (venta)."""
    if requests is None:
        raise ImportError("Falta instalar requests. Corré: pip install requests")

    resp = _get(f"{BASE_URL}/cotizaciones/dolares/oficial")
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise ValueError("La API de ArgentinaDatos no devolvió cotizaciones del dólar oficial.")

    data_ordenada = sorted(data, key=lambda x: x.get("fecha", ""))
    ultimo = data_ordenada[-1]

    return {"cotizacion": float(ultimo["venta"]), "fecha": ultimo.get("fecha", "")}


@cache_data(ttl=60 * 60 * 12)
def get_devaluacion_anual_historica(years: int = 5) -> float:
    """CAGR histórico (%) del dólar oficial en los últimos `years` años.
    Sirve como punto de partida razonable para estimar la devaluación
    futura del peso, pero NO es una garantía ni una predicción: el
    futuro puede ser muy distinto al pasado."""
    if requests is None:
        raise ImportError("Falta instalar requests. Corré: pip install requests")

    resp = _get(f"{BASE_URL}/cotizaciones/dolares/oficial")
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise ValueError("La API de ArgentinaDatos no devolvió cotizaciones históricas del dólar.")

    data_ordenada = sorted(data, key=lambda x: x.get("fecha", ""))

    hoy = dt.date.today()
    fecha_objetivo = hoy.replace(year=hoy.year - years).isoformat()

    candidatos_pasado = [d for d in data_ordenada if d.get("fecha", "") <= fecha_objetivo]
    inicial = candidatos_pasado[-1] if candidatos_pasado else data_ordenada[0]
    final = data_ordenada[-1]

    valor_inicial = float(inicial["venta"])
    valor_final = float(final["venta"])

    if valor_inicial <= 0:
        raise ValueError("Cotización histórica inválida (valor inicial <= 0).")

    fecha_i = dt.date.fromisoformat(inicial["fecha"][:10])
    fecha_f = dt.date.fromisoformat(final["fecha"][:10])
    anios_reales = (fecha_f - fecha_i).days / 365.25

    if anios_reales <= 0:
        raise ValueError("No hay suficiente rango histórico para calcular la devaluación.")

    return ((valor_final / valor_inicial) ** (1 / anios_reales) - 1) * 100
