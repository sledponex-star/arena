import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Быстрый бесплатный ИИ-шлюз через демонстрационные сервера
async def fetch_fast_free_image(prompt: str, provider_id: int) -> str:
    # Используем разные стабильные бесплатные эндпоинты для создания слепого теста
    endpoints = [
        "https://hf.space",
        "https://hf.space"
    ]
    url = endpoints[provider_id % len(endpoints)]
    
    payload = {
        "data": [
            prompt,
            1,     # seed
            True,  # randomize_seed
            1024,  # width
            1024,  # height
            4,     # num_inference_steps
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                # Извлекаем готовую картинку, которую сервер сгенерировал за пару секунд
                if "data" in data and len(data["data"]) > 0:
                    return data["data"][0]  # Возвращает base64 или прямую ссылку
            return "https://placeholder.com"
    except Exception:
        return "https://placeholder.com"

@app.websocket("/ws/generate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_prompt = data.get("prompt")
            
            if not user_prompt:
                continue

            # Запускаем две быстрые параллельные генерации вслепую
            task_a = asyncio.create_task(fetch_fast_free_image(user_prompt, 0))
            task_b = asyncio.create_task(fetch_fast_free_image(user_prompt, 1))

            url_a = await task_a
            await websocket.send_json({"slot": "A", "url": url_a})

            url_b = await task_b
            await websocket.send_json({"slot": "B", "url": url_b})

    except WebSocketDisconnect:
        print("User disconnected")
