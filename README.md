# Simulador de Inversiones DCA

App multipágina de Streamlit para simular, monitorear y explorar
inversiones periódicas (Dollar Cost Averaging).

## Estructura del proyecto

```
dca_app/
├── Home.py                  # Simulador (proyección + backtest histórico)
├── pages/
│   ├── 1_Perfil.py          # Cartera real: altas/bajas + gráfico de torta
│   ├── 2_Mercado.py         # Top 10 por rubro (1/3/5 años) + buscador
│   └── 3_Noticias.py        # Titulares con resumen y link a la nota
├── core/
│   ├── simulation.py        # Lógica pura de simulación DCA
│   ├── data_fetcher.py      # Precios históricos y actuales (yfinance)
│   ├── portfolio.py         # Manejo de la cartera real (persiste en JSON)
│   ├── market.py            # Universo de tickers por rubro + retornos
│   └── news.py               # Noticias vía RSS (MarketWatch, CNBC, Yahoo)
├── data/
│   └── portfolio.json        # Se crea solo, con tus posiciones cargadas
├── requirements.txt
└── README.md
```

## Cómo correrla

1. Entorno virtual (opcional pero recomendado):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # en Windows: venv\Scripts\activate
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Correr la app (el punto de entrada ahora es `Home.py`):
   ```bash
   streamlit run Home.py
   ```
   Si en Windows te tira "streamlit no se reconoce como comando", usá:
   ```bash
   python -m streamlit run Home.py
   ```

La barra lateral izquierda va a mostrar automáticamente las 4 secciones:
**Home** (simulador), **Perfil**, **Mercado** y **Noticias**.

## Las secciones

### 🏠 Home — Simulador
Lo que ya tenías: proyección con tasa asumida, o backtest histórico real
con un ticker, para distintos horizontes (1/2/5/10 años, configurable).

### 👤 Perfil — Cartera real
Cargás tus posiciones reales (ticker, cantidad de acciones, precio
promedio de compra). La app:
- Guarda todo en `data/portfolio.json` (persiste entre sesiones).
- Calcula el valor actual de cada posición con el precio de mercado.
- Muestra un **gráfico de torta** con el % que representa cada acción
  sobre el valor total de la cartera.
- Muestra invertido / valor actual / ganancia-pérdida.

### 🏦 Mercado — Por rubro
- Elegís un rubro (Tecnología, Salud, Financiero, Energía, etc.) y un
  horizonte (1, 3 o 5 años).
- El **listado de empresas de cada rubro se trae en vivo desde Yahoo
  Finance** (vía `yfinance.Sector(...).top_companies`), no está
  hardcodeado. Se cachea 24hs para que la app no se ponga lenta ni
  golpee la API de más.
- Con ese listado, calcula el retorno real de cada empresa en el
  horizonte elegido y te muestra el **top 10**.
- Si Yahoo Finance no responde (sin internet, o versión vieja de
  `yfinance` que no tiene el módulo `Sector`), usa un respaldo chico
  hardcodeado (`FALLBACK_TICKERS` en `core/market.py`) para que la app
  no se rompa.
- Buscador: si una empresa no aparece en el top del rubro, la buscás
  por ticker y te trae su retorno a 1/3/5 años igual, sin depender del
  listado del rubro.

> **Importante**: el módulo `Sector` de yfinance es relativamente
> nuevo. Si te tira error al elegir un rubro, corré
> `pip install --upgrade yfinance` y volvé a intentar.

### 📰 Noticias
- Pestaña "Mercado general": titulares de MarketWatch y CNBC.
- Pestaña "De mi cartera": si cargaste posiciones en Perfil, trae
  noticias específicas de esos tickers (vía el feed RSS de Yahoo
  Finance por ticker).
- Cada noticia muestra el resumen que trae la propia fuente (no
  generado por IA) y un link directo para leer la nota completa.

## Ideas para seguir ampliando

1. **Simulación de Monte Carlo** en el simulador: usar la volatilidad
   histórica en vez de una tasa fija, y mostrar un rango de resultados
   posibles (percentiles 10/50/90).
2. **Comparar varios tickers a la vez** en Mercado, superpuestos en un
   mismo gráfico de evolución.
3. **Alertas**: marcar en Noticias o Mercado si una acción de tu
   cartera tuvo una caída/suba fuerte reciente.
4. **Ampliar el universo de Mercado**: en vez de una lista curada a
   mano, integrar el listado completo de un índice (ej. S&P 500) con
   su clasificación de sector real (via `yfinance`'s `.info["sector"]`
   o un CSV de referencia).
5. **Exportar la cartera o los resultados** a CSV/Excel.
6. **Autenticación simple** si en algún momento la vas a compartir con
   más de una persona, para que cada quien tenga su propia cartera.

La separación `core/` (lógica) vs `Home.py` + `pages/` (interfaz) sigue
vigente: podés testear y extender cada módulo sin tocar la parte visual.
