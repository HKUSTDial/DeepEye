"""
Sandbox Protocol Definition

Defines the minimal interface for sandbox implementations. Concrete runtimes
such as Docker, E2B, or Daytona should live outside the core package and satisfy
this protocol.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class CommandResult:
    """Result from executing a command in sandbox."""
    stdout: str
    stderr: str
    exit_code: int
    success: bool = True
    execution_time_ms: int = 0
    
    def __post_init__(self):
        """Auto-calculate success from exit_code if not explicitly set."""
        self.success = (self.exit_code == 0)


@runtime_checkable
class SandboxProtocol(Protocol):
    """
    Sandbox protocol for agent tools.
    
    Required methods:
        - create():       Create and start the sandbox
        - stop():         Stop the sandbox (preserve data)
        - start():        Start a stopped sandbox
        - destroy():      Destroy the sandbox and clean up resources
        - exec_command(): Execute command in sandbox
    """

    async def exec_command(self, command: str) -> CommandResult:
        """
        Execute a command in the sandbox.
        
        Args:
            command: Shell command to execute
            
        Returns:
            CommandResult with success, exit_code, stdout, stderr
        """
        ...

    async def create(self) -> None:
        """
        Creates and starts the sandbox instance.
        
        Implementation requirements:
        - Allocate resources (container/VM/cloud instance)
        - Start the runtime
        - Wait until ready
        
        Raises:
            RuntimeError: If creation fails
        """
        ...

    async def stop(self) -> None:
        """
        Stops the sandbox instance, preserving its state and data.
        
        Implementation requirements:
        - Stop the runtime
        - Ensure resources are not actively consumed but data persists
        - Idempotent operation
        """
        ...

    async def start(self) -> None:
        """
        Starts a previously stopped sandbox instance.
        
        Implementation requirements:
        - Resume the runtime from its preserved state
        - Wait until ready
        
        Raises:
            RuntimeError: If starting fails or sandbox is not in a stoppable state
        """
        ...

    async def destroy(self) -> None:
        """
        Destroys the sandbox and cleans up all associated resources.
        
        Implementation requirements:
        - Stop the runtime
        - Release all resources
        - Clean up temporary files and persistent data
        - Idempotent operation
        """
        ...
