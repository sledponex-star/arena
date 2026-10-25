import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

# Настройка связи между сайтом и сервером (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Функция, которая идет на бесплатные внешние ресурсы за картинкой
async def fetch_free_horde_image(prompt: str, model_name: str) -> str:
    url = "https://aihorde.net"
    
    # Официальный анонимный бесплатный ключ, не требующий карт
    headers = {"apikey": "0000000000"} 
    
    payload = {
        "prompt": prompt,
        "params": {
            "steps": 20,
            "width": 1024,
            "height": 1024,
            "cfg_scale": 6,
            "nsfw": True  # Включаем пропуск взрослого контента
        },
        "models": [model_name]
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 1. Отправляем промпт волонтерам
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 202:
                return "https://placeholder.com"
                
            job_id = response.json()["id"]
            check_url = f"https://aihorde.net{job_id}"
            
            # 2. Ждем готовности (опрашиваем каждые 3 секунды)
            while True:
                await asyncio.sleep(3)
                status_res = await client.get(check_url)
                status_data = status_res.json()
                
                if status_data.get("done"):
                    # Возвращаем прямую ссылку на картинку с внешнего сервера
                    return status_data["generations"][0]["img"]
                elif status_data.get("faulted"):
                    return "https://placeholder.com"
        except Exception:
            return "https://placeholder.com"

# WebSocket-канал для быстрой связи с сайтом без таймаутов хостинга
@app.websocket("/ws/generate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Принимаем промпт от нашего index.html
            data = await websocket.receive_json()
            user_prompt = data.get("prompt")
            
            if not user_prompt:
                continue

            # Список отвязных бесплатных моделей в сети волонтеров
            free_models = ["PonyDiffusion", "Flux.1-Dev-Uncensored", "CyberRealistic_Pony", "DreamShaper_XL"]
            
            # Вслепую выбираем две разные модели для раунда
            selected = random.sample(free_models, 2)
            
            # Запускаем генерацию на двух разных ресурсах одновременно
            task_a = asyncio.create_task(fetch_free_horde_image(user_prompt, selected[0]))
            task_b = asyncio.create_task(fetch_free_horde_image(user_prompt, selected[1]))

            # Отправляем готовую картинку А на сайт, как только она догрузилась
            url_a = await task_a
            await websocket.send_json({"slot": "A", "url": url_a})

            # Отправляем картинку Б на сайт
            url_b = await task_b
            await websocket.send_json({"slot": "B", "url": url_b})

    except WebSocketDisconnect:
        print("User disconnected")
