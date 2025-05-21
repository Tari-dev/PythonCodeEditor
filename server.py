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
        "python3", "-u", filename,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=set_limits
    )
    async def read_stream(stream, stream_type):
        while True:
            chunk = await stream.read(64)  # Read up to 64 bytes at a time
            if not chunk:
                break
            await websocket.send_json({"type": stream_type, "data": chunk.decode(errors='replace')})
    stdout_task = asyncio.create_task(read_stream(proc.stdout, "stdout"))
    stderr_task = asyncio.create_task(read_stream(proc.stderr, "stderr"))
    proc_wait_task = asyncio.create_task(proc.wait())
    try:
        while True:
            input_task = asyncio.create_task(websocket.receive_text())
            done, pending = await asyncio.wait(
                [input_task, proc_wait_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            if proc_wait_task in done:
                if not input_task.done():
                    input_task.cancel()
                break
            if input_task in done:
                try:
                    msg = input_task.result()
                except asyncio.CancelledError:
                    break
                if proc.stdin.is_closing():
                    break
                proc.stdin.write(msg.encode())
                await proc.stdin.drain()
    except WebSocketDisconnect:
        proc.kill()
    finally:
        await stdout_task
        await stderr_task
        os.unlink(filename)
        if not websocket.client_state.name == 'DISCONNECTED':
            await websocket.close()
