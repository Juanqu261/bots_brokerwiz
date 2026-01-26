"""
Bots - Implementaciones de bots de cotización por aseguradora.

Exports:
- BaseBot: Clase base que orquesta Selenium y HTTP
- HDIBot: Bot para HDI Seguros
- BotExecutionLogger: Logger específico por ejecución
- cleanup_old_bot_logs: Limpieza de logs viejos
"""

from workers.bots.base_bot import BaseBot
from workers.bots.hdi_bot import HDIBot
from workers.bots.bot_logger import BotExecutionLogger, cleanup_old_bot_logs

__all__ = [
    "BaseBot",
    "HDIBot",
    "BotExecutionLogger",
    "cleanup_old_bot_logs",
]
