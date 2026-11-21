"""Interpretación segura de la función f(x) y de los valores numéricos que ingresa el usuario.

Se usa SymPy para:
  * convertir el texto (por ejemplo "x^3 - x - 1") en una expresión matemática,
  * calcular la derivada automáticamente (necesaria para Newton-Raphson),
  * obtener la versión LaTeX para mostrarla bonita en la página.

Antes de interpretar el texto se valida con una lista blanca de caracteres y de
nombres, para que el usuario no pueda ejecutar código arbitrario.
"""
from __future__ import annotations

import math
import re

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_application,
    implicit_multiplication,
    parse_expr,
    standard_transformations,
)

X = sp.Symbol("x", real=True)

_TRANSFORMACIONES = standard_transformations + (
    convert_xor,  # permite usar ^ como potencia
    implicit_multiplication,  # permite escribir 2x en lugar de 2*x
    implicit_application,  # permite escribir sin x en lugar de sin(x)
)


def _log10(valor):
    return sp.log(valor, 10)


# Únicos nombres que el usuario puede escribir en la función.
NOMBRES_PERMITIDOS = {
    "x": X,
    "e": sp.E,
    "E": sp.E,
    "pi": sp.pi,
    "sin": sp.sin,
    "sen": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "tg": sp.tan,
    "sec": sp.sec,
    "csc": sp.csc,
    "cot": sp.cot,
    "asin": sp.asin,
    "arcsin": sp.asin,
    "acos": sp.acos,
    "arccos": sp.acos,
    "atan": sp.atan,
    "arctan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "exp": sp.exp,
    "log": sp.log,
    "ln": sp.log,
    "log10": _log10,
    "sqrt": sp.sqrt,
    "raiz": sp.sqrt,
    "abs": sp.Abs,
}

_CARACTERES_VALIDOS = re.compile(r"^[0-9a-zA-Z_+\-*/^().,=\s]*$")
_NOMBRE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NOTACION_CIENTIFICA = re.compile(r"\d+\.?\d*[eE][+-]?\d+")
_REEMPLAZOS = {"−": "-", "–": "-", "×": "*", "·": "*", "÷": "/", "²": "^2", "³": "^3"}
LONGITUD_MAXIMA = 200


class ErrorFuncion(ValueError):
    """La función escrita por el usuario no es válida."""


class ErrorEvaluacion(ArithmeticError):
    """La función no se puede evaluar en un punto (fuera del dominio, desbordamiento...)."""


def _normalizar(texto: str) -> str:
    texto = texto.strip()
    for original, nuevo in _REEMPLAZOS.items():
        texto = texto.replace(original, nuevo)
    # "f(x) = ..." o "y = ..." al inicio: se descarta esa parte
    texto = re.sub(r"^\s*(f\s*\(\s*x\s*\)|y)\s*=", "", texto)
    return texto.strip()


def _validar_texto(texto: str) -> None:
    if len(texto) > LONGITUD_MAXIMA:
        raise ErrorFuncion(f"La función es demasiado larga (máximo {LONGITUD_MAXIMA} caracteres).")
    if "__" in texto or not _CARACTERES_VALIDOS.match(texto):
        raise ErrorFuncion(
            "La función contiene caracteres no permitidos. Use números, x, + - * / ^ ( ) "
            "y funciones como sin, cos, exp, ln, sqrt."
        )
    sin_numeros = _NOTACION_CIENTIFICA.sub("0", texto)
    for nombre in _NOMBRE.findall(sin_numeros):
        if nombre not in NOMBRES_PERMITIDOS:
            raise ErrorFuncion(
                f"'{nombre}' no es una variable o función reconocida. Use x como variable "
                "y escriba los productos con * (ej.: 2*x*sin(x), exp(-x), ln(x))."
            )
    if texto.count("(") != texto.count(")"):
        raise ErrorFuncion("Los paréntesis de la función no están balanceados.")


def _parsear(texto: str) -> sp.Expr:
    try:
        expr = parse_expr(texto, local_dict=dict(NOMBRES_PERMITIDOS), transformations=_TRANSFORMACIONES)
    except Exception as exc:  # SyntaxError, TokenError, TypeError...
        raise ErrorFuncion("La función no tiene una sintaxis válida. Revise operadores y paréntesis.") from exc
    if not isinstance(expr, sp.Expr):
        raise ErrorFuncion("La expresión ingresada no es una función matemática válida.")
    return expr


