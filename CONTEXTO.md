# Contexto del proyecto — Simulador de Inversiones DCA

Este archivo resume el estado del proyecto y las decisiones/gotchas que
costó descubrir, para que una conversación nueva (conmigo o con
cualquiera que retome el proyecto) pueda arrancar rápido sin tener que
releer todo el historial del chat.

## Qué es la app

App de Streamlit para alguien que **no sabe administrar sus finanzas**:
lo guía desde "¿cuánto ahorrás por mes?" hasta comparar sus opciones
reales (guardar la plata, plazo fijo, S&P 500), con datos reales de
mercado, no inventados.

## Estructura

```
dca_app/
├── Home.py                  # Encuesta + objetivo de ahorro tangible (con gráficos Plotly) + comparación de 3 escenarios + simulador avanzado
├── pages/
│   ├── 0_Perfil_de_Riesgo.py # Cuestionario de riesgo + cartera modelo sugerida (Conservador/Moderado/Agresivo)
│   ├── 1_Perfil.py          # Cartera real: altas/bajas, gráfico de torta interactivo por rubro
│   ├── 2_Mercado.py         # Noticias de tus posiciones + Top 10 por rubro + buscador con alta directa a cartera
│   └── 3_Noticias.py        # RSS con imagen, resumen y link
├── core/
│   ├── simulation.py        # Motor de simulación DCA (ver "TNA vs tasa efectiva" abajo)
│   ├── data_fetcher.py      # Precios de yfinance (históricos, actuales)
│   ├── portfolio.py         # Cartera real (persiste en data/portfolio.json)
│   ├── ticker_catalog.py    # 50 tickers populares + los que el usuario fue agregando (data/known_tickers.json)
│   ├── classification.py    # Categoría/rubro + color de cada ticker (para el gráfico de torta)
│   ├── pie_chart.py         # Gráfico de torta interactivo (SVG+JS, sin librerías externas)
│   ├── charts.py            # Estilo Plotly compartido (gráficos de línea de Home): paleta, fondo transparente
│   ├── market.py            # Top 10 por rubro (yfinance.Sector, listado real, no hardcodeado)
│   ├── news.py               # Noticias RSS (MarketWatch, CNBC, Yahoo por ticker) + imagen
│   ├── user_profile.py       # Encuesta de "cuánto ahorrás por mes" (persiste en data/user_profile.json)
│   ├── risk_profile.py       # Cuestionario de perfil de riesgo (persiste en data/risk_profile.json)
│   ├── model_portfolios.py   # Carteras modelo por perfil (% por clase de activo, sin tickers puntuales)
│   ├── savings_goals.py      # Objetivos de ahorro tangibles + "cuánto tardás en llegar" (Home)
│   ├── onboarding.py         # Guía de "primeros pasos" en Home (progreso persistido en data/onboarding.json)
│   └── bcra.py                # Tasa de plazo fijo, dólar oficial y devaluación (ver abajo)
├── data/                     # JSONs de persistencia (se crean solos)
├── requirements.txt
└── README.md                 # Instrucciones de instalación/uso (para el usuario final)
```

## Decisiones y gotchas importantes (no obvias)

### 1. TNA vs. tasa efectiva — NO son intercambiables
El BCRA informa la tasa de plazo fijo como **TNA (Tasa Nominal Anual)**,
que es una tasa **lineal**: el rendimiento mensual real es `TNA / 12`,
punto. NO se debe convertir con raíz doceava (`(1+tasa)^(1/12)-1`) —
esa fórmula es para tasas **efectivas/compuestas**, y aplicada a una
TNA infla artificialmente el resultado.

En `core/simulation.py` hay DOS funciones separadas por esto:
- `simulate_dca_monthly_rate(monto, meses, tasa_mensual)`: motor base,
  recibe la tasa mensual ya calculada por quien llama. Se usa para el
  plazo fijo (TNA/12).
- `simulate_dca_fixed_rate(monto, meses, tasa_anual_pct)`: para tasas
  efectivas/compuestas (ej. el "Retorno anual asumido" del simulador
  avanzado). Por dentro llama a la anterior.

