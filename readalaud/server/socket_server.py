"""
socket_server.py —— FastAPI HTTP 端点 + WebSocket 音频流接收。
"""
import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket
import json
import pathlib
import wave
import os
import mimetypes
from ..logger.log_manager import log_system
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')


def bind_server_api(instance):
    instance.start_server = lambda: start_socket_server(instance)


def start_socket_server(queue=None):
    log_system("启动 Socket 服务器", "start_socket_server called")
    fast_server = fastapi.FastAPI(debug=False, redoc_url=None, docs_url=None)
    project_root = pathlib.Path(__file__).resolve().parent.parent.parent
    web_dir = project_root / "web"

    fast_server.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if web_dir.exists():
        # 挂载后，比如通过 http://127.0.0.1:8008/web/audio_visualizer.html 即可访问静态文件
        fast_server.mount("/web", StaticFiles(directory=str(web_dir), html=True), name="web")
        log_system("挂载静态目录", str(web_dir))

    @fast_server.get("/bootstrap.min.css", include_in_schema=False)
    async def bootstrap_css():
        css_path = web_dir / "bootstrap.min.css"
        if css_path.exists():
            return FileResponse(str(css_path), media_type="text/css")
        return JSONResponse(status_code=404, content={"message": "bootstrap.min.css not found"})

    last_state = {}

    @fast_server.post("/get_state")
    async def show_test(data: dict):
        try:
            print("/get_state received:", data)
            last_state["broadcast"] = data
            if queue is not None:
                queue.put({"broadcast": data})
            return {"message": "ok"}
        except Exception as e:
            log_system("/get_state 异常", str(e))
            print(e)
            return {"message": "err: " + str(e)}

    @fast_server.post("/get_temp")
    async def get_temp():
        project_root = pathlib.Path(__file__).resolve().parent.parent.parent
        temp_path = project_root / "temp.json"
        try:
            with open(str(temp_path), encoding="utf-8") as f:
                read_data = json.load(f)
            return read_data
        except Exception as e:
            log_system("/get_temp 异常", str(e))
            print(e)
            return {"message": "err: " + str(e)}

    @fast_server.post("/end_reading")
    async def end_reading():
        print("get_ended")
        log_system("收到结束朗读请求", "POST /end_reading")
        last_state["end_sig"] = True
        if queue is not None:
            queue.put({"end_sig": True})
        return {"msg": "ok"}

    @fast_server.get("/poll")
    async def poll_state():
        try:
            result = dict(last_state)
            if "end_sig" in last_state:
                del last_state["end_sig"]
            return result
        except Exception as e:
            log_system("/poll 异常", str(e))
            print(e)
            return {"message": "err: " + str(e)}

    @fast_server.websocket("/audio_stream")
    async def audio_receive(websocket: WebSocket):
        await websocket.accept()
        log_system("音频 WebSocket 已连接", "/audio_stream accepted")

        SAMPLE_RATE = 44100
        CHANNELS = 1
        SAMPLE_WIDTH = 2
        CHUNK_SECONDS = 60
        BYTES_PER_CHUNK = SAMPLE_RATE * SAMPLE_WIDTH * CHUNK_SECONDS * CHANNELS

        output_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "audio_chunks"
        output_dir.mkdir(parents=True, exist_ok=True)

        read_file_name = os.listdir(output_dir)
        index_list = []
        if read_file_name:
            for name in read_file_name:
                try:
                    index_list.append(int(name.split("_")[1].split(".")[0]))
                except Exception:
                    pass
            index_list.sort()
            chunk_index = index_list[-1] + 1 if index_list else 0
        else:
            chunk_index = 0
        current_buffer = bytearray()

        try:
            while True:
                data = await websocket.receive_bytes()
                current_buffer.extend(data)
                while len(current_buffer) >= BYTES_PER_CHUNK:
                    chunk_data = current_buffer[:BYTES_PER_CHUNK]
                    output_file = output_dir / f"chunk_{chunk_index}.wav"
                    with wave.open(str(output_file), "wb") as wav_file:
                        wav_file.setnchannels(CHANNELS)
                        wav_file.setsampwidth(SAMPLE_WIDTH)
                        wav_file.setframerate(SAMPLE_RATE)
                        wav_file.writeframes(chunk_data)
                    print(f"Saved chunk: {output_file}")
                    del current_buffer[:BYTES_PER_CHUNK]
                    chunk_index += 1
        except Exception as e:
            log_system("音频 WebSocket 连接关闭", str(e))
            print(f"WebSocket connection closed: {e}")
        finally:
            if len(current_buffer) > 0:
                output_file = output_dir / f"chunk_{chunk_index}.wav"
                with wave.open(str(output_file), "wb") as wav_file:
                    wav_file.setnchannels(CHANNELS)
                    wav_file.setsampwidth(SAMPLE_WIDTH)
                    wav_file.setframerate(SAMPLE_RATE)
                    wav_file.writeframes(current_buffer)
                print(f"Saved final chunk: {output_file}")
                log_system("保存最后音频分块", str(output_file))
            try:
                await websocket.close()
            except Exception:
                pass

    log_system("运行 Uvicorn", "127.0.0.1:8008")
    uvicorn.run(app=fast_server, host="127.0.0.1", port=8008, limit_concurrency=20)
