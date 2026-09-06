class LoxError(Exception):
    """Error base de todo el intérprete."""


class ScanError(LoxError):
    """Error ocurrido durante el escaneo (análisis léxico)."""


class ParseError(LoxError):
    """Error ocurrido durante el parseo (análisis sintáctico)."""