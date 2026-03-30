"""CK Life OS Configuration."""
import os


class Settings:
    """App settings."""

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5420"))
    ENV = os.getenv("ENV", "development")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://amtl:amtl@localhost:5433/ck_life_os")

    # Five Practices (universal, no philosophical names in UI)
    PRACTICES = [
        "presence",      # Awareness, mindfulness
        "reflection",    # Contemplation, processing
        "intention",     # Direction, values alignment
        "gratitude",     # Appreciation, perspective
        "equanimity"     # Balance, acceptance
    ]

    # Prompts: opt-in, never pushed
    PROMPTS_ENABLED_BY_DEFAULT = True
    PROMPTS_OPTIONAL = True  # User can disable completely

    # NO gamification
    STREAKS_ENABLED = False
    SCORES_ENABLED = False
    BADGES_ENABLED = False

    # Difficult Month Mode: first-class feature (not hidden)
    DIFFICULT_MONTH_MODE_ENABLED = True
    DIFFICULT_MONTH_ADJUSTMENTS = {
        "reflection_frequency": "optional",  # Don't pressure
        "prompt_tone": "compassionate",      # Gentler language
        "goal_tracking": "disabled",         # No pressure
        "comparison": "hidden"               # Hide other stats
    }


settings = Settings()
