"""
Bots - Implementaciones de bots de cotización por aseguradora.

Exports:
- BaseBot: Clase base que orquesta Selenium y HTTP
- HDIBot: Bot para HDI Seguros
"""

from workers.bots.base_bot import BaseBot
from workers.bots.hdi_bot import HDIBot

__all__ = [
    "BaseBot",
    "HDIBot",
]
