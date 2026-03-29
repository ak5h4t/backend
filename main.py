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


# ✅ Gemini HTTP function (robust + retry + safe parsing)
def get_ai_feedback(prompt: str):
    api_key = os.getenv("GEMINI_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    # 🔁 retry logic
    for attempt in range(3):
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()

            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                return f"API Parse Error: {result}"

        # ⏳ handle rate limit
        if response.status_code == 429:
            time.sleep(5)
        else:
            return f"API Error: {response.text}"

    return "AI temporarily unavailable (rate limit)"


@app.get("/")
def home():
    return {"message": "Backend is running"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        global last_call_time

        # ⏱️ basic cooldown protection
        if time.time() - last_call_time < 3:
            return {"error": "Too many requests. Please wait a few seconds."}

        last_call_time = time.time()

        print("STEP 1: File received")

        # Read file
        contents = await file.read()
        print("STEP 2: File read")

        # Parse CSV safely
        try:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        except Exception:
            df = pd.read_csv(io.BytesIO(contents))

        print("STEP 3: CSV parsed")

        # Metrics (safe)
        avg_speed = float(df["speed"].mean()) if "speed" in df.columns else 0
        max_speed = float(df["speed"].max()) if "speed" in df.columns else 0
        avg_throttle = float(df["throttle"].mean()) if "throttle" in df.columns else 0
        avg_brake = float(df["brake"].mean()) if "brake" in df.columns else 0

        # 🔥 reduce token usage
        data_sample = df.head(5).to_string()

        print("STEP 4: Data prepared")

        # ✅ optimized prompt
        prompt = f"""
You are a professional racing coach.

Telemetry:
{data_sample}

Stats:
Avg Speed: {avg_speed}
Max Speed: {max_speed}
Throttle: {avg_throttle}
Brake: {avg_brake}

Give:
- Summary
- Mistakes
- Advice
- 3 Questions

Be concise and technical.
"""

        print("STEP 5: Calling Gemini API")

        feedback_text = get_ai_feedback(prompt)

        print("STEP 6: Gemini response received")

        # ✅ DEBUG MODE (FIXED INDENTATION)
        if "API Error" in feedback_text or "unavailable" in feedback_text.lower():
            return {
                "debug_error": feedback_text
            }

        # ✅ normal flow
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
        print("ERROR:", str(e))
        return {"error": str(e)}