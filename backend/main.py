import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

from prompts import SCAM_DETECTION_SYSTEM_PROMPT


class AnalyzeRequest(BaseModel):
    transcript: str
    call_duration_seconds: float = 0


class AnalyzeResponse(BaseModel):
    score: int
    reasoning: str
    red_flags: list[str]
    recommendation: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    if not req.transcript or len(req.transcript.strip()) < 10:
        return AnalyzeResponse(
            score=0,
            reasoning="Not enough text to analyze",
            red_flags=[],
            recommendation="SAFE",
        )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=SCAM_DETECTION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyze this phone call transcript for scam indicators:\n\n{req.transcript}",
                }
            ],
        )
        result = json.loads(response.content[0].text)
        score = int(result.get("score", 0))
        if score <= 3:
            rec = "SAFE"
        elif score <= 6:
            rec = "CAUTION"
        else:
            rec = "END CALL NOW"
        return AnalyzeResponse(
            score=score,
            reasoning=result.get("reasoning", "Analysis complete"),
            red_flags=result.get("red_flags", []),
            recommendation=rec,
        )
    except Exception as e:
        print(f"Analysis error: {e}")
        return AnalyzeResponse(
            score=0,
            reasoning="Analysis temporarily unavailable",
            red_flags=[],
            recommendation="SAFE",
        )
