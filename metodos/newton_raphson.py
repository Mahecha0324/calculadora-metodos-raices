"""Método de Newton-Raphson — método abierto."""
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
    {"clave": "xn", "titulo": "xn", "latex": "x_n"},
    {"clave": "fxn", "titulo": "f(xn)", "latex": "f(x_n)"},
    {"clave": "dfxn", "titulo": "f'(xn)", "latex": "f'(x_n)"},
    {"clave": "xn1", "titulo": "xn+1", "latex": "x_{n+1}"},
    {"clave": "ea", "titulo": "Error abs.", "latex": "E_a"},
    {"clave": "er", "titulo": "Error rel. (%)", "latex": "E_r\\,(\\%)"},
]

FORMULA = Linea("xn+1 = xn − f(xn) / f'(xn)", "x_{n+1} = x_n - \\frac{f(x_n)}{f'(x_n)}")

DERIVADA_CASI_CERO = 1e-12
LIMITE_DIVERGENCIA = 1e8


def newton_raphson(f: Funcion, x0: float, tol: float, max_iter: int,
                   criterio: str = "absoluto", decimales: int = 6) -> Resultado:
    d = decimales
    df = f.derivada()
    iteraciones: list[dict] = []
    pasos: list[Paso] = [
        Paso(
            "Derivada de la función",
            [
                Linea(f"f(x) = {f.como_texto}", f"f(x) = {f.latex}"),
                Linea(f"f'(x) = {df.como_texto}", f"f'(x) = {df.latex}"),
                Linea(f"Valor inicial: x0 = {fmt(x0, d)}", f"x_0 = {fmt_latex(x0, d)}"),
            ],
        )
    ]
    puntos: list[dict] = []
    segmentos: list[dict] = []
    errores_iter: list[dict] = []

    estado, mensaje = MAX_ITERACIONES, ""
    raiz = f_raiz = error = None
    xn = x0

    for n in range(1, max_iter + 1):
        try:
            fxn = f(xn)
            dfxn = df(xn)
        except ErrorEvaluacion as exc:
            estado, mensaje = FALLO, f"No se pudo continuar en la iteración {n}: {exc}."
            break

        if fxn == 0:
            raiz, f_raiz, estado = xn, 0.0, CONVERGIO
            pasos.append(Paso(f"Iteración {n}", [Linea(f"f({fmt(xn, d)}) = 0  →  x = {fmt(xn, d)} es una raíz exacta.")]))
            break

        if abs(dfxn) < DERIVADA_CASI_CERO:
            estado = FALLO
            mensaje = (f"La derivada es cero (o casi cero) en x = {fmt(xn, d)} (iteración {n}). "
                       "La recta tangente es horizontal y Newton-Raphson no puede continuar. "
                       "Pruebe con otro valor inicial.")
            pasos.append(Paso(f"Iteración {n}", [Linea(f"f'({fmt(xn, d)}) = {fmt(dfxn, d)} ≈ 0  →  no se puede dividir entre f'(xn).")]))
            break

        xn1 = xn - fxn / dfxn
        ea, er = errores(xn1, xn)
        fila = {"iteracion": n, "xn": xn, "fxn": fxn, "dfxn": dfxn, "xn1": xn1, "ea": ea, "er": er}

        paso = Paso(f"Iteración {n}")
        paso.lineas.append(
            Linea(
                f"x{n - 1} = {fmt(xn, d)},  f(x{n - 1}) = {fmt(fxn, d)},  f'(x{n - 1}) = {fmt(dfxn, d)}",
                f"x_{{{n - 1}}} = {fmt_latex(xn, d)},\\quad f(x_{{{n - 1}}}) = {fmt_latex(fxn, d)},\\quad f'(x_{{{n - 1}}}) = {fmt_latex(dfxn, d)}",
            )
        )
        paso.lineas.append(
            Linea(
                f"x{n} = {fmt(xn, d)} − {fmt_par(fxn, d)} / {fmt_par(dfxn, d)} = {fmt(xn1, d)}",
                f"x_{{{n}}} = {fmt_latex(xn, d)} - \\frac{{{fmt_latex(fxn, d)}}}{{{fmt_latex(dfxn, d)}}} = {fmt_latex(xn1, d)}",
            )
        )
        paso.lineas.extend(lineas_error(criterio, "x", xn1, xn, ea, er, tol, d))

        iteraciones.append(fila)
        pasos.append(paso)
        puntos.append({"n": n - 1, "x": xn, "y": fxn})
        segmentos.append({"n": n, "x0": xn, "y0": fxn, "x1": xn1, "y1": 0.0})
        errores_iter.append({"n": n, "ea": ea, "er": er})

        raiz, error = xn1, (ea if criterio == "absoluto" else er)
        try:
            f_raiz = f(xn1)
        except ErrorEvaluacion:
            f_raiz = None

        if abs(xn1) > LIMITE_DIVERGENCIA:
            estado = FALLO
            mensaje = (f"El método diverge: |x{n}| = {fmt(abs(xn1), d)} crece sin control. "
                       "Pruebe con un valor inicial más cercano a la raíz.")
            break
        if cumple_tolerancia(criterio, ea, er, tol) or f_raiz == 0:
            estado = CONVERGIO
            break
        xn = xn1

    if estado == CONVERGIO:
        mensaje = (f"El método convergió en {len(iteraciones)} iteraciones. "
                   f"Raíz aproximada x ≈ {fmt(raiz, d)}.")
    elif estado == MAX_ITERACIONES:
        mensaje = (f"Se alcanzó el máximo de {max_iter} iteraciones sin cumplir la tolerancia. "
                   f"Última aproximación: x ≈ {fmt(raiz, d)}. Pruebe otro valor inicial o más iteraciones.")
    elif not mensaje:
        mensaje = "El método no pudo completarse."

    if raiz is not None and f_raiz is not None:
        puntos.append({"n": len(iteraciones), "x": raiz, "y": f_raiz})

    xs = [x0] + [p["x"] for p in puntos]
    x_min, x_max = min(xs), max(xs)
    ancho = x_max - x_min
    if ancho < 1e-9:
        ancho = max(abs(x0), 1.0)
    grafica = datos_grafica(
        f,
        x_min - 0.3 * ancho,
        x_max + 0.3 * ancho,
        puntos,
        None if raiz is None or f_raiz is None else {"x": raiz, "y": f_raiz},
        segmentos,
        "Rectas tangentes",
        errores_iter,
    )

    return Resultado(
        metodo="newton_raphson",
        nombre_metodo="Newton-Raphson",
        funcion=f.como_texto,
        funcion_latex=f.latex,
        derivada=df.como_texto,
        derivada_latex=df.latex,
        parametros={"x0": x0, "tolerancia": tol, "max_iter": max_iter, "criterio": criterio},
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