class Funcion:
    """Una función de una variable lista para evaluarse numéricamente."""

    def __init__(self, texto: str, expr: sp.Expr):
        self.texto = texto
        self.expr = expr
        self._f_escalar = sp.lambdify(X, expr, modules="math")
        self._f_vector = sp.lambdify(X, expr, modules="numpy")

    @property
    def latex(self) -> str:
        return sp.latex(self.expr)

    @property
    def como_texto(self) -> str:
        """El texto tal como lo escribió el usuario (más fácil de reconocer que la forma de SymPy)."""
        return self.texto.replace("**", "^")

    def derivada(self) -> "Funcion":
        d = sp.diff(self.expr, X)
        try:
            simplificada = sp.simplify(d)
            if sp.count_ops(simplificada) <= sp.count_ops(d):
                d = simplificada
        except Exception:  # pragma: no cover - simplify rara vez falla
            pass
        return Funcion(str(d), d)

    def __call__(self, valor: float) -> float:
        try:
            resultado = self._f_escalar(valor)
        except (ValueError, ZeroDivisionError, OverflowError, TypeError) as exc:
            raise ErrorEvaluacion(f"la función no está definida en x = {valor:.6g}") from exc
        if isinstance(resultado, complex):
            if abs(resultado.imag) > 1e-12:
                raise ErrorEvaluacion(f"la función no está definida en x = {valor:.6g} (valor complejo)")
            resultado = resultado.real
        resultado = float(resultado)
        if not math.isfinite(resultado):
            raise ErrorEvaluacion(f"la función no es finita en x = {valor:.6g}")
        return resultado

    def evaluar_vector(self, xs: np.ndarray) -> np.ndarray:
        """Evalúa la función en muchos puntos (para las gráficas). Devuelve NaN donde no existe."""
        with np.errstate(all="ignore"):
            try:
                ys = self._f_vector(xs)
            except Exception:
                ys = np.array([self._seguro(v) for v in xs])
            ys = np.asarray(ys)
            if np.iscomplexobj(ys):
                ys = np.where(np.abs(ys.imag) < 1e-12, ys.real, np.nan)
            ys = np.broadcast_to(ys.astype(float), xs.shape).copy()
        ys[~np.isfinite(ys)] = np.nan
        return ys

    def _seguro(self, valor: float) -> float:
        try:
            return self(float(valor))
        except ErrorEvaluacion:
            return float("nan")


def interpretar_funcion(texto: str | None) -> Funcion:
    """Convierte el texto del usuario en una :class:`Funcion`. Lanza ErrorFuncion si no es válida."""
    if texto is None or not str(texto).strip():
        raise ErrorFuncion("Ingrese la función f(x).")
    texto = _normalizar(str(texto))
    if not texto:
        raise ErrorFuncion("Ingrese la función f(x).")
    _validar_texto(texto)

    if "=" in texto:
        # Ecuación del tipo  izquierda = derecha  ->  f(x) = izquierda - (derecha)
        partes = texto.split("=")
        if len(partes) != 2 or not partes[0].strip() or not partes[1].strip():
            raise ErrorFuncion("Escriba la función como f(x) o como una ecuación con un solo '='.")
        expr = _parsear(partes[0]) - _parsear(partes[1])
        texto = str(expr)
    else:
        expr = _parsear(texto)

    if expr.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        raise ErrorFuncion("La función contiene una división por cero o un valor indefinido.")
    if expr.free_symbols - {X}:
        raise ErrorFuncion("La función solo puede depender de la variable x.")
    if X not in expr.free_symbols:
        raise ErrorFuncion("La función debe depender de x (por ejemplo: x^2 - 4).")
    return Funcion(texto, expr)


def interpretar_numero(texto, nombre_campo: str) -> float:
    """Convierte un campo numérico. Acepta '0,5', '1e-4', 'pi/2', 'sqrt(2)'..."""
    if texto is None or str(texto).strip() == "":
        raise ErrorFuncion(f"El campo «{nombre_campo}» es obligatorio.")
    if isinstance(texto, (int, float)) and not isinstance(texto, bool):
        valor = float(texto)
    else:
        limpio = _normalizar(str(texto)).replace(",", ".")
        try:
            valor = float(limpio)
        except ValueError:
            mensaje = f"«{nombre_campo}» debe ser un número (ej.: 2, -1.5, 0.0001, pi/2)."
            try:
                _validar_texto(limpio)
                expr = _parsear(limpio)
            except ErrorFuncion as exc:
                raise ErrorFuncion(mensaje) from exc
            if expr.free_symbols:
                raise ErrorFuncion(mensaje)
            try:
                valor = float(expr.evalf())
            except (TypeError, ValueError) as exc:
                raise ErrorFuncion(mensaje) from exc
    if not math.isfinite(valor):
        raise ErrorFuncion(f"«{nombre_campo}» debe ser un número finito.")
    return valor