### 2. Plazo fijo en pesos → equivalente en dólares (mes a mes)
El escenario de plazo fijo se calcula así, **mes a mes** (no una sola
vez al año):
1. `tasa_mensual_pesos = TNA / 100 / 12` (lineal)
2. `tasa_mensual_devaluacion = (1 + devaluación_anual/100)^(1/12) - 1`
   (esta sí es compuesta, porque la devaluación del dólar sí es un
   proceso que compone año a año — es un CAGR real, no una TNA)
3. `tasa_mensual_usd = (1 + tasa_mensual_pesos) / (1 + tasa_mensual_devaluacion) - 1`

Esto puede dar **negativo** (el plazo fijo "pierde" contra el dólar) y
está bien que así sea — es la realidad histórica de Argentina la
mayoría de los períodos.

### 3. APIs usadas para datos de Argentina — con historial de dolores de cabeza
- ~~`api.bcra.gob.ar/estadisticas/v3.0`~~ → **dada de baja** (410 Gone).
  Hubo que migrar a v4.0, que además cambia los nombres de campo
  (`ultValorInformado`/`ultFechaInformada` en vez de `valor`/`fecha`).
- Después de varias vueltas buscando la variable correcta en el
  listado de 1000+ variables del BCRA (con nombres que no siempre
  contienen "plazo fijo" literal), **se abandonó la API cruda del
  BCRA** en favor de:
- **`api.argentinadatos.com`**: API pública que reprocesa los mismos
  datos del BCRA en endpoints mucho más simples y estables:
  - `GET /v1/finanzas/tasas/depositos30Dias` → `[{fecha, valor}]`
  - `GET /v1/cotizaciones/dolares/oficial` → `[{moneda, casa, fecha, compra, venta}]`
  - Sin token, sin necesidad de buscar IDs de variables.
- Todo esto vive en `core/bcra.py`. Si en el futuro esta API también
  cambia, **revisar primero con búsqueda web la documentación actual**
  antes de adivinar el esquema — ya pasó dos veces que un esquema
  asumido resultó estar desactualizado.

### 4. Streamlit + signos `$` = LaTeX no deseado
Cualquier texto en Streamlit (`st.write`, `st.caption`, labels de
widgets, etc.) que tenga **dos o más `$`** en el mismo string puede
disparar el renderizado de fórmulas matemáticas (LaTeX/KaTeX), y el
texto entre medio sale con otra tipografía/color. Solución: escapar
como `\$` (con doble backslash en el código fuente: `"\\$"`, porque un
solo backslash genera un `SyntaxWarning` de secuencia de escape
inválida en Python).

### 5. Streamlit multipágina
El punto de entrada es `Home.py` (no `app.py`), y las páginas viven en
`pages/` con prefijo numérico (`1_Perfil.py`, etc.) — así aparecen
ordenadas solas en el menú lateral. Se corre con
`streamlit run Home.py` (o `python -m streamlit run Home.py` si el
comando `streamlit` no se reconoce en la terminal).

