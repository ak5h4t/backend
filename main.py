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
You are an elite professional racing coach analyzing driver telemetry.

Your job is to provide deep, actionable performance insights.

Analyze the data and return:

1. Overall Performance Summary
2. Key Mistakes (specific driving issues)
3. Performance Metrics Insights (speed, braking, throttle, consistency)
4. Actionable Coaching Advice (clear steps to improve)
5. Suggested Driver Questions (3 smart follow-up questions)

Telemetry Data:
{data}

Rules:
- Be specific and technical
- Do NOT be generic
- Focus on improving lap time and consistency
- Use structured sections
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