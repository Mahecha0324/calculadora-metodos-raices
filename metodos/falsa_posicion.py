"""Método de Falsa Posición (Regula Falsi) — método cerrado."""
from __future__ import annotations

from .formato import fmt, fmt_latex, fmt_latex_par, fmt_par
from .funcion import ErrorEvaluacion, Funcion
from .resultado import (
    CONVERGIO,
    FALLO,
    MAX_ITERACIONES,
    Linea,
    Paso,
    Resultado,
    cumple_tolerancia,
    datos_grafica,
    errores,
    lineas_error,
)

COLUMNAS = [
    {"clave": "iteracion", "titulo": "Iteración", "latex": "n"},
    {"clave": "a", "titulo": "a", "latex": "a"},
    {"clave": "b", "titulo": "b", "latex": "b"},
    {"clave": "fa", "titulo": "f(a)", "latex": "f(a)"},
    {"clave": "fb", "titulo": "f(b)", "latex": "f(b)"},
    {"clave": "xr", "titulo": "xr", "latex": "x_r"},
    {"clave": "fxr", "titulo": "f(xr)", "latex": "f(x_r)"},
    {"clave": "ea", "titulo": "Error abs.", "latex": "E_a"},
    {"clave": "er", "titulo": "Error rel. (%)", "latex": "E_r\\,(\\%)"},
    {"clave": "subintervalo", "titulo": "Raíz en", "latex": "\\text{Raíz en}"},
]

FORMULA = Linea(
    "xr = b − f(b)·(b − a) / (f(b) − f(a))",
    "x_r = b - \\frac{f(b)\\,(b-a)}{f(b)-f(a)}",
)


