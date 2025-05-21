# server.py - FastAPI Python code execution server
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import subprocess
import tempfile
import os
import sys
import resource
import asyncio
from docker import from_env as docker_from_env
from docker.errors import DockerException

app = FastAPI()


@app.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive_json()
    code = data.get("code", "")
    docker = docker_from_env()
    container = None
    filename = None
    websocket_closed = False  # Track if websocket is closed
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(code)
            filename = f.name
        container = docker.containers.run(
            image="python:3.11-slim",
            command=["python", "-u", filename],
            network_mode="none",
            mem_limit="100m",
            pids_limit=10,
            read_only=True,
            tmpfs={"/tmp": ""},
            detach=True,
            stdin_open=True,
            tty=True,  # <-- changed from False to True
            volumes={filename: {'bind': filename, 'mode': 'ro'}},
        )
        sock = container.attach_socket(params={"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1})
        sock._sock.setblocking(True)
        loop = asyncio.get_event_loop()
        stop_flag = False
        process_running = True
        async def read_from_container():
            nonlocal websocket_closed, process_running
            while not stop_flag:
                data = await loop.run_in_executor(None, sock._sock.recv, 4096)
                if not data:
                    break
                try:
                    if not websocket_closed:
                        await websocket.send_json({"type": "stdout", "data": data.decode(errors='replace')})
                except Exception:
                    websocket_closed = True
                    break
            process_running = False  # Mark process as not running

        async def read_from_websocket():
            nonlocal websocket_closed, process_running
            # Add a small delay to ensure process is ready for input
            await asyncio.sleep(0.1)
            while not stop_flag and not websocket_closed:
                try:
                    msg = await websocket.receive_text()
                    if process_running:
                        sock._sock.send(msg.encode())
                except Exception:
                    websocket_closed = True
                    break

        async def monitor_container():
            nonlocal stop_flag, websocket_closed, process_running
            exit_code = await loop.run_in_executor(None, lambda: container.wait(timeout=10).get('StatusCode', 1))
            stop_flag = True
            process_running = False
            try:
                if not websocket_closed:
                    await websocket.send_json({"type": "exit", "data": exit_code})
            except Exception:
                websocket_closed = True
            try:
                sock._sock.close()
            except Exception:
                pass
            try:
                if not websocket_closed:
                    await websocket.close()
            except Exception:
                pass
            websocket_closed = True

        await asyncio.gather(
            read_from_container(),
            read_from_websocket(),
            monitor_container()
        )
        # Removed old exit_code logic here, now handled in monitor_container
    except DockerException as e:
        try:
            if not websocket_closed:
                await websocket.send_json({"type": "error", "data": str(e)})
        except Exception:
            websocket_closed = True
    except WebSocketDisconnect:
        websocket_closed = True
        pass
    finally:
        stop_flag = True
        if container:
            try:
                container.kill()
                container.remove()
            except:
                pass
        if filename and os.path.exists(filename):
            os.unlink(filename)
        try:
            if not websocket_closed:
                await websocket.close()
        except Exception:
            pass
