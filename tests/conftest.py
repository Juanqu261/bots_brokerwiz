import sys
import asyncio
import pytest

# Fix for Windows: use SelectorEventLoop instead of ProactorEventLoop
if sys.platform == "win32":
    # Set the event loop policy BEFORE pytest-asyncio creates loops
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use SelectorEventLoop on Windows for aiomqtt compatibility."""
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()