### 6. Entorno de Windows
El usuario trabaja en Windows con Anaconda + VS Code. Terminó usando
un entorno virtual dedicado (`.venv` dentro de `dca_app`, creado con
`python -m venv .venv` y activado con `.venv\Scripts\Activate.ps1`)
para evitar conflictos con el Python global/Anaconda. Los avisos de
Pylance ("Import could not be resolved") y de VS Code ("Error
refreshing packages") eran síntomas de que el intérprete seleccionado
en el editor no coincidía con el de la terminal — no afectaban la
ejecución real de la app.

### 7. Carteras modelo por perfil de riesgo (`0_Perfil_de_Riesgo.py`)
Página nueva, primera en el menú (prefijo `0_`), pensada para ser lo
primero que alguien ve al abrir la app: un cuestionario corto que
asigna un perfil de riesgo y sugiere una cartera modelo.

- **`core/risk_profile.py`**: 5 preguntas (horizonte, reacción ante una
  caída del 20%, para qué es la plata, experiencia, qué % de los
  ahorros totales representa), cada opción puntúa 1-4. La suma (5 a 20)
  mapea a un perfil: 5-9 conservador, 10-15 moderado, 16-20 agresivo.
  Persiste en `data/risk_profile.json`.
- **`core/model_portfolios.py`**: las 3 carteras modelo, definidas como
  **% por clase de activo** (Efectivo/Plazo fijo, Bonos, Acciones/ETFs,
  Cripto) — a propósito sin tickers puntuales, para no tener que
  mantenerlos actualizados ni dar la impresión de una recomendación de
  instrumentos específicos. Cada clase tiene un color fijo
  (`ASSET_CLASS_COLORS`) y un ejemplo ilustrativo de texto
  (`ASSET_CLASS_EXAMPLES`), separado de `CATEGORY_COLORS` de
  `classification.py` (que es por rubro/industria de un ticker, un
  concepto distinto).
- **`core/pie_chart.py`** ganó un parámetro opcional `format_value`
  (callable) en `build_interactive_pie(...)`: por defecto sigue
  mostrando `$` (para la cartera real de Perfil, que son montos), pero
  la cartera modelo le pasa `lambda v: f"{v:.0f}%"` porque ahí `value`
  ya es un porcentaje, no un monto. Si se agregan más usos del gráfico
  de torta con otro tipo de valor, seguir este mismo patrón en vez de
  hardcodear el formato dentro de `pie_chart.py`.
- El resultado del cuestionario se persiste, así que la próxima vez que
  se abre la página va directo al resultado (con un botón para
  rehacerlo). `Home.py` tiene un `st.info(...)` al principio invitando
  a ir primero a esta página.
- Es explícitamente un modelo general para arrancar, no asesoramiento
  financiero personalizado — el texto de la página lo aclara y remite a
  la sección Perfil para armar la cartera real con tickers concretos.

### 8. Home reorganizado: "🎯 Tu objetivo" arriba de todo (`core/savings_goals.py`)
El Home mezclaba demasiadas cosas al mismo nivel (encuesta, gráfico de
10 años, simulador avanzado, noticias). Se agregó una sección nueva,
**arriba del gráfico comparativo de 10 años**, que hace tangible el
ahorro: elegís un objetivo (depto ~$100.000, auto ~$20.000, fondo de
emergencia = 6x tu ahorro mensual, o un monto propio) y se muestra
cuánto tardarías en juntarlo guardando la plata, en plazo fijo, o
invirtiendo en el S&P 500.

- **`core/savings_goals.py`**: `GOAL_PRESETS` (los objetivos
  preestablecidos) y `months_to_reach_goal(monthly_amount, goal_amount,
  monthly_rate, max_months=360)`, que simula con
  `simulate_dca_monthly_rate` hasta encontrar el mes en que se alcanza
  la meta, con un **tope de 30 años** (si no se alcanza en ese
  horizonte, devuelve `None`, y `format_years_months` lo muestra como
  "más de 30 años" — pasa seguido con el objetivo del depto y montos
  mensuales chicos/tasa 0%, y es a propósito: el contraste con
  invertir es justamente el punto).
- El S&P 500 acá usa una **proyección por tasa** (CAGR histórico de los
  últimos `HORIZONTE_ANIOS` años, vía `annual_effective_to_monthly_rate`
  nueva en `core/simulation.py`), NO el backtest mes a mes real que usa
  el gráfico de "Tu panorama" — porque el objetivo puede tardar más
  años de los que hay datos históricos descargados. El CAGR se calcula
  a partir de la MISMA descarga de precios que ya se hace para el
  backtest (`get_monthly_closes`), para no pedirle los datos dos veces
  a Yahoo Finance.
- Los datos de mercado compartidos (tasa BCRA, dólar, devaluación,
  precios del S&P 500) se buscan **una sola vez**, antes de la sección
  del objetivo, y se reutilizan en "Tu panorama" más abajo.

### 9. Gráficos con Plotly (`core/charts.py`) en vez de matplotlib estático
A pedido de hacer los gráficos "más lindos" y agregar uno chico por
cada objetivo de ahorro, el Home pasó de matplotlib (imágenes estáticas
vía `st.pyplot`) a **Plotly** (`st.plotly_chart`, interactivo: tooltip
al pasar el mouse, zoom) para los gráficos de línea. El simulador
avanzado (dentro del expander "🔧 Simulador avanzado") y el gráfico de
torta de Perfil/Perfil de Riesgo (`core/pie_chart.py`, que es SVG a
mano, no matplotlib) **quedaron sin tocar** — no se pidió unificar esos.

- **`core/charts.py`**: paleta categórica fija (azul = guardar, naranja
  = plazo fijo, aqua/verde = S&P 500 — mismo orden siempre, nunca se
  reasigna) y dos builders: `build_goal_progress_figure(...)` (los
  gráficos chicos de "Tu objetivo": línea por estrategia + línea
  punteada de meta + un punto donde cada una la cruza) y
  `build_comparison_figure(...)` (el gráfico grande de "Tu panorama").
- **Gotcha importante — fondo del gráfico**: NO hardcodear un color de
  fondo asumiendo tema oscuro. `core/pie_chart.py` sí lo hace (asume
  `#0e1117`, el fondo oscuro por defecto de Streamlit) porque ahí es un
  SVG a mano; pero para Plotly se probó en un entorno con tema CLARO
  por default y un fondo oscuro fijo se veía como un parche negro feo
  sobre una página blanca. La solución: `plot_bgcolor` /
  `paper_bgcolor` en `rgba(0,0,0,0)` (transparente) y `font=dict(size=12)`
  sin fijar color, más `st.plotly_chart(fig, theme="streamlit")` (el
  default) para que el tema activo (el que sea, claro u oscuro) termine
  de adaptar tipografía y grilla. No hay forma confiable de detectar
  el tema real desde el script (`st.get_option("theme.base")` devuelve
  `None` si no hay un tema configurado explícitamente en
  `.streamlit/config.toml`), así que la fórmula "transparente + dejar
  que Streamlit termine de temear" es más robusta que asumir.
- Los 3 colores de estrategia SÍ son fijos en hex (no dependen del
  tema): son los tonos calibrados para fondo claro de una paleta
  categórica validada para daltonismo (ver skill de dataviz), que
  también se distinguen razonablemente bien sobre fondo oscuro.
- Probado end-to-end corriendo `streamlit run Home.py` con Playwright
  (headless, sin acceso real a BCRA/Yahoo Finance desde ese entorno,
  pero confirmando que no tira excepciones, que los objetivos calculan
  bien, y mirando el screenshot para chequear que se vea bien).
- **Gotcha de proceso (para la próxima)**: en esta sesión, los cambios
  se probaron primero armando una copia espejo completa del proyecto en
  una carpeta temporal (original + archivos nuevos/editados encima) y
  corriendo streamlit ahí — NO en la carpeta real del usuario — antes
  de recién ahí copiar los archivos definitivos a la carpeta real. Es
  clave, después de "commitear" un archivo a la carpeta real, volver a
  leerlo desde ahí (no asumir que porque se escribió a un archivo local
  de prueba ya se aplicó) para confirmar que el contenido que quedó
  ahí es el que se esperaba.

### 10. Noticias de la cartera: movidas de Home a Mercado
La idea original era que las noticias relevantes para el inversor
(las de los tickers que tiene en su cartera) vivieran en la sección
**Mercado**, no en Home — Home había terminado teniendo esa sección
"📰 Noticias de tus inversiones" al final por cómo fue creciendo, pero
no era el lugar pensado.

- Se sacó esa sección entera de `Home.py` (quedó terminando en el
  disclaimer, después del `st.divider()`).
- Se agregó "📰 Noticias de tus posiciones" al principio de
  `pages/2_Mercado.py` (antes del buscador por rubro, que ahora tiene
  su propio subtítulo "Top 10 por rubro" para separar visualmente las
  dos secciones). Reutiliza `core/portfolio.load_portfolio()` +
  `core/news.get_news_for_tickers()` + `core/news.render_news_list()`
  — las mismas funciones que ya usaba Home, sin duplicar lógica.
- **Pendiente a considerar**: `pages/3_Noticias.py` tiene una pestaña
  "De mi cartera" que muestra exactamente lo mismo. Quedó así porque no
  se pidió tocarla, pero ahora hay contenido duplicado en dos secciones
  (Mercado y Noticias). Si en algún momento se quiere prolijar, lo más
  simple sería sacar esa pestaña de `3_Noticias.py` y dejar solo
  "Mercado general" ahí, ya que la cartera vive ahora en Mercado.

### 11. Caché para que navegar entre páginas no se sienta lento + guía de "primeros pasos"

**Caché faltante en `core/data_fetcher.py`.** Streamlit vuelve a correr
el script de la página entera en cada interacción (no solo al navegar:
también al tocar cualquier widget). `core/bcra.py`, `core/market.py` y
`core/news.py` ya cacheaban sus llamadas de red con `st.cache_data`,
pero `core/data_fetcher.py` (que trae precios de yfinance:
`get_monthly_closes`, `get_current_price`,
`get_annualized_historical_return`) no tenía nada — así que cada rerun
de Home (el backtest del S&P 500) o de Perfil (el precio actual de
cada ticker de la cartera) volvía a pegarle a Yahoo Finance de cero.
Se le agregó el mismo patrón try/except de import que ya usan los otros
tres módulos (para poder testear sin streamlit instalado) y
`@cache_data`: 6hs para precios históricos/CAGR (no cambian más rápido
que eso), 15min para el precio "actual" (más corto porque es el único
que pretende reflejar el momento, pero tampoco hace falta pedirlo en
cada click). Con esto, entrar y salir de una página varias veces
reutiliza los datos ya bajados en vez de volver a descargarlos.

**`core/onboarding.py`: guía de primeros pasos en Home.** Para alguien
que abre la app por primera vez y no sabe por dónde arrancar, se
agregó una caja arriba de todo en Home con una checklist de 5 pasos:
hacer el test de inversor (Perfil de Riesgo), decir cuánto ahorra por
mes (se resuelve ahí mismo, más abajo en Home), cargar la cartera real
(Perfil), y explorar Mercado y Noticias — cada ítem con una frase
corta de qué es esa sección y, para las que son otra página, un
`st.page_link` para ir directo (requiere Streamlit >= 1.31, ya estamos
en >= 1.32).

- El progreso se persiste en `data/onboarding.json`
  (`OnboardingState`: `dismissed`, `visitado_mercado`,
  `visitado_noticias`) — mismo patrón que `risk_profile.json` /
  `user_profile.json` / `portfolio.json`. Los primeros 3 pasos se
  tildan solos leyendo el estado real (¿existe `risk_profile.json`?,
  ¿existe `user_profile.json`?, ¿la cartera tiene posiciones?); los
  últimos 2 (Mercado/Noticias, que son secciones para explorar más que
  "tareas") se tildan con `mark_visited("mercado")` /
  `mark_visited("noticias")`, una línea agregada al principio de esas
  dos páginas.
- Tiene un botón "Ya sé cómo funciona, no mostrar más" que persiste
  `dismissed=True` y esconde la caja; y, al pie de Home (después del
  disclaimer final), si está descartada aparece un botón chico
  "🔄 Volver a mostrar la guía de primeros pasos" para poder recuperarla
  sin tener que borrar el JSON a mano.
- Si ya se completaron los 5 pasos, en vez de la checklist se muestra
  un cartel de éxito con el mismo botón para ocultarlo.
- Reemplaza al viejo `st.info` de "¿No sabés en qué poner tu plata?"
  que estaba al principio de Home (quedaba redundante con el primer
  ítem de la checklist).
- Probado end-to-end con Playwright: arranca en 0/5 con la app
  "limpia" (sin JSONs de datos), sube a 1/5 al guardar el monto
  mensual, a 3/5 al visitar Mercado y Noticias (los otros dos quedan
  pendientes porque requieren datos que no se cargaron en la prueba), el
  link a Perfil de Riesgo navega bien, y el flujo cerrar → botón
  "volver a mostrar" → vuelve a aparecer funciona en ambas direcciones.

### 12. La precarga de Home pasó de "cacheada con TTL" a "una sola vez por sesión, y nada más"

El punto 11 resolvía el caso general (no pegarle a la red de más), pero
el pedido puntual era más estricto: que la precarga de los datos de
mercado de Home (tasa de plazo fijo, dólar, devaluación, precios del
S&P 500) pase exactamente **una vez** al entrar a la página, con un
aviso de "cargando" mientras dura, y nada más después — ni un
mini-delay de caché ni un spinner que parpadee de nuevo en cada
interacción.

`st.cache_data` con TTL (lo de la sección 11) no garantiza eso: sigue
siendo "recalcular si pasó el tiempo X", así que en teoría podía volver
a pegarle a la red en medio de una sesión larga, y además, aunque el
dato viniera de caché (rápido), la llamada a la función igual pasaba
por `st.spinner(...)` en cada rerun, lo cual puede parpadear la UI
sin necesidad.

**Solución: `st.session_state`, no `st.cache_data`, para este bloque
puntual.** Todo el fetch de datos de mercado de Home se movió a una
función `_precargar_datos_de_mercado(horizonte_anios)` que devuelve un
diccionario con todo adentro (tasas, dólar, devaluación, precios del
S&P 500, CAGR). Esa función se llama **una sola vez por sesión**,
adentro de:

```python
if "datos_mercado" not in st.session_state:
    with st.spinner("⏳ Cargando datos de mercado (...) esto pasa una sola vez por sesión."):
        st.session_state.datos_mercado = _precargar_datos_de_mercado(HORIZONTE_ANIOS)
```

En cualquier rerun posterior (tocar un slider, expandir algo, ir a
Mercado y volver a Home — `st.session_state` se comparte entre todas
las páginas de una app multipágina de Streamlit, así que sobrevive la
navegación), el `if` da `False` y ni siquiera se llama a la función:
no hay spinner, no hay chequeo de caché, no hay nada — se lee directo
de `st.session_state.datos_mercado`. Se verificó con un contador
temporal instrumentado en `get_tasa_plazo_fijo` que, a lo largo de
varias interacciones de UI y una ida y vuelta a Mercado, la función se
ejecuta **exactamente 1 vez** por sesión de navegador.

La única cuenta que se recalcula en cada rerun (a propósito) es
`res_sp500 = simulate_dca_from_prices(perfil.monto_mensual, precios_sp500)`,
porque es aritmética local (sin red) que depende del monto mensual
actual — si la persona lo cambia en la encuesta de arriba, tiene que
reflejarse sin necesidad de recargar la página ni repetir la precarga.

Los fetches de otras páginas (`core/market.py` en Mercado, `get_current_price`
en Perfil) se dejaron con el esquema de `st.cache_data` con TTL de la
sección 11, sin este patrón de `session_state`: son datos que **no** se
piden si no se visita esa página (ya son "lazy" por estar en un script
de página aparte), que es justamente la otra mitad del pedido — no
precargar de más lo que capaz no se termina usando.

### 13. Buscar un ticker que no está en la lista lo agrega directo a la cartera (y queda guardado)

Hasta ahora, un ticker fuera de la lista curada de ~50 populares se
podía cargar en Perfil escribiéndolo a mano (opción "Otro"), pero no
quedaba registrado en ningún lado — la próxima vez había que volver a
escribirlo. Y en Mercado, el buscador "🔍 Buscar otra firma" solo
mostraba los retornos históricos: no había forma de sumarlo a la
cartera real desde ahí.

- **`core/ticker_catalog.py`** ganó `remember_ticker(ticker, nombre="")`,
  que persiste el ticker en `data/known_tickers.json` (mismo patrón que
  el resto de los JSONs de `data/`). No hace nada si el ticker ya está
  en la lista curada (`POPULAR_TICKERS`) o ya estaba guardado — se
  puede llamar sin culpa cada vez que se agrega una posición, sea el
  ticker conocido o no. `get_display_options()` ahora devuelve la lista
  curada **más** estos tickers aprendidos (sin nombre de empresa, se
  muestran solo con el ticker: `"PYPL"` en vez de `"PYPL - PayPal"`,
  porque conseguir el nombre real requeriría otra llamada a la API de
  yfinance — `.info` — que es lenta y poco confiable; no se justificaba
  para esto).
- **`pages/1_Perfil.py`**: al agregar una posición nueva (con cualquier
  ticker, venga del selector o escrito a mano con "Otro"), justo
  después de guardar la cartera se llama a `remember_ticker(ticker_input)`.
  Así, la próxima vez que se abre el selector, ese ticker ya aparece
  sin tener que volver a escribirlo.
- **`pages/2_Mercado.py`**: el buscador "🔍 Buscar otra firma" ahora,
  además de los retornos históricos, intenta traer el precio de
  mercado actual (`core.data_fetcher.get_current_price`) y muestra un
  expander "➕ Agregar {ticker} a mi cartera" con precio de compra y
  monto invertido (precargados con el precio de mercado si se pudo
  traer, editables igual que en Perfil). Al confirmar, se agrega como
  posición real (`core.portfolio.add_holding` + `save_portfolio`) y se
  llama a `remember_ticker(...)` — o sea, la misma acción cubre las dos
  cosas: "sumalo a mi cartera" y "acordate de este ticker para la
  próxima". Si no se pudo confirmar el precio actual (sin internet, o
  ticker inexistente), se muestra una advertencia pero se puede seguir
  agregando con un precio a mano — mismo criterio que ya usaba Perfil
  cuando `get_current_price` falla.
  - El resultado de la búsqueda se guarda en `st.session_state`
    (`ticker_encontrado`, `retornos_encontrados`) porque tocar los
    `number_input` de precio/monto dispara un rerun de la página, y sin
    esto se perdería el resultado de la búsqueda en el medio. Se limpia
    al agregar la posición o al apretar "Cancelar búsqueda".
