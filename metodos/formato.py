"""Funciones para mostrar números de forma consistente (tabla, procedimiento, PDF y Excel)."""
from __future__ import annotations


def fmt(valor: float | None, decimales: int = 6) -> str:
    """Formatea un número con `decimales` cifras; usa notación científica si es muy pequeño o grande."""
    if valor is None:
        return "—"
    if valor == 0:
        return f"{0:.{decimales}f}"
    if abs(valor) < 10 ** (-decimales) or abs(valor) >= 1e10:
        return f"{valor:.{max(decimales - 2, 2)}e}"
    return f"{valor:.{decimales}f}"


def fmt_par(valor: float | None, decimales: int = 6) -> str:
    """Igual que fmt pero pone entre paréntesis los negativos (útil al sustituir en fórmulas)."""
    texto = fmt(valor, decimales)
    return f"({texto})" if valor is not None and valor < 0 else texto


def fmt_latex(valor: float | None, decimales: int = 6) -> str:
    """Versión LaTeX: convierte 1.23e-05 en 1.23 \\times 10^{-5}."""
    texto = fmt(valor, decimales)
    if "e" in texto:
        mantisa, exponente = texto.split("e")
        texto = f"{mantisa} \\times 10^{{{int(exponente)}}}"
    return texto


def fmt_latex_par(valor: float | None, decimales: int = 6) -> str:
    texto = fmt_latex(valor, decimales)
    return f"\\left({texto}\\right)" if valor is not None and valor < 0 else texto
