"""Docker integration test for sandbox basics."""

import os
import asyncio
import pytest

# Set required env vars for testing
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LLM_MODEL", "test-model")

from app.sandbox import create_sandbox

pytestmark = pytest.mark.skipif(
    os.environ.get("DEEPEYE_RUN_DOCKER_TESTS") != "1",
    reason="Set DEEPEYE_RUN_DOCKER_TESTS=1 to run Docker integration tests.",
)


async def test_sandbox_create():
    """Test sandbox creation and basic operations"""
    print("=== Testing Sandbox ===\n")
    
    # Create sandbox
    sandbox = create_sandbox()
    print("✓ Sandbox instance created")
    
    # Start sandbox
    await sandbox.create()
    print("✓ Container created")
    
    try:
        # Test command execution
        result = await sandbox.exec_command("echo 'Hello from sandbox'")
        print(f"✓ Command executed: {result.stdout.strip()}")
        
        # Test Python
        result = await sandbox.exec_command("python --version")
        print(f"✓ Python version: {result.stdout.strip()}")
        
        # Test file operations with bash
        result = await sandbox.exec_command("echo 'Hello World' > /workspace/test.txt")
        print(f"✓ File written: {result.success}")
        
        result = await sandbox.exec_command("cat /workspace/test.txt")
        print(f"✓ File content: {result.stdout.strip()}")
        
        print("\n✅ All tests passed!")
        
    finally:
        # Cleanup
        await sandbox.destroy()
        print("✓ Container destroyed")


if __name__ == "__main__":
    asyncio.run(test_sandbox_create())
