from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
def home():
    return {"message": "Backend is running"}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)

    avg_speed = df["speed"].mean()
    max_speed = df["speed"].max()
    avg_throttle = df["throttle"].mean()
    avg_brake = df["brake"].mean()

    prompt = f"""
You are a professional racing coach.

Telemetry:
- Avg speed: {avg_speed:.2f}
- Max speed: {max_speed:.2f}
- Throttle: {avg_throttle:.2f}
- Brake: {avg_brake:.2f}

Give 3 short, actionable tips.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    feedback_text = response.choices[0].message.content
    feedback = [line.strip() for line in feedback_text.split("\n") if line.strip()]

    return {
        "avg_speed": float(avg_speed),
        "max_speed": float(max_speed),
        "feedback": feedback
    }