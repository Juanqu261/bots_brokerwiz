"""
MQTT statistics client for querying broker metrics.

Queries Mosquitto $SYS topics to get queue depth and broker health.
"""

import asyncio
import logging
from typing import Optional
from collections import defaultdict

import aiomqtt

from config.settings import settings

logger = logging.getLogger(__name__)


class MQTTStatsClient:
    """
    Client for querying MQTT broker statistics.
    
    Queries $SYS topics to get:
    - Queue depth (total and per aseguradora)
    - Broker health status
    - Connected clients count
    """
    
    def __init__(self, broker_host: Optional[str] = None, broker_port: Optional[int] = None):
        """
        Initialize MQTT stats client.
        
        Args:
            broker_host: MQTT broker hostname (default: from settings)
            broker_port: MQTT broker port (default: from settings)
        """
        self.broker_host = broker_host or settings.mqtt.MQTT_HOST
        self.broker_port = broker_port or settings.mqtt.MQTT_PORT
    
    async def get_queue_depth(self, timeout: float = 2.0) -> dict:
        """
        Query MQTT broker for message counts per topic.
        
        Args:
            timeout: Timeout in seconds for MQTT operations
        
        Returns:
            Dictionary with queue metrics:
            {
                "total_messages": int,
                "by_aseguradora": {"sbs": int, "hdi": int, ...}
            }
        """
        try:
            # Connect to broker with short timeout
            async with aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                identifier=f"stats-client-{asyncio.current_task().get_name()}",
                timeout=timeout
            ) as client:
                # Subscribe to $SYS topics for message counts
                await client.subscribe("$SYS/broker/messages/stored")
                await client.subscribe("$SYS/broker/subscriptions/count")
                
                # Collect messages with timeout
                total_messages = 0
                by_aseguradora = defaultdict(int)
                
                try:
                    async with asyncio.timeout(timeout):
                        async for message in client.messages:
                            topic = str(message.topic)
                            payload = message.payload.decode('utf-8')
                            
                            if topic == "$SYS/broker/messages/stored":
                                try:
                                    total_messages = int(payload)
                                except ValueError:
                                    pass
                                break  # Got what we need
                
                except asyncio.TimeoutError:
                    logger.debug("Timeout waiting for MQTT $SYS messages")
                
                # Note: Mosquitto doesn't provide per-topic message counts via $SYS
                # We return total only. Per-aseguradora would require custom tracking.
                return {
                    "total_messages": total_messages,
                    "by_aseguradora": dict(by_aseguradora)
                }
        
        except Exception as e:
            logger.warning(f"Error querying MQTT queue depth: {e}")
            return {
                "total_messages": -1,  # -1 indicates unavailable
                "by_aseguradora": {}
            }
    
    async def is_broker_healthy(self, timeout: float = 2.0) -> bool:
        """
        Check if MQTT broker is responsive.
        
        Args:
            timeout: Timeout in seconds for connection attempt
        
        Returns:
            True if broker responds to connection, False otherwise
        """
        try:
            async with asyncio.timeout(timeout):
                async with aiomqtt.Client(
                    hostname=self.broker_host,
                    port=self.broker_port,
                    identifier=f"health-check-{asyncio.current_task().get_name()}",
                    timeout=timeout
                ) as client:
                    # If we can connect, broker is healthy
                    return True
        
        except asyncio.TimeoutError:
            logger.warning(f"MQTT broker health check timeout ({timeout}s)")
            return False
        except Exception as e:
            logger.warning(f"MQTT broker health check failed: {e}")
            return False
    
    async def get_connected_clients(self, timeout: float = 2.0) -> int:
        """
        Get number of connected MQTT clients.
        
        Args:
            timeout: Timeout in seconds for MQTT operations
        
        Returns:
            Number of connected clients, or -1 if unavailable
        """
        try:
            async with aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                identifier=f"stats-client-{asyncio.current_task().get_name()}",
                timeout=timeout
            ) as client:
                await client.subscribe("$SYS/broker/clients/connected")
                
                try:
                    async with asyncio.timeout(timeout):
                        async for message in client.messages:
                            payload = message.payload.decode('utf-8')
                            try:
                                return int(payload)
                            except ValueError:
                                return -1
                
                except asyncio.TimeoutError:
                    logger.debug("Timeout waiting for connected clients count")
                    return -1
        
        except Exception as e:
            logger.warning(f"Error getting connected clients: {e}")
            return -1
