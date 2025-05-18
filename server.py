# server.py - FastAPI Python code execution server
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import subprocess
import tempfile
import os
import sys
import resource

app = FastAPI()

@app.post("/execute")
async def execute_code(request: Request):
    data = await request.json()
    code = data.get("code", "")
    user_input = data.get("input", "")
    if not isinstance(code, str):
        return JSONResponse({"error": "Missing code"}, status_code=400)
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            filename = f.name
        # Function to set resource limits (memory, CPU time)
        def set_limits():
            # Limit CPU time to 5 seconds
            resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
            # Limit memory to 100MB
            resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
        # Run the code with input, capture output and errors
        proc = subprocess.Popen(
            ["python3", filename],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=set_limits  # Set resource limits in child process
        )
        try:
            stdout, stderr = proc.communicate(input=user_input, timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            return JSONResponse({"stdout": "", "stderr": "Timeout expired", "exitCode": -1}, status_code=200)
        finally:
            os.unlink(filename)
        return JSONResponse({"stdout": stdout, "stderr": stderr, "exitCode": proc.returncode}, status_code=200)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
