"""
Bots - Implementaciones de bots de cotización por aseguradora.

Exports:
- BaseBot: Clase base que orquesta Selenium y HTTP
- (Bots específicos se agregarán aquí conforme se implementen)
"""

from workers.bots.base_bot import BaseBot

__all__ = [
    "BaseBot",
]