- Probado end-to-end: se buscó un ticker fuera de las listas curadas
  (PYPL) desde Mercado sin acceso real a internet en el entorno de
  prueba (por eso no se pudo autocompletar el precio, y apareció la
  advertencia correspondiente), se cargó un precio a mano, se agregó a
  la cartera, y se confirmó que: (a) apareció en "Tus posiciones" en
  Perfil, (b) quedó en `data/known_tickers.json`, y (c) el selector de
  Perfil lo ofrece desde ese momento sin tener que escribirlo de nuevo.

## Cómo seguir trabajando en este proyecto de forma eficiente

**El problema que estás resolviendo ahora**: cada mensaje nuevo en
este chat reenvía TODO el historial anterior, así que cuanto más larga
la conversación, más caro (en tokens) es cada respuesta — aunque yo ya
no necesite releer decisiones viejas para ayudarte con algo nuevo.

**La solución no es "hacer que yo recuerde menos" dentro de este chat**
(eso no es controlable desde acá), sino:

1. **Para el próximo cambio grande, iniciá una conversación nueva** y
   subí este `CONTEXTO.md` junto con los archivos `.py` relevantes al
   cambio que quieras hacer (no hace falta subir los 15 archivos, solo
   los que tocan). Yo puedo leer el estado real del código en vez de
   inferirlo de la charla.

2. **Para iteración más ágil y directa sobre tus archivos**, considerá
   pasarte a **Claude Code** (versión de escritorio): en vez de
   copiar/pegar código en un chat, trabaja directo sobre la carpeta
   `dca_app` en tu compu — lee y edita los archivos reales, corre la
   app, y no depende de que vos subas manualmente cada archivo
   modificado. El contexto persistente ahí son los propios archivos
   del proyecto, no una conversación que crece sin límite.

3. Si en algún momento hacés cambios grandes de arquitectura, actualizá
   este mismo `CONTEXTO.md` (la sección de gotchas, sobre todo) para
   que seis meses o seis conversaciones después, tanto vos como
   cualquier IA que retome el proyecto no tengan que redescubrir los
   mismos problemas.
