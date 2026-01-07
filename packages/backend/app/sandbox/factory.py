"""Sandbox Factory - Create sandbox instances from config"""

from app.core.config import settings
from deepeye.sandbox import SandboxProtocol
from app.sandbox.docker_sandbox import DockerSandbox


def create_sandbox(sandbox_type: str | None = None) -> SandboxProtocol:
    """
    Create sandbox instance from config.
    
    Args:
        sandbox_type: Sandbox type ("docker", "e2b", "daytona")
                     Uses SANDBOX_TYPE from config if None
        
    Returns:
        SandboxProtocol instance
        
    Raises:
        ValueError: Unknown sandbox type
        NotImplementedError: Type not implemented yet
    """
    sandbox_type = sandbox_type or settings.SANDBOX_TYPE

    if sandbox_type == "docker":
        return DockerSandbox()

    elif sandbox_type == "e2b":
        raise NotImplementedError("E2B sandbox not implemented. Use SANDBOX_TYPE=docker")

    elif sandbox_type == "daytona":
        raise NotImplementedError("Daytona sandbox not implemented. Use SANDBOX_TYPE=docker")

    else:
        raise ValueError(f"Unknown sandbox type: {sandbox_type}")

