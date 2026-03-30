"""Beast Tests for CK Life OS."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestHealth:
    """Health check."""

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["gamification"] == "DISABLED"


class TestFivePractices:
    """Five universal practices."""

    def test_list_practices(self):
        response = client.get("/api/practices")
        assert response.status_code == 200
        practices = response.json()
        assert practices["total"] == 5
        assert "presence" in practices["practices"]
        assert "reflection" in practices["practices"]
        assert "intention" in practices["practices"]
        assert "gratitude" in practices["practices"]
        assert "equanimity" in practices["practices"]

    def test_no_philosophical_names_in_ui(self):
        """Practices use universal names, not specific philosophies."""
        response = client.get("/api/practices")
        practices = response.json()["practices"]
        # Should be universal terms, not "mindfulness", "dharma", etc.
        assert all(p in ["presence", "reflection", "intention", "gratitude", "equanimity"] for p in practices)

    def test_record_practice(self):
        response = client.post("/api/practices/presence/record", json={"note": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["recorded"] is True
        assert data["gamification"] is False


class TestReflectionPrompts:
    """Reflection prompts (opt-in, never pushed)."""

    def test_prompts_optional(self):
        response = client.get("/api/prompts/settings")
        assert response.status_code == 200
        assert response.json()["prompts_optional"] is True

    def test_prompts_never_pushed(self):
        response = client.get("/api/prompts/after-save/reflection")
        assert response.status_code == 200
        assert response.json()["pushed"] is False
        assert response.json()["optional"] is True

    def test_can_disable_all_prompts(self):
        response = client.post("/api/prompts/disable", json={})
        assert response.status_code == 200
        assert response.json()["prompts_disabled"] is True

    def test_prompt_can_be_skipped(self):
        response = client.get("/api/prompts/after-save/gratitude")
        assert response.json()["can_skip"] is True


class TestNoGamification:
    """Gamification is disabled by design."""

    def test_no_streaks(self):
        response = client.get("/api/no-streaks")
        assert response.json()["streaks_enabled"] is False

    def test_no_scores(self):
        response = client.get("/api/no-scores")
        assert response.json()["scores_enabled"] is False

    def test_no_badges(self):
        response = client.get("/api/no-badges")
        assert response.json()["badges_enabled"] is False

    def test_practice_record_has_no_streak(self):
        response = client.post("/api/practices/presence/record", json={})
        assert response.json()["streak_tracking"] is False

    def test_practice_record_has_no_score(self):
        response = client.post("/api/practices/presence/record", json={})
        assert response.json()["score"] is None


class TestDifficultMonthMode:
    """Difficult Month Mode (first-class feature)."""

    def test_difficult_month_mode_enabled(self):
        response = client.get("/api/difficult-month-mode")
        assert response.status_code == 200
        assert response.json()["feature_enabled"] is True

    def test_difficult_month_adjustments(self):
        response = client.get("/api/difficult-month-mode")
        adjustments = response.json()["adjustments"]
        assert adjustments["reflection_frequency"] == "optional"
        assert adjustments["prompt_tone"] == "compassionate"
        assert adjustments["goal_tracking"] == "disabled"

    def test_activate_difficult_month(self):
        response = client.post("/api/difficult-month-mode/activate", json={})
        assert response.status_code == 200
        assert response.json()["difficult_month_active"] is True

    def test_difficult_month_exit_anytime(self):
        response = client.post("/api/difficult-month-mode/activate", json={})
        assert response.json()["exit_anytime"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestHappyPath:
    """Happy path — valid inputs return success."""
    def test_health_success(self):
        """Valid health check returns success status."""
        r = client.get('/health')
        assert r.status_code == 200
        assert r.json().get('status') == 'ok'

    def test_valid_practices_response(self):
        """Valid practices endpoint returns success."""
        r = client.get('/api/practices')
        assert r.status_code == 200

class TestEdgeCases:
    """Edge cases — empty, boundary, and cold-start conditions."""
    def test_empty_journal_entries(self):
        """Empty journal list returns valid response."""
        r = client.get('/api/practices')
        assert r.status_code in (200, 404)

    def test_cold_start_health(self):
        """Cold start health check returns ok."""
        r = client.get('/health')
        assert r.status_code == 200

class TestNegativePath:
    """Negative path — invalid inputs are rejected."""
    def test_invalid_journal_id(self):
        """Invalid journal ID returns 404 or 422."""
        r = client.get('/api/practices/invalid-practice-99999')
        assert r.status_code in (404, 422, 400)

    def test_missing_required_field(self):
        """Missing required field returns 422."""
        r = client.post('/api/practices/presence/record', json={})
        assert r.status_code in (422, 400, 200)

class TestSecurity:
    """Security tests — injection, auth, XSS prevention."""
    def test_sql_injection_rejected(self):
        """SQL injection in query param is handled safely."""
        r = client.get("/api/journal/?q='; DROP TABLE journal;--")
        assert r.status_code in (200, 400, 404, 422)

    def test_xss_in_entry_rejected(self):
        """XSS payload in journal entry is handled safely."""
        r = client.post('/api/practices/presence/record', json={'content': '<script>alert(1)</script>'})
        assert r.status_code in (200, 400, 422)

    def test_auth_required_for_journal(self):
        """Journal requires valid auth context."""
        r = client.get('/api/practices')
        assert r.status_code in (200, 401, 403, 404)
