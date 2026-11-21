"""Gráficas estáticas (PNG) con matplotlib para incluirlas en el PDF."""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")  # sin ventana: solo genera imágenes
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from metodos.resultado import Resultado  # noqa: E402

AZUL = "#1d4ed8"
NARANJA = "#f59e0b"
ROJO = "#dc2626"
GRIS = "#94a3b8"


def _a_png(fig) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


def grafica_funcion(r: Resultado) -> bytes:
    g = r.grafica
    fig, ax = plt.subplots(figsize=(8, 4.2))
    xs = [x for x in g["x"]]
    ys = [float("nan") if y is None else y for y in g["y"]]
    ax.plot(xs, ys, color=AZUL, linewidth=2, label=f"f(x) = {r.funcion}")
    ax.axhline(0, color="#334155", linewidth=0.8)

    for i, s in enumerate(g["segmentos"]):
        ax.plot([s["x0"], s["x1"]], [s["y0"], s["y1"]], color=GRIS, linestyle="--", linewidth=0.9,
                label=g["nombre_segmentos"] if i == 0 else None)
    if g.get("intervalo"):
        ax.axvspan(*g["intervalo"], color=AZUL, alpha=0.06, label="Intervalo inicial [a, b]")
    if g["puntos"]:
        ax.scatter([p["x"] for p in g["puntos"]], [p["y"] for p in g["puntos"]], color=NARANJA,
                   zorder=3, s=28, label="Aproximaciones")
    if g["raiz"]:
        ax.scatter([g["raiz"]["x"]], [g["raiz"]["y"]], color=ROJO, zorder=4, s=60,
                   label=f"Raíz ≈ {g['raiz']['x']:.{r.decimales}f}")

    ax.set_xlim(*g["rango_x"])
    ax.set_ylim(*g["rango_y"])
    ax.set_xlabel("x")
    ax.set_ylabel("f(x)")
    ax.set_title(f"Gráfica de la función — {r.nombre_metodo}")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc="best")
    return _a_png(fig)


def grafica_error(r: Resultado) -> bytes | None:
    relativo = r.parametros["criterio"] == "relativo"
    clave = "er" if relativo else "ea"
    errores = [e for e in r.grafica["errores"] if e[clave] is not None and e[clave] > 0]
    if len(errores) < 2:
        return None
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.semilogy([e["n"] for e in errores], [e[clave] for e in errores], marker="o", color=AZUL, label="Error")
    tol = r.parametros["tolerancia"]
    ax.axhline(tol, color=ROJO, linestyle="--", linewidth=1,
               label=f"Tolerancia ε = {tol:g}" + (" %" if relativo else ""))
    ax.set_xlabel("Iteración")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylabel(("Error relativo (%)" if relativo else "Error absoluto") + " — escala log")
    ax.set_title("Convergencia del error")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    return _a_png(fig)
