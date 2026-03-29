from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import io
import google.generativeai as genai

app = FastAPI()

# CORS (for Lovable frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash-latest")


@app.get("/")
def home():
    return {"message": "Backend is running"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        print("STEP 1: File received")

        # Read file safely
        contents = await file.read()
        print("STEP 2: File read")

        # Parse CSV safely
        try:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        except Exception:
            df = pd.read_csv(io.BytesIO(contents))

        print("STEP 3: CSV parsed")

        # Basic metrics (safe access)
        avg_speed = float(df["speed"].mean()) if "speed" in df.columns else 0
        max_speed = float(df["speed"].max()) if "speed" in df.columns else 0
        avg_throttle = float(df["throttle"].mean()) if "throttle" in df.columns else 0
        avg_brake = float(df["brake"].mean()) if "brake" in df.columns else 0

        # Prepare data sample
        data = df.head(20).to_string()
        print("STEP 4: Data prepared")

        # Prompt
        prompt = f"""
You are an elite professional racing coach analyzing driver telemetry.

Telemetry Sample:
{data}

Stats:
- Avg Speed: {avg_speed}
- Max Speed: {max_speed}
- Avg Throttle: {avg_throttle}
- Avg Brake: {avg_brake}

Return structured insights:

Summary:
Key Mistakes:
Advice:
Suggested Questions:

Be specific, technical, and actionable.
"""

        print("STEP 5: Calling Gemini")

        # Gemini call
        response = model.generate_content(prompt)

        print("STEP 6: Gemini response received")

        feedback_text = response.text if response and response.text else "No response from AI"

        # Clean output
        feedback = [line.strip() for line in feedback_text.split("\n") if line.strip()]

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