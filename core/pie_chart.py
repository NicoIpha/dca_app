"""
Genera un gráfico de torta interactivo (SVG + JS puro, sin librerías
externas) donde al pasar el mouse por el nombre del ticker en la lista
se resalta la porción correspondiente en el gráfico, y viceversa.

Se devuelve un string HTML listo para pasarle a
streamlit.components.v1.html(...).
"""
import math
import re
from typing import Callable, List, Dict, Optional


def _sanitize_id(ticker: str) -> str:
    """HTML ids no deberían tener caracteres como '^'; los reemplazamos."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", ticker)


def _build_slices(items: List[Dict], cx: float, cy: float, r: float) -> List[Dict]:
    total = sum(item["value"] for item in items) or 1
    cumulative_angle = -90.0  # empieza arriba (12 en punto)
    slices = []
    for item in items:
        fraction = item["value"] / total
        angle = fraction * 360.0
        start_rad = math.radians(cumulative_angle)
        end_rad = math.radians(cumulative_angle + angle)
        x1, y1 = cx + r * math.cos(start_rad), cy + r * math.sin(start_rad)
        x2, y2 = cx + r * math.cos(end_rad), cy + r * math.sin(end_rad)
        large_arc = 1 if angle > 180 else 0
        path_d = f"M{cx},{cy} L{x1:.2f},{y1:.2f} A{r},{r} 0 {large_arc} 1 {x2:.2f},{y2:.2f} Z"
        slices.append(
            {
                "ticker": item["ticker"],
                "id": _sanitize_id(item["ticker"]),
                "d": path_d,
                "color": item["color"],
                "pct": fraction * 100,
                "value": item["value"],
            }
        )
        cumulative_angle += angle
    return slices


def build_interactive_pie(
    items: List[Dict], size: int = 300, format_value: Optional[Callable[[float], str]] = None
) -> str:
    """
    items: lista de dicts con {ticker, value, color}
    format_value: cómo mostrar el valor de cada porción junto al %
    (por defecto, un monto en dólares — ej: gráfico de la cartera real
    de Perfil). Pasar algo como `lambda v: f"{v:.0f}%"` cuando `value`
    ya es un porcentaje y no un monto (ej: cartera modelo por clase de
    activo en Perfil de Riesgo).
    Devuelve HTML con el gráfico de torta + lista de tickers, ambos
    sincronizados por hover.
    """
    if format_value is None:
        format_value = lambda v: f"${v:,.0f}"

    r = size * 0.42
    cx = cy = size / 2
    slices = _build_slices(items, cx, cy, r)

    paths_html = "\n".join(
        f'<path id="slice-{s["id"]}" d="{s["d"]}" fill="{s["color"]}" '
        f'stroke="#0e1117" stroke-width="2" '
        f'onmouseover="highlight(\'{s["id"]}\')" onmouseout="unhighlight(\'{s["id"]}\')" '
        f'style="transform-origin: {cx}px {cy}px; transition: transform 0.15s ease, filter 0.15s ease; cursor: pointer;">'
        f'<title>{s["ticker"]}: {s["pct"]:.1f}%</title></path>'
        for s in slices
    )

    rows_html = "\n".join(
        f'<div id="label-{s["id"]}" onmouseover="highlight(\'{s["id"]}\')" onmouseout="unhighlight(\'{s["id"]}\')" '
        f'style="display:flex; align-items:center; gap:10px; padding:8px 10px; border-radius:8px; '
        f'cursor:pointer; transition: background 0.15s ease;">'
        f'<span style="width:12px; height:12px; border-radius:50%; background:{s["color"]}; flex-shrink:0;"></span>'
        f'<span style="font-family: sans-serif; font-size:14px; color:#e6e6e6;">'
        f'<strong>{s["ticker"]}</strong> &nbsp;·&nbsp; {s["pct"]:.1f}% &nbsp;·&nbsp; {format_value(s["value"])}'
        f'</span></div>'
        for s in slices
    )

    return f"""
    <div style="display:flex; align-items:center; gap:32px; flex-wrap:wrap;">
      <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        {paths_html}
      </svg>
      <div style="display:flex; flex-direction:column; gap:4px; min-width:200px;">
        {rows_html}
      </div>
    </div>
    <script>
      function highlight(id) {{
        var slice = document.getElementById('slice-' + id);
        var label = document.getElementById('label-' + id);
        if (slice) {{
          slice.style.transform = 'scale(1.06)';
          slice.style.filter = 'brightness(1.25)';
        }}
        if (label) {{
          label.style.background = 'rgba(255,255,255,0.08)';
        }}
      }}
      function unhighlight(id) {{
        var slice = document.getElementById('slice-' + id);
        var label = document.getElementById('label-' + id);
        if (slice) {{
          slice.style.transform = 'scale(1)';
          slice.style.filter = 'none';
        }}
        if (label) {{
          label.style.background = 'transparent';
        }}
      }}
    </script>
    """
