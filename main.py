from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import io
import requests
import time

app = FastAPI()

# CORS (for Lovable frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⏱️ simple rate limiter
last_call_time = 0


# ✅ OpenRouter AI (STABLE)
def get_ai_feedback(prompt: str):
    api_key = os.getenv("OPENROUTER_API_KEY")

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct",  # ✅ reliable free model
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500
    }

    # 🔁 retry logic
    for attempt in range(3):
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            try:
                return result["choices"][0]["message"]["content"]
            except Exception:
                return f"API Parse Error: {result}"

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

        # ⏱️ cooldown
        if time.time() - last_call_time < 2:
            return {"error": "Too many requests. Wait a moment."}

        last_call_time = time.time()

        print("STEP 1: File received")

        contents = await file.read()

        try:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        except:
            df = pd.read_csv(io.BytesIO(contents))

        print("STEP 2: CSV parsed")

        # Metrics
        avg_speed = float(df["speed"].mean()) if "speed" in df.columns else 0
        max_speed = float(df["speed"].max()) if "speed" in df.columns else 0
        avg_throttle = float(df["throttle"].mean()) if "throttle" in df.columns else 0
        avg_brake = float(df["brake"].mean()) if "brake" in df.columns else 0

        # smaller sample = cheaper + faster
        data_sample = df.head(5).to_string()

        prompt = f"""
You are a professional racing coach analyzing driver telemetry.

Telemetry:
{data_sample}

Stats:
- Avg Speed: {avg_speed}
- Max Speed: {max_speed}
- Avg Throttle: {avg_throttle}
- Avg Brake: {avg_brake}

Return:
1. Summary
2. Key Mistakes
3. Advice
4. 3 Suggested Questions

Be concise and technical.
"""

        print("STEP 3: Calling AI")

        feedback_text = get_ai_feedback(prompt)

        print("STEP 4: AI response received")

        # debug if fails
        if "API Error" in feedback_text or "unavailable" in feedback_text.lower():
            return {"debug_error": feedback_text}

        feedback = [
            line.strip()
            for line in feedback_text.split("\n")
            if line.strip()
        ]

        return {
            "avg_speed": avg_speed,
            "max_speed": max_speed,
            "avg_throttle": avg_throttle,
            "avg_brake": avg_brake,
            "feedback": feedback
        }

    except Exception as e:
        return {"error": str(e)}