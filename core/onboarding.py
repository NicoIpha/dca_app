"""
Guía de "primeros pasos" para alguien que recién abre la app: qué hacer
primero (el test de inversor, decir cuánto ahorra por mes) y qué va a
encontrar en cada una de las otras secciones (Perfil, Mercado, Noticias).

El progreso se persiste en un JSON local (mismo patrón que
risk_profile.py / user_profile.py / portfolio.py) para no repetir la
guía una vez que la persona ya la vio, y para tildar solas las
secciones informativas (Mercado/Noticias) apenas las visita.
"""
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List

try:
    import streamlit as st
except ImportError:
    st = None

ONBOARDING_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "onboarding.json")


@dataclass
class OnboardingState:
    dismissed: bool = False
    visitado_mercado: bool = False
    visitado_noticias: bool = False


def load_state() -> OnboardingState:
    if not os.path.exists(ONBOARDING_FILE):
        return OnboardingState()
    try:
        with open(ONBOARDING_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return OnboardingState(**raw)
    except Exception:
        return OnboardingState()


def save_state(state: OnboardingState) -> None:
    os.makedirs(os.path.dirname(ONBOARDING_FILE), exist_ok=True)
    with open(ONBOARDING_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(state), f, indent=2, ensure_ascii=False)


def mark_visited(pagina: str) -> None:
    """Marca una sección informativa (ej: 'mercado', 'noticias') como ya
    vista, para que se tilde sola en la guía de primeros pasos la
    próxima vez que alguien entre a Home."""
    campo = f"visitado_{pagina}"
    state = load_state()
    if not getattr(state, campo, False):
        setattr(state, campo, True)
        save_state(state)


# Cada paso: ícono, título, detalle (qué es / para qué sirve esa
# sección), página a la que lleva (None si se resuelve en la misma
# Home) y una función que decide si ya está hecho, a partir del
# contexto que le pasa Home (ver render_primeros_pasos).
STEPS: List[Dict[str, object]] = [
    {
        "icon": "🧭",
        "titulo": "Hacé el test de inversor",
        "detalle": "5 preguntas cortas para saber tu perfil de riesgo y ver una cartera modelo sugerida (Conservador / Moderado / Agresivo).",
        "page": "pages/0_Perfil_de_Riesgo.py",
        "page_label": "Ir a Perfil de Riesgo",
        "hecho": lambda estado, ctx: bool(ctx.get("tiene_perfil_riesgo")),
    },
    {
        "icon": "💰",
        "titulo": "Contanos cuánto ahorrás por mes",
        "detalle": "Con ese número te mostramos, ahí abajo, en cuánto tiempo llegarías a distintas metas ahorrando o invirtiendo.",
        "page": None,
        "page_label": "👇 Lo hacés acá abajo",
        "hecho": lambda estado, ctx: bool(ctx.get("tiene_monto_mensual")),
    },
    {
        "icon": "📊",
        "titulo": "Cargá tu cartera real (si ya invertís)",
        "detalle": "En Perfil sumás tus posiciones y ves cómo está compuesta tu cartera hoy, por rubro.",
        "page": "pages/1_Perfil.py",
        "page_label": "Ir a Perfil",
        "hecho": lambda estado, ctx: bool(ctx.get("tiene_cartera")),
    },
    {
        "icon": "🏦",
        "titulo": "Mirá qué está rindiendo mejor en Mercado",
        "detalle": "Top 10 de acciones por rubro (1, 3 y 5 años), noticias de tus posiciones y un buscador para cualquier ticker puntual.",
        "page": "pages/2_Mercado.py",
        "page_label": "Ir a Mercado",
        "hecho": lambda estado, ctx: estado.visitado_mercado,
    },
    {
        "icon": "📰",
        "titulo": "Seguí las noticias",
        "detalle": "Noticias generales del mercado y, si tenés cartera cargada, de las empresas en las que invertís.",
        "page": "pages/3_Noticias.py",
        "page_label": "Ir a Noticias",
        "hecho": lambda estado, ctx: estado.visitado_noticias,
    },
]


def render_primeros_pasos(tiene_perfil_riesgo: bool, tiene_monto_mensual: bool, tiene_cartera: bool) -> None:
    """Dibuja la guía de primeros pasos en Home, con lo ya hecho tildado
    solo. No hace nada si la persona ya la cerró."""
    if st is None:
        return

    estado = load_state()
    if estado.dismissed:
        return

    ctx = {
        "tiene_perfil_riesgo": tiene_perfil_riesgo,
        "tiene_monto_mensual": tiene_monto_mensual,
        "tiene_cartera": tiene_cartera,
    }
    completados = sum(1 for paso in STEPS if paso["hecho"](estado, ctx))
    total = len(STEPS)

    with st.container(border=True):
        if completados == total:
            st.success("🎉 ¡Ya diste todos los primeros pasos! Explorá el resto de la app con el menú de la izquierda.")
        else:
            st.markdown(f"#### 🚀 Primeros pasos para arrancar ({completados}/{total})")
            st.progress(completados / total)

            for paso in STEPS:
                hecho = paso["hecho"](estado, ctx)
                marca = "✅" if hecho else "⬜"
                col_texto, col_accion = st.columns([5, 2])
                with col_texto:
                    st.markdown(f"{marca} {paso['icon']} **{paso['titulo']}**")
                    st.caption(paso["detalle"])
                with col_accion:
                    if not hecho:
                        if paso["page"]:
                            st.page_link(paso["page"], label=paso["page_label"])
                        else:
                            st.caption(paso["page_label"])

        if st.button("Ya sé cómo funciona, no mostrar más", key="onboarding_dismiss"):
            estado.dismissed = True
            save_state(estado)
            st.rerun()
