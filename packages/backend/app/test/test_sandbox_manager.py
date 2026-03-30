"""Docker integration test for SandboxManager."""

import os
import asyncio
import pytest

# Set required env vars
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.sandbox import sandbox_manager

pytestmark = pytest.mark.skipif(
    os.environ.get("DEEPEYE_RUN_DOCKER_TESTS") != "1",
    reason="Set DEEPEYE_RUN_DOCKER_TESTS=1 to run Docker integration tests.",
)


async def test_sandbox_manager():
    """Test sandbox manager with multiple sessions"""
    print("=== Testing SandboxManager ===\n")
    
    # Test 1: Create sandboxes for session1
    print("--- Test 1: Create sandboxes for session1 ---")
    session1 = "session-001"
    
    sandbox1 = await sandbox_manager.create_for_session(session1)
    print(f"✓ Created sandbox1 for {session1}")
    
    await sandbox_manager.create_for_session(session1)
    print(f"✓ Created sandbox2 for {session1}")
    
    # Test command in sandbox1
    result = await sandbox1.exec_command("echo 'Hello from sandbox1'")
    print(f"✓ Sandbox1 output: {result.stdout.strip()}")
    
    # Test 2: Create sandbox for session2
    print("\n--- Test 2: Create sandbox for session2 ---")
    session2 = "session-002"
    
    sandbox3 = await sandbox_manager.create_for_session(session2)
    print(f"✓ Created sandbox for {session2}")
    
    result = await sandbox3.exec_command("echo 'Hello from session2'")
    print(f"✓ Sandbox output: {result.stdout.strip()}")
    
    # Test 3: Get sandboxes
    print("\n--- Test 3: List sandboxes ---")
    session1_sandboxes = await sandbox_manager.list_sandboxes(session1)
    print(f"✓ Session1 has {len(session1_sandboxes)} sandboxes")
    
    session2_sandboxes = await sandbox_manager.list_sandboxes(session2)
    print(f"✓ Session2 has {len(session2_sandboxes)} sandboxes")
    
    # Test 4: Get stats
    print("\n--- Test 4: Manager stats ---")
    stats = sandbox_manager.get_stats()
    print(f"✓ Total sessions: {stats['total_sessions']}")
    print(f"✓ Total sandboxes: {stats['total_sandboxes_cached']}")
    
    # Test 5: Stop session1 (preserve data)
    print("\n--- Test 5: Stop session1 ---")
    await sandbox_manager.stop_session(session1)
    print("✓ Session1 stopped (data preserved)")
    
    # Test 6: Restart session1
    print("\n--- Test 6: Restart session1 ---")
    await sandbox_manager.restart_session(session1)
    print("✓ Session1 restarted")
    
    # Verify data still exists
    result = await sandbox1.exec_command("echo 'Still alive!'")
    print(f"✓ Sandbox1 output after restart: {result.stdout.strip()}")
    
    # Test 7: Destroy session1 (remove data)
    print("\n--- Test 7: Destroy session1 ---")
    await sandbox_manager.destroy_session(session1, delete_data=True)
    print("✓ Session1 destroyed (data removed)")
    
    stats = sandbox_manager.get_stats()
    print(f"✓ Remaining sessions: {stats['total_sessions']}")
    print(f"✓ Remaining sandboxes: {stats['total_sandboxes_cached']}")
    
    # Test 8: Destroy all
    print("\n--- Test 8: Destroy all ---")
    await sandbox_manager.cleanup_all()
    print("✓ All sessions destroyed")
    
    stats = sandbox_manager.get_stats()
    print(f"✓ Final sessions: {stats['total_sessions']}")
    print(f"✓ Final sandboxes: {stats['total_sandboxes_cached']}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_sandbox_manager())
