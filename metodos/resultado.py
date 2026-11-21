"""Estructuras comunes a ambos métodos: resultado, criterio de parada y datos de la gráfica."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from .formato import fmt, fmt_latex
from .funcion import Funcion

CONVERGIO = "convergio"
MAX_ITERACIONES = "max_iter"
FALLO = "fallo"

ETIQUETAS_ESTADO = {
    CONVERGIO: "Convergió",
    MAX_ITERACIONES: "No convergió",
    FALLO: "Falló",
}

CRITERIOS = {
    "absoluto": "Error absoluto |xₙ − xₙ₋₁| < ε",
    "relativo": "Error relativo porcentual |(xₙ − xₙ₋₁)/xₙ|·100 < ε",
}


@dataclass
class Linea:
    """Una línea del procedimiento, en texto plano (PDF/Excel) y en LaTeX (página web)."""

    texto: str
    latex: str | None = None


@dataclass
class Paso:
    titulo: str
    lineas: list[Linea] = field(default_factory=list)


@dataclass
class Resultado:
    metodo: str
    nombre_metodo: str
    funcion: str
    funcion_latex: str
    derivada: str | None
    derivada_latex: str | None
    parametros: dict
    columnas: list[dict]
    iteraciones: list[dict]
    raiz: float | None
    f_raiz: float | None
    error: float | None
    n_iteraciones: int
    estado: str
    mensaje: str
    pasos: list[Paso]
    formula: Linea
    decimales: int
    grafica: dict = field(default_factory=dict)

    @property
    def etiqueta_estado(self) -> str:
        return ETIQUETAS_ESTADO[self.estado]

    def to_dict(self) -> dict:
        datos = asdict(self)
        datos["etiqueta_estado"] = self.etiqueta_estado
        datos["criterio_texto"] = CRITERIOS[self.parametros["criterio"]]
        return datos


def errores(x_nuevo: float, x_anterior: float | None) -> tuple[float | None, float | None]:
    """Devuelve (error absoluto, error relativo %) entre dos aproximaciones consecutivas."""
    if x_anterior is None:
        return None, None
    ea = abs(x_nuevo - x_anterior)
    er = ea / abs(x_nuevo) * 100 if x_nuevo != 0 else None
    return ea, er


def cumple_tolerancia(criterio: str, ea: float | None, er: float | None, tol: float) -> bool:
    valor = ea if criterio == "absoluto" else er
    return valor is not None and valor < tol


def lineas_error(criterio: str, simbolo: str, x_nuevo: float, x_anterior: float | None,
                 ea: float | None, er: float | None, tol: float, d: int) -> list[Linea]:
    """Líneas del procedimiento que explican el cálculo del error y la comparación con ε."""
    if x_anterior is None:
        return [Linea("Primera aproximación: aún no hay valor anterior para calcular el error.")]
    lineas = [
        Linea(
            f"Eₐ = |{simbolo} nuevo − {simbolo} anterior| = |{fmt(x_nuevo, d)} − {fmt(x_anterior, d)}| = {fmt(ea, d)}",
            f"E_a = \\left|{fmt_latex(x_nuevo, d)} - {fmt_latex(x_anterior, d)}\\right| = {fmt_latex(ea, d)}",
        )
    ]
    if er is not None:
        lineas.append(
            Linea(
                f"Eᵣ = Eₐ / |{simbolo} nuevo| · 100 = {fmt(er, d)} %",
                f"E_r = \\frac{{E_a}}{{|{fmt_latex(x_nuevo, d)}|}}\\cdot 100 = {fmt_latex(er, d)}\\,\\%",
            )
        )
    valor, nombre, nombre_tex = (ea, "Eₐ", "E_a") if criterio == "absoluto" else (er, "Eᵣ", "E_r")
    unidad = "" if criterio == "absoluto" else " %"
    if valor is None:
        return lineas
    if valor < tol:
        lineas.append(
            Linea(
                f"{nombre} = {fmt(valor, d)}{unidad} < ε = {fmt(tol, d)}{unidad}  →  se alcanzó la tolerancia, el método converge.",
                f"{nombre_tex} = {fmt_latex(valor, d)} < \\varepsilon = {fmt_latex(tol, d)} \\;\\Rightarrow\\; \\text{{converge}}",
            )
        )
    else:
        lineas.append(
            Linea(
                f"{nombre} = {fmt(valor, d)}{unidad} ≥ ε = {fmt(tol, d)}{unidad}  →  se continúa iterando.",
                f"{nombre_tex} = {fmt_latex(valor, d)} \\geq \\varepsilon = {fmt_latex(tol, d)} \\;\\Rightarrow\\; \\text{{se continúa}}",
            )
        )
    return lineas


def datos_grafica(f: Funcion, x_min: float, x_max: float, puntos: list[dict], raiz: dict | None,
                  segmentos: list[dict], nombre_segmentos: str, errores_iter: list[dict],
                  intervalo: list[float] | None = None, muestras: int = 600) -> dict:
    """Prepara los datos para Plotly (web), matplotlib (PDF) y los gráficos de Excel."""
    if not np.isfinite([x_min, x_max]).all() or x_max - x_min <= 0:
        centro = 0.0 if not np.isfinite(x_min) else x_min
        x_min, x_max = centro - 1, centro + 1
    xs = np.linspace(x_min, x_max, muestras)
    ys = f.evaluar_vector(xs)

    finitos = ys[np.isfinite(ys)]
    if finitos.size:
        y_lo, y_hi = np.percentile(finitos, [2, 98])
    else:
        y_lo, y_hi = -1.0, 1.0
    extras = [p["y"] for p in puntos if p.get("y") is not None and np.isfinite(p["y"])]
    y_lo = min([y_lo, 0.0, *extras])
    y_hi = max([y_hi, 0.0, *extras])
    margen = (y_hi - y_lo) * 0.1 or 1.0
    y_lo, y_hi = y_lo - margen, y_hi + margen

    # Se descartan valores muy alejados (asíntotas) para que la curva no "salte".
    alcance = (y_hi - y_lo) * 2
    fuera = (ys < y_lo - alcance) | (ys > y_hi + alcance)
    ys[fuera] = np.nan

    def limpiar(arr):
        return [None if not np.isfinite(v) else float(v) for v in arr]

    return {
        "x": limpiar(xs),
        "y": limpiar(ys),
        "rango_x": [float(x_min), float(x_max)],
        "rango_y": [float(y_lo), float(y_hi)],
        "puntos": puntos,
        "raiz": raiz,
        "segmentos": segmentos,
        "nombre_segmentos": nombre_segmentos,
        "errores": errores_iter,
        "intervalo": intervalo,
    }
