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

        # ✅ PARSE SECTIONS
        sections = [s.strip() for s in clean_text.split("\n\n") if s.strip()]

        # ✅ SAFE STRUCTURED OUTPUT
        def safe_get(index):
            return sections[index] if index < len(sections) else ""

        return {
            "avg_speed": avg_speed,
            "max_speed": max_speed,
            "avg_throttle": avg_throttle,
            "avg_brake": avg_brake,

            # 🔥 CLEAN STRUCTURED DATA (BEST FOR UI)
            "summary": safe_get(0),
            "mistakes": safe_get(1),
            "advice": safe_get(2),
            "questions": safe_get(3),

            # optional fallback (for debugging / raw display)
            "raw_feedback": clean_text
        }

    except Exception as e:
        return {"error": str(e)}