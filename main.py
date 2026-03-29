from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import io
from openai import OpenAI

app = FastAPI()

# Allow all origins (for Lovable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        except:
            df = pd.read_csv(io.BytesIO(contents))

        print("STEP 3: CSV parsed")

        # Basic metrics (safe access)
        avg_speed = float(df["speed"].mean()) if "speed" in df.columns else 0
        max_speed = float(df["speed"].max()) if "speed" in df.columns else 0
        avg_throttle = float(df["throttle"].mean()) if "throttle" in df.columns else 0
        avg_brake = float(df["brake"].mean()) if "brake" in df.columns else 0

        # Prepare data sample for AI
        data = df.head(20).to_string()
        print("STEP 4: Data prepared")

        # AI prompt
        prompt = f"""
You are an elite professional racing coach analyzing driver telemetry.

Telemetry Sample:
{data}

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

Be specific and technical.
"""

        print("STEP 5: Calling OpenAI")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        print("STEP 6: OpenAI response received")

        feedback_text = response.choices[0].message.content

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