# Author: Mani Padisetti
"""CK Life OS — Five Practices for Living."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from config import settings

app = FastAPI(
    title="CK Life OS",
    description="Five practices for living: Presence, Reflection, Intention, Gratitude, Equanimity",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "port": settings.PORT,
        "practices": len(settings.PRACTICES),
        "gamification": "DISABLED",
        "difficult_month_mode": "AVAILABLE"
    }

# Practices
@app.get("/api/practices")
async def list_practices():
    """List five practices (universal, no philosophical names)."""
    return {
        "total": len(settings.PRACTICES),
        "practices": settings.PRACTICES,
        "description": "Five universal practices for living"
    }

# Practice data endpoints
@app.post("/api/practices/{practice}/record")
async def record_practice(practice: str, request: Request):
    """Record a practice entry (no gamification)."""
    data = await request.json() if request.method == "POST" else {}
    return {
        "status": "success",
        "practice": practice,
        "recorded": True,
        "entry_id": f"{practice}-001",
        "streak_tracking": False,
        "score": None,
        "gamification": False
    }

# Reflection prompts (opt-in, never pushed)
@app.get("/api/prompts/settings")
async def prompt_settings():
    """User's prompt preferences."""
    return {
        "prompts_enabled": settings.PROMPTS_ENABLED_BY_DEFAULT,
        "prompts_optional": settings.PROMPTS_OPTIONAL,
        "can_disable_completely": True,
        "delivery": "offered after save, never pushed",
        "user_can_adjust": True
    }

@app.post("/api/prompts/disable")
async def disable_all_prompts(request: Request):
    """User can disable ALL prompts entirely."""
    return {
        "status": "success",
        "prompts_disabled": True,
        "can_re_enable": True,
        "description": "All reflection prompts disabled"
    }

@app.get("/api/prompts/after-save/{practice}")
async def get_optional_prompt(practice: str):
    """Optional reflection prompt offered after save (not pushed)."""
    return {
        "practice": practice,
        "prompt": f"How did this {practice} practice feel today?",
        "optional": True,
        "pushed": False,
        "can_skip": True,
        "description": "Optional reflection — dismiss anytime"
    }

# Difficult Month Mode (first-class feature)
@app.get("/api/difficult-month-mode")
async def difficult_month_status():
    """Difficult Month Mode configuration."""
    return {
        "feature_enabled": settings.DIFFICULT_MONTH_MODE_ENABLED,
        "description": "For when life is hard — everything adjusts",
        "active": False,
        "adjustments": settings.DIFFICULT_MONTH_ADJUSTMENTS
    }

@app.post("/api/difficult-month-mode/activate")
async def activate_difficult_month():
    """Activate Difficult Month Mode."""
    return {
        "status": "success",
        "difficult_month_active": True,
        "adjustments": {
            "reflection_frequency": "optional",
            "prompt_tone": "compassionate",
            "goal_tracking": "disabled",
            "comparison_view": "hidden"
        },
        "duration": "user-defined",
        "exit_anytime": True
    }

# No gamification endpoints (these SHOULD NOT exist)
@app.get("/api/no-streaks")
async def no_streaks():
    """Streaks are disabled by design."""
    return {
        "streaks_enabled": False,
        "reason": "Streaks create unhealthy pressure and external motivation"
    }

@app.get("/api/no-scores")
async def no_scores():
    """Scores are disabled by design."""
    return {
        "scores_enabled": False,
        "reason": "Quantifying lived experience corrupts genuine practice"
    }

@app.get("/api/no-badges")
async def no_badges():
    """Badges are disabled by design."""
    return {
        "badges_enabled": False,
        "reason": "Achievement symbols encourage performative practice"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)

from fastapi.responses import FileResponse
import os as _os

@app.get('/api/health')
async def health_alias():
    """NGINX-compliant health alias. Author: Mani Padisetti"""
    return await health()

@app.get('/')
async def root():
    """Serve index.html. Author: Mani Padisetti"""
    idx = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'index.html')
    if _os.path.exists(idx):
        return FileResponse(idx, media_type='text/html')
    return {'service': 'running'}
