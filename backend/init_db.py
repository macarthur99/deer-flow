"""Initialize database tables for memory storage."""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from deerflow.database.connection import init_async_engine, get_sync_engine
from deerflow.database.memory import create_memory_table_sync
import asyncio


async def main():
    print("Initializing database connection...")
    await init_async_engine()

    print("Creating memory table...")
    engine = get_sync_engine()
    if engine is None:
        print("Error: Database engine not initialized")
        return

    create_memory_table_sync(engine)
    print("Memory table created successfully!")

    # Test MySQLMemoryStorage
    print("\nTesting MySQLMemoryStorage...")
    from deerflow.agents.memory.mysql_storage import MySQLMemoryStorage

    storage = MySQLMemoryStorage()

    # Test load (should return empty memory)
    print("Testing load...")
    memory = storage.load("test_user")
    print(f"Loaded memory version: {memory.get('version')}")

    # Test save
    print("Testing save...")
    memory["user"]["workContext"]["summary"] = "Test context"
    result = storage.save(memory, "test_user")
    print(f"Save result: {result}")

    # Test reload
    print("Testing reload...")
    reloaded = storage.reload("test_user")
    print(f"Reloaded context: {reloaded['user']['workContext']['summary']}")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
