from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import io
import requests
import time

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

last_call_time = 0


# ✅ OpenRouter AI
def get_ai_feedback(prompt: str):
    api_key = os.getenv("OPENROUTER_API_KEY")

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500
    }

    for _ in range(3):
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            try:
                return response.json()["choices"][0]["message"]["content"]
            except:
                return f"API Parse Error: {response.json()}"

        if response.status_code == 429:
            time.sleep(5)
        else:
            return f"API Error: {response.text}"

    return "AI temporarily unavailable"


@app.get("/")
def home():
    return {"message": "Backend is running"}


# ✅ ANALYZE ENDPOINT
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        global last_call_time

        if time.time() - last_call_time < 2:
            return {"error": "Too many requests. Wait a moment."}

        last_call_time = time.time()

        contents = await file.read()

        try:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        except:
            df = pd.read_csv(io.BytesIO(contents))

        # metrics
        avg_speed = float(df["speed"].mean()) if "speed" in df.columns else 0
        max_speed = float(df["speed"].max()) if "speed" in df.columns else 0
        avg_throttle = float(df["throttle"].mean()) if "throttle" in df.columns else 0
        avg_brake = float(df["brake"].mean()) if "brake" in df.columns else 0

        data_sample = df.head(5).to_string()

        prompt = f"""
You are a professional racing coach.

Analyze this telemetry.

Telemetry:
{data_sample}

Stats:
Avg Speed: {avg_speed}
Max Speed: {max_speed}
Throttle: {avg_throttle}
Brake: {avg_brake}

Respond EXACTLY in this format:

Summary:
...

Key Mistakes:
- ...
- ...

Advice:
- ...
- ...

Suggested Questions:
1. ...
2. ...
3. ...
"""

        feedback_text = get_ai_feedback(prompt)

        # debug fallback
        if "API Error" in feedback_text or "unavailable" in feedback_text.lower():
            return {"debug_error": feedback_text}

        # ✅ CLEAN TEXT
        clean_text = feedback_text.replace("\\n", "\n").replace("**", "")

        # ✅ SIMPLE LINE FORMAT (BEST FOR FRONTEND)
        feedback_lines = [
            line.strip()
            for line in clean_text.split("\n")
            if line.strip()
        ]

        return {
            "avg_speed": avg_speed,
            "max_speed": max_speed,
            "avg_throttle": avg_throttle,
            "avg_brake": avg_brake,
            "feedback": feedback_lines,   # 👈 MOST IMPORTANT FIX
            "raw_feedback": clean_text    # optional debug
        }

    except Exception as e:
        return {"error": str(e)}


# ✅ CHAT ENDPOINT (FIXES YOUR CHAT ERROR)
@app.post("/chat")
async def chat(body: dict):
    try:
        message = body.get("message", "")

        if not message:
            return {"error": "No message provided"}

        response = get_ai_feedback(message)

        if "API Error" in response or "unavailable" in response.lower():
            return {"error": response}

        return {"response": response}

    except Exception as e:
        return {"error": str(e)}