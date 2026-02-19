import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket
import json
import pathlib
from pydub import AudioSegment
from pydub.utils import make_chunks
import wave 
import os

def bind_server_api(instance):
    instance.start_server = lambda:start_socket_server(instance)

def start_socket_server(queue=None):
    fast_server = fastapi.FastAPI(debug=False, redoc_url=None, docs_url=None)

    fast_server.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局状态缓存，供/poll和轮询线程读取
    last_state = {}

    @fast_server.post("/get_state")
    async def show_test(data: dict):
        try:
            print("/get_state received:", data)
            # 更新全局状态
            last_state["broadcast"] = data
            # 如果有IPC队列，仅put，不get/put
            if queue is not None:
                queue.put({"broadcast": data})
            return {"message": "ok"}
        except Exception as e:
            print(e)
            return {"message": "err: " + str(e)}

    @fast_server.post("/get_temp")
    async def get_temp():
        project_root = pathlib.Path(__file__).resolve().parent.parent
        temp_path = project_root / "temp.json"
        try:
            with open(str(temp_path), encoding="utf-8") as f:
                read_data = json.load(f)
            return read_data
        except Exception as e:
            print(e)
            return {"message": "err: " + str(e)}

    @fast_server.post("/end_reading")
    async def end_reading():
        print("get_ended")
        last_state["end_sig"] = True
        if queue is not None:
            queue.put({"end_sig": True})
        print("end_reading updated last_state and queue")
        return {"msg": "ok"}

    @fast_server.get("/poll")
    async def poll_state():
        try:
            result = dict(last_state)
            # end_sig 只返回一次，读取后立即清除，避免后续轮询重复触发结束流程
            if "end_sig" in last_state:
                del last_state["end_sig"]
            return result
        except Exception as e:
            print(e)
            return {"message": "err: " + str(e)}

    @fast_server.websocket("/audio_stream")
    async def audio_receive(websocket: WebSocket):
        await websocket.accept()
        
        # Audio Configuration
        SAMPLE_RATE = 44100
        CHANNELS = 1
        SAMPLE_WIDTH = 2 # 16-bit
        CHUNK_SECONDS = 60 # 1 minute
        
        # Calculate bytes per chunk
        BYTES_PER_CHUNK = SAMPLE_RATE * SAMPLE_WIDTH * CHUNK_SECONDS * CHANNELS
        
        output_dir = pathlib.Path(__file__).resolve().parent.parent / "audio_chunks"
        output_dir.mkdir(exist_ok=True)
        
        read_file_name = os.listdir(output_dir)
        index_list = []
        print("read_file_name:"+ str(read_file_name))
        if read_file_name != []:
            for i in range(len(read_file_name)):
                index_list.append(int(read_file_name[i].split("_")[1].split(".")[0]))
            index_list.sort()
            chunk_index = index_list[len(index_list) - 1] + 1
        else:
            chunk_index = 0
        current_buffer = bytearray()
        

        try:
            while True:
                # Receive binary audio data from the WebSocket
                data = await websocket.receive_bytes()
                current_buffer.extend(data)

                # Check if the buffer has reached the threshold
                while len(current_buffer) >= BYTES_PER_CHUNK:
                    # Extract the chunk data
                    chunk_data = current_buffer[:BYTES_PER_CHUNK]
                    
                    # Save the chunk to a WAV file
                    output_file = output_dir / f"chunk_{chunk_index}.wav"
                    with wave.open(str(output_file), "wb") as wav_file:
                        wav_file.setnchannels(CHANNELS)
                        wav_file.setsampwidth(SAMPLE_WIDTH)
                        wav_file.setframerate(SAMPLE_RATE)
                        wav_file.writeframes(chunk_data)
                    print(f"Saved chunk: {output_file}")
                    
                    # Remove from buffer
                    del current_buffer[:BYTES_PER_CHUNK]
                    chunk_index += 1

        except Exception as e:
            print(f"WebSocket connection closed: {e}")
        finally:
            # Save any remaining audio data when the connection is closed
            if len(current_buffer) > 0:
                output_file = output_dir / f"chunk_{chunk_index}.wav"
                with wave.open(str(output_file), "wb") as wav_file:
                    wav_file.setnchannels(CHANNELS)
                    wav_file.setsampwidth(SAMPLE_WIDTH)
                    wav_file.setframerate(SAMPLE_RATE)
                    wav_file.writeframes(current_buffer)
                print(f"Saved final chunk: {output_file}")

            try:
                await websocket.close()
            except:
                pass
    uvicorn.run(app=fast_server, host="127.0.0.1", port=8008, limit_concurrency=20)
