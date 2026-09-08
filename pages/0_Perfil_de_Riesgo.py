"""
Página de Perfil de Riesgo: cuestionario corto para estimar la
tolerancia al riesgo de la persona, y mostrarle una cartera modelo
(Conservador / Moderado / Agresivo) como punto de partida de dónde
poner su dinero.

Es el primer lugar al que llega alguien que recién abre la app y no
sabe por dónde arrancar. No reemplaza el asesoramiento financiero
personalizado: es un modelo general para tener una referencia rápida.
Para armar la cartera real con tickers concretos está la sección
Perfil.
"""
import streamlit as st
import streamlit.components.v1 as components

from core.risk_profile import QUESTIONS, compute_result, load_result, save_result
from core.model_portfolios import MODEL_PORTFOLIOS, ASSET_CLASS_COLORS, ASSET_CLASS_EXAMPLES
from core.pie_chart import build_interactive_pie

st.set_page_config(page_title="Perfil de Riesgo", layout="wide")
st.title("🎯 Perfil de Riesgo")
st.caption(
    "Respondé estas preguntas para saber qué tan cómodo/a estás con el riesgo, "
    "y te sugerimos una cartera modelo como punto de partida — no es una "
    "recomendación financiera personalizada, es una guía general."
)

resultado_guardado = load_result()

if "mostrar_cuestionario" not in st.session_state:
    st.session_state.mostrar_cuestionario = resultado_guardado is None

# ---------------------------------------------------------------------------
# Cuestionario (se muestra si todavía no hay resultado guardado, o si la
# persona pidió volver a hacerlo)
# ---------------------------------------------------------------------------
if resultado_guardado is None or st.session_state.mostrar_cuestionario:
    st.subheader("Cuestionario")

    respuestas_seleccionadas = []
    for i, pregunta in enumerate(QUESTIONS):
        opciones_texto = [op[0] for op in pregunta["opciones"]]
        elegida = st.radio(pregunta["texto"], opciones_texto, key=f"pregunta_{i}", index=None)
        if elegida is not None:
            puntaje = dict(pregunta["opciones"])[elegida]
            respuestas_seleccionadas.append(puntaje)
        st.write("")

    completo = len(respuestas_seleccionadas) == len(QUESTIONS)
    if not completo:
        st.caption(f"Respondiste {len(respuestas_seleccionadas)} de {len(QUESTIONS)} preguntas.")

    if st.button("Ver mi cartera sugerida", disabled=not completo, type="primary"):
        resultado = compute_result(respuestas_seleccionadas)
        save_result(resultado)
        st.session_state.mostrar_cuestionario = False
        st.rerun()

    st.stop()

# ---------------------------------------------------------------------------
# Resultado: perfil asignado + cartera modelo sugerida
# ---------------------------------------------------------------------------
portfolio = MODEL_PORTFOLIOS[resultado_guardado.perfil]

col_titulo, col_boton = st.columns([4, 1])
with col_titulo:
    st.success(f"Tu perfil es: **{portfolio.nombre}** (puntaje {resultado_guardado.score}/20)")
with col_boton:
    if st.button("Volver a hacer el cuestionario"):
        st.session_state.mostrar_cuestionario = True
        st.rerun()

st.divider()

st.subheader(f"Cartera modelo: {portfolio.nombre}")
st.write(portfolio.resumen)
st.caption(f"Horizonte sugerido: {portfolio.horizonte_sugerido}")

col_grafico, col_detalle = st.columns([2, 3])

items = [
    {"ticker": clase, "value": pct, "color": ASSET_CLASS_COLORS.get(clase, "#bdbdbd")}
    for clase, pct in portfolio.allocation.items()
    if pct > 0
]

with col_grafico:
    html = build_interactive_pie(items, size=260, format_value=lambda v: f"{v:.0f}%")
    components.html(html, height=max(280, 60 * len(items)), scrolling=False)

with col_detalle:
    for clase, pct in portfolio.allocation.items():
        if pct <= 0:
            continue
        st.markdown(
            f'<span style="color:{ASSET_CLASS_COLORS.get(clase, "#bdbdbd")};">●</span> '
            f'**{clase}** — {pct:.0f}%<br>'
            f'<span style="font-size:13px; color:#999;">{ASSET_CLASS_EXAMPLES.get(clase, "")}</span>',
            unsafe_allow_html=True,
        )
        st.write("")

st.divider()

st.subheader("Comparación de los 3 perfiles")
cols = st.columns(3)
for col, key in zip(cols, ["conservador", "moderado", "agresivo"]):
    p = MODEL_PORTFOLIOS[key]
    with col:
        es_el_tuyo = key == portfolio.key
        st.markdown(f"{'👉 ' if es_el_tuyo else ''}**{p.nombre}**")
        for clase, pct in p.allocation.items():
            if pct > 0:
                st.caption(f"{clase}: {pct:.0f}%")

st.divider()
st.caption(
    "⚠️ Esta cartera modelo es un punto de partida general en base a tus "
    "respuestas, no una recomendación financiera personalizada. Para armar "
    "tu cartera real con tickers concretos y hacerle seguimiento, andá a la "
    "sección **Perfil**."
)