def falsa_posicion(f: Funcion, a: float, b: float, tol: float, max_iter: int,
                   criterio: str = "absoluto", decimales: int = 6) -> Resultado:
    """Aplica Falsa Posición en [a, b]. Se asume que ya se validó que f(a)·f(b) <= 0."""
    d = decimales
    a0, b0 = a, b
    fa, fb = f(a), f(b)
    iteraciones: list[dict] = []
    pasos: list[Paso] = []
    puntos: list[dict] = []
    segmentos: list[dict] = []
    errores_iter: list[dict] = []

    pasos.append(
        Paso(
            "Verificación del intervalo",
            [
                Linea(
                    f"f(a) = f({fmt(a, d)}) = {fmt(fa, d)}    f(b) = f({fmt(b, d)}) = {fmt(fb, d)}",
                    f"f(a) = f({fmt_latex(a, d)}) = {fmt_latex(fa, d)} \\qquad f(b) = f({fmt_latex(b, d)}) = {fmt_latex(fb, d)}",
                ),
                Linea(
                    f"f(a)·f(b) = {fmt(fa * fb, d)} ≤ 0  →  existe al menos una raíz en [a, b].",
                    f"f(a)\\cdot f(b) = {fmt_latex(fa * fb, d)} \\leq 0 \\;\\Rightarrow\\; \\exists\\, \\text{{raíz en }} [a, b]",
                ),
            ],
        )
    )

    estado, mensaje = MAX_ITERACIONES, ""
    raiz = f_raiz = error = None
    x_anterior: float | None = None

    if fa == 0 or fb == 0:
        raiz = a if fa == 0 else b
        f_raiz = 0.0
        estado = CONVERGIO
        mensaje = f"El extremo {'a' if fa == 0 else 'b'} = {fmt(raiz, d)} es una raíz exacta: f = 0."
        pasos[0].lineas.append(Linea(mensaje))
    else:
        for n in range(1, max_iter + 1):
            xr = b - fb * (b - a) / (fb - fa)
            try:
                fxr = f(xr)
            except ErrorEvaluacion as exc:
                estado, mensaje = FALLO, f"No se pudo continuar en la iteración {n}: {exc}."
                break
            ea, er = errores(xr, x_anterior)
            producto = fa * fxr

            fila = {"iteracion": n, "a": a, "b": b, "fa": fa, "fb": fb, "xr": xr, "fxr": fxr, "ea": ea, "er": er}
            paso = Paso(f"Iteración {n}")
            paso.lineas.append(
                Linea(
                    f"Intervalo: [a, b] = [{fmt(a, d)}, {fmt(b, d)}],  f(a) = {fmt(fa, d)},  f(b) = {fmt(fb, d)}",
                    f"[a,b] = [{fmt_latex(a, d)},\\ {fmt_latex(b, d)}],\\quad f(a) = {fmt_latex(fa, d)},\\quad f(b) = {fmt_latex(fb, d)}",
                )
            )
            paso.lineas.append(
                Linea(
                    f"xr = {fmt(b, d)} − {fmt_par(fb, d)}·({fmt(b, d)} − {fmt_par(a, d)}) / ({fmt(fb, d)} − {fmt_par(fa, d)}) = {fmt(xr, d)}",
                    f"x_r = {fmt_latex(b, d)} - \\frac{{{fmt_latex_par(fb, d)}\\left({fmt_latex(b, d)} - {fmt_latex_par(a, d)}\\right)}}"
                    f"{{{fmt_latex(fb, d)} - {fmt_latex_par(fa, d)}}} = {fmt_latex(xr, d)}",
                )
            )
            paso.lineas.append(
                Linea(f"f(xr) = f({fmt(xr, d)}) = {fmt(fxr, d)}",
                      f"f(x_r) = f({fmt_latex(xr, d)}) = {fmt_latex(fxr, d)}")
            )

            segmentos.append({"n": n, "x0": a, "y0": fa, "x1": b, "y1": fb})
            puntos.append({"n": n, "x": xr, "y": fxr})

            if producto < 0:
                fila["subintervalo"] = "[a, xr]"
                paso.lineas.append(
                    Linea(
                        f"f(a)·f(xr) = {fmt(producto, d)} < 0  →  la raíz está en [a, xr]; se actualiza b = {fmt(xr, d)}",
                        f"f(a)\\cdot f(x_r) = {fmt_latex(producto, d)} < 0 \\;\\Rightarrow\\; b = x_r = {fmt_latex(xr, d)}",
                    )
                )
                b, fb = xr, fxr
            elif producto > 0:
                fila["subintervalo"] = "[xr, b]"
                paso.lineas.append(
                    Linea(
                        f"f(a)·f(xr) = {fmt(producto, d)} > 0  →  la raíz está en [xr, b]; se actualiza a = {fmt(xr, d)}",
                        f"f(a)\\cdot f(x_r) = {fmt_latex(producto, d)} > 0 \\;\\Rightarrow\\; a = x_r = {fmt_latex(xr, d)}",
                    )
                )
                a, fa = xr, fxr
            else:
                fila["subintervalo"] = "xr es raíz"
                paso.lineas.append(Linea("f(xr) = 0  →  xr es una raíz exacta.", "f(x_r) = 0 \\;\\Rightarrow\\; x_r \\text{ es raíz exacta}"))

            paso.lineas.extend(lineas_error(criterio, "xr", xr, x_anterior, ea, er, tol, d))
            iteraciones.append(fila)
            pasos.append(paso)
            if ea is not None:
                errores_iter.append({"n": n, "ea": ea, "er": er})

            raiz, f_raiz, error = xr, fxr, (ea if criterio == "absoluto" else er)
            if fxr == 0 or cumple_tolerancia(criterio, ea, er, tol):
                estado = CONVERGIO
                break
            x_anterior = xr

        if estado == CONVERGIO:
            mensaje = (f"El método convergió en {len(iteraciones)} iteraciones. "
                       f"Raíz aproximada x ≈ {fmt(raiz, d)}.")
        elif estado == MAX_ITERACIONES:
            mensaje = (f"Se alcanzó el máximo de {max_iter} iteraciones sin cumplir la tolerancia. "
                       f"Última aproximación: x ≈ {fmt(raiz, d)}. Aumente las iteraciones o la tolerancia.")

    ancho = b0 - a0
    grafica = datos_grafica(
        f,
        a0 - 0.15 * ancho,
        b0 + 0.15 * ancho,
        puntos,
        None if raiz is None else {"x": raiz, "y": f_raiz},
        segmentos,
        "Rectas secantes",
        errores_iter,
        intervalo=[a0, b0],
    )

    return Resultado(
        metodo="falsa_posicion",
        nombre_metodo="Falsa Posición",
        funcion=f.como_texto,
        funcion_latex=f.latex,
        derivada=None,
        derivada_latex=None,
        parametros={"a": a0, "b": b0, "tolerancia": tol, "max_iter": max_iter, "criterio": criterio},
        columnas=COLUMNAS,
        iteraciones=iteraciones,
        raiz=raiz,
        f_raiz=f_raiz,
        error=error,
        n_iteraciones=len(iteraciones),
        estado=estado,
        mensaje=mensaje,
        pasos=pasos,
        formula=FORMULA,
        decimales=d,
        grafica=grafica,
    )
