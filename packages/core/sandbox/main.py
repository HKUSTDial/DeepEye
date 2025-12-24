from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import io
import contextlib
import traceback
import os
import time

app = FastAPI()

class CodeExecutionRequest(BaseModel):
    code: str

class CodeExecutionResponse(BaseModel):
    output: str
    error: str | None

@app.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    start_time = time.time()
    os.environ.setdefault("MPLBACKEND", "Agg")
    code = request.code
    output_buffer = io.StringIO()
    error_message = None

    try:
        # Redirect stdout to capture print statements
        with contextlib.redirect_stdout(output_buffer):
            # Execute the code
            # We use a shared dictionary for local variables to persist state if needed,
            # but for now let's keep it stateless per request or use a global dict if we want a session.
            # To be safe and simple: stateless execution.
            exec_globals = {}
            exec(code, exec_globals)

    except Exception:
        error_message = traceback.format_exc()
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    print(f"[sandbox] execute done elapsed_ms={elapsed_ms} output_bytes={len(output_buffer.getvalue())} error={error_message is not None}")
    return CodeExecutionResponse(
        output=output_buffer.getvalue(),
        error=error_message,
    )

@app.get("/health")
async def health():
    return {"status": "ok"}

