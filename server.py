# server.py - FastAPI Python code execution server
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import subprocess
import tempfile
import os
import sys
import resource
import asyncio

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

@app.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive_json()
    code = data.get("code", "")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        filename = f.name
    def set_limits():
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
    proc = await asyncio.create_subprocess_exec(
        "python3", filename,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=set_limits
    )
    async def read_stream(stream, stream_type):
        while True:
            line = await stream.readline()
            if not line:
                break
            await websocket.send_json({"type": stream_type, "data": line.decode()})
    stdout_task = asyncio.create_task(read_stream(proc.stdout, "stdout"))
    stderr_task = asyncio.create_task(read_stream(proc.stderr, "stderr"))
    try:
        while True:
            msg = await websocket.receive_text()
            proc.stdin.write(msg.encode())
            await proc.stdin.drain()
    except WebSocketDisconnect:
        proc.kill()
    finally:
        await stdout_task
        await stderr_task
        os.unlink(filename)
        await websocket.close()
