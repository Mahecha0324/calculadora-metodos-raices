"""Valida los datos que llegan del formulario y ejecuta el método elegido."""
from __future__ import annotations

from .falsa_posicion import falsa_posicion
from .formato import fmt
from .funcion import ErrorEvaluacion, ErrorFuncion, interpretar_funcion, interpretar_numero
from .newton_raphson import newton_raphson
from .resultado import CRITERIOS, Resultado

METODOS = {"falsa_posicion": "Falsa Posición", "newton_raphson": "Newton-Raphson"}
MAX_ITER_PERMITIDAS = 1000


class ErrorValidacion(ValueError):
    """Agrupa los errores de cada campo del formulario: {campo: mensaje}."""

    def __init__(self, errores: dict[str, str]):
        super().__init__("; ".join(errores.values()))
        self.errores = errores


def _entero(valor, nombre: str, minimo: int, maximo: int) -> int:
    numero = interpretar_numero(valor, nombre)
    if numero != int(numero):
        raise ErrorFuncion(f"«{nombre}» debe ser un número entero.")
    numero = int(numero)
    if not minimo <= numero <= maximo:
        raise ErrorFuncion(f"«{nombre}» debe estar entre {minimo} y {maximo}.")
    return numero


def resolver(datos: dict) -> Resultado:
    """Punto de entrada único usado por la API y por las exportaciones."""
    errores: dict[str, str] = {}

    metodo = (datos.get("metodo") or "").strip()
    if metodo not in METODOS:
        errores["metodo"] = "Seleccione un método: Falsa Posición o Newton-Raphson."

    criterio = (datos.get("criterio") or "absoluto").strip()
    if criterio not in CRITERIOS:
        errores["criterio"] = "Criterio de parada no válido."

    f = None
    try:
        f = interpretar_funcion(datos.get("funcion"))
    except ErrorFuncion as exc:
        errores["funcion"] = str(exc)

    def leer(campo, nombre, conversor=interpretar_numero, *extra):
        try:
            return conversor(datos.get(campo), nombre, *extra)
        except ErrorFuncion as exc:
            errores[campo] = str(exc)
            return None

    tol = leer("tolerancia", "Tolerancia (ε)")
    if tol is not None and tol <= 0:
        errores["tolerancia"] = "La tolerancia debe ser mayor que 0."
    max_iter = leer("max_iter", "Máximo de iteraciones", _entero, 1, MAX_ITER_PERMITIDAS)
    decimales = 6
    if datos.get("decimales") not in (None, ""):
        decimales = leer("decimales", "Decimales", _entero, 2, 12)

    a = b = x0 = None
    if metodo == "falsa_posicion":
        a = leer("a", "Límite inferior (a)")
        b = leer("b", "Límite superior (b)")
        if a is not None and b is not None:
            if a >= b:
                errores["b"] = "El límite superior (b) debe ser mayor que el límite inferior (a)."
            elif f is not None:
                fa = fb = None
                try:
                    fa = f(a)
                except ErrorEvaluacion as exc:
                    errores["a"] = f"En a: {exc}."
                try:
                    fb = f(b)
                except ErrorEvaluacion as exc:
                    errores["b"] = f"En b: {exc}."
                if fa is not None and fb is not None and fa * fb > 0:
                    d = decimales or 6
                    errores["intervalo"] = (
                        f"No hay cambio de signo en [{fmt(a, d)}, {fmt(b, d)}]: "
                        f"f(a) = {fmt(fa, d)} y f(b) = {fmt(fb, d)} tienen el mismo signo. "
                        "Elija otro intervalo (revise la gráfica para ubicar la raíz)."
                    )
    elif metodo == "newton_raphson":
        x0 = leer("x0", "Valor inicial (x₀)")
        if x0 is not None and f is not None:
            try:
                f(x0)
            except ErrorEvaluacion as exc:
                errores["x0"] = f"En x₀: {exc}."

    if errores:
        raise ErrorValidacion(errores)

    if metodo == "falsa_posicion":
        return falsa_posicion(f, a, b, tol, max_iter, criterio, decimales)
    return newton_raphson(f, x0, tol, max_iter, criterio, decimales)


def vista_previa(texto: str) -> dict:
    """LaTeX de f(x) y f'(x) para mostrar mientras el usuario escribe."""
    f = interpretar_funcion(texto)
    df = f.derivada()
    return {"latex": f.latex, "derivada_latex": df.latex, "texto": f.como_texto, "derivada": df.como_texto}
