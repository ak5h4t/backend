from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    feedback = []

    if avg_brake > 0.3:
        feedback.append("You are braking too much. Try braking later.")

    if avg_throttle < 0.5:
        feedback.append("You are not accelerating enough out of corners.")

    if avg_speed < 80:
        feedback.append("Your overall speed is low. Focus on carrying more speed.")

    if not feedback:
        feedback.append("Great driving! Keep pushing your limits.")

    return {
        "avg_speed": float(avg_speed),
        "max_speed": float(max_speed),
        "feedback": feedback
    }