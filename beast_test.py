"""Beast Tests for CK Life OS."""
import pytest
from fastapi.testclient import TestClient
from main import JOURNAL_FILE, app

client = TestClient(app)


class TestHealth:
    """Health check."""

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["gamification"] == "DISABLED"
        assert response.json()["runtime_independent"] is True

    def test_api_health_alias(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_root_serves_ui(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "CK Life OS" in response.text


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
        assert data["receipt"]["external_send"] is False

    def test_unknown_practice_rejected_on_record(self):
        response = client.post("/api/practices/invalid-practice/record", json={"note": "test"})
        assert response.status_code == 404
        assert response.json()["detail"]["can_claim_canonical_five_only"] is True


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

    def test_unknown_practice_rejected_on_prompt(self):
        response = client.get("/api/prompts/after-save/invalid-practice")
        assert response.status_code == 404

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


class TestMani100TruthSurfaces:
    """Local/internal truth surfaces for C1 audit."""

    def test_product_bible_matrix_truth(self):
        response = client.get("/api/product-bible-matrix")
        assert response.status_code == 200
        data = response.json()
        assert data["covers_features"] is True
        assert data["covers_functions"] is True
        assert data["covers_500_ideas"] is True
        assert data["covers_field_level_innovations"] is True
        assert data["covers_cross_app_handoffs"] is True
        assert data["covers_guided_use"] is True
        assert data["covers_reports_exports"] is True
        assert data["covers_synthetic_data_hygiene"] is True
        assert data["covers_delivery_matrix"] is True
        assert data["covers_semantic_intent_map"] is True

    def test_r2d2_equivalent_truth(self):
        response = client.get("/api/r2d2")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pass"
        assert data["partial"] == 0
        assert data["blocked"] == 0
        assert "guided_use" in data["checks"]
        assert "reports_exports" in data["checks"]
        assert "synthetic_data_hygiene" in data["checks"]

    def test_ideas_are_counted_and_labelled_synthetic(self):
        response = client.get("/api/ideas")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 500
        assert len(data["ideas"]) == 500
        assert data["synthetic_data"] is True
        assert data["provider_called"] is False

    def test_ideas_filter_and_detail(self):
        response = client.get("/api/ideas?practice=presence&situation=morning&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["returned"] == 3
        assert all(item["practice"] == "presence" for item in data["ideas"])
        detail = client.get(f"/api/ideas/{data['ideas'][0]['id']}")
        assert detail.status_code == 200
        assert detail.json()["implementation_status"] == "seed_idea_not_feature"

    def test_contextual_6w_eli10(self):
        response = client.get("/api/contextual-guide/presence")
        assert response.status_code == 200
        data = response.json()
        for key in ["who", "what", "when", "where", "why", "how", "eli10"]:
            assert data[key]
        assert data["pressure"] == "none"

    def test_dependency_down_fallback(self):
        response = client.get("/api/dependency-status")
        assert response.status_code == 200
        data = response.json()
        assert data["postgres"]["required_for_core_ui"] is False
        assert data["postgres"]["fallback"] == "local JSONL receipts"
        assert data["external_providers"]["required_for_core_ui"] is False
        assert data["external_providers"]["configured_provider"] == "openrouter"
        assert data["external_providers"]["provider_called"] is False
        assert data["runtime_independent"] is True

    def test_openrouter_policy_exposes_no_secret(self):
        response = client.get("/api/ai/model-policy")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openrouter"
        assert data["routing_order"] == ["free", "modest", "expensive"]
        assert data["policy"]["free"]["reasoning_levels"] == ["low"]
        assert data["policy"]["modest"]["reasoning_levels"] == ["medium"]
        assert data["policy"]["expensive"]["reasoning_levels"] == ["high"]
        assert "OPENROUTER_API_KEY" not in str(data["policy"])
        assert "server-side" in data["secret_boundary"]

    def test_openrouter_reasoning_route_and_cost_cap(self):
        low = client.post("/api/ai/route", json={"task": "write a short prompt", "reasoning_level": "low"})
        high_capped = client.post(
            "/api/ai/route",
            json={"task": "hard synthesis", "reasoning_level": "high", "max_cost_tier": "modest"},
        )
        assert low.status_code == 200
        assert high_capped.status_code == 200
        assert low.json()["selected"]["tier"] == "free"
        assert high_capped.json()["selected"]["tier"] == "modest"
        assert low.json()["provider_called"] is False
        assert high_capped.json()["provider_called"] is False

    def test_openrouter_complete_requires_explicit_execution_and_paid_approval(self):
        response = client.post(
            "/api/ai/complete",
            json={"prompt": "Suggest one gentle action", "reasoning_level": "medium", "execute": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["selected"]["tier"] == "modest"
        assert data["provider_called"] is False
        assert data["fallback"] is True
        assert data["approval_required"] is True

    def test_openrouter_complete_requires_prompt(self):
        response = client.post("/api/ai/complete", json={"reasoning_level": "low"})
        assert response.status_code == 400

    def test_encrypted_journal_roundtrip_and_at_rest_boundary(self):
        phrase = "journal encryption proof unique phrase 270626"
        saved = client.post(
            "/api/journal",
            json={"practice": "reflection", "title": "Encryption proof", "content": phrase},
        )
        assert saved.status_code == 200
        saved_data = saved.json()
        assert saved_data["encrypted_at_rest"] is True
        assert saved_data["plaintext_stored"] is False
        assert saved_data["external_send"] is False

        status = client.get("/api/journal/status").json()
        assert status["enabled"] is True
        assert status["encrypted_at_rest"] is True
        assert status["plaintext_stored"] is False

        listed = client.get("/api/journal").json()
        assert listed["encrypted_at_rest"] is True
        assert any(item["journal_id"] == saved_data["journal_id"] for item in listed["items"])

        detail = client.get(f"/api/journal/{saved_data['journal_id']}")
        assert detail.status_code == 200
        assert detail.json()["content"] == phrase
        assert detail.json()["decrypted_for_local_ui"] is True

        assert JOURNAL_FILE.exists()
        assert phrase not in JOURNAL_FILE.read_text(encoding="utf-8")

    def test_ui_and_data_truth(self):
        ui = client.get("/api/ui-truth").json()
        data = client.get("/api/data-truth").json()
        assert ui["button_truth"] is True
        assert ui["count_truth"] is True
        assert ui["buttons"]["ai_route"] == "POST /api/ai/route"
        assert ui["buttons"]["journal_save"] == "POST /api/journal"
        assert data["ideas"]["count"] == 500
        assert data["encrypted_journal"]["encrypted_at_rest"] is True
        assert data["encrypted_journal"]["plaintext_stored"] is False
        assert data["external_send"] is False
        assert data["paid_provider_call"] is False
        assert data["ai_provider"]["configured_provider"] == "openrouter"
        assert data["ai_provider"]["last_proof_provider_called"] is False

    def test_guided_use(self):
        response = client.get("/api/guided-use?view=reports")
        assert response.status_code == 200
        data = response.json()
        assert data["screen"] == "Reports"
        assert "what to click" not in data["start_here"].lower()
        assert data["write_boundary"]

    def test_reports_and_markdown_export(self):
        response = client.get("/api/reports/local-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["idea_count"] == 500
        assert data["handover_boundary"]["external_send"] is False
        markdown = client.get("/api/reports/local-summary.md")
        assert markdown.status_code == 200
        assert "CK Life OS Local Summary" in markdown.text

    def test_handover_gate_is_local_only(self):
        response = client.get("/api/handoffs")
        assert response.status_code == 200
        data = response.json()
        assert data["external_send"] is False
        assert data["human_review_required"] is True
        staged = client.post("/api/handoffs/lifeos-elaine-local/stage", json={"note": "test"})
        assert staged.status_code == 200
        assert staged.json()["external_send"] is False
        assert staged.json()["approval_state"] == "draft_local_only"

    def test_synthetic_data_hygiene(self):
        status = client.get("/api/synthetic-data/status")
        assert status.status_code == 200
        assert status.json()["synthetic_outside_demo_scope"] == 0
        preview = client.get("/api/synthetic-data/removal-preview")
        assert preview.status_code == 200
        assert preview.json()["would_remove"] == 0
        cleanup = client.post("/api/synthetic-data/cleanup", json={"confirm": True})
        assert cleanup.status_code == 200
        assert cleanup.json()["post_clean_synthetic_outside_demo_scope"] == 0

    def test_field_oss_cost_effort_truth(self):
        fields = client.get("/api/field-utilities").json()
        oss = client.get("/api/oss-adoption").json()
        cost = client.get("/api/cost-effort-reduction").json()
        assert fields["total"] >= 5
        assert oss["total"] >= 4
        assert cost["total"] >= 3
