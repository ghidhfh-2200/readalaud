import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
import json
import pathlib
from queue import Empty

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
            return last_state
        except Exception as e:
            print(e)
            return {"message": "err: " + str(e)}

    uvicorn.run(app=fast_server, host="127.0.0.1", port=8008, limit_concurrency=20)
