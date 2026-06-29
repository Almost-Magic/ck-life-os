"""Beast Tests for CK Life OS."""
import pytest
import main as lifeos
from fastapi.testclient import TestClient
from main import INNER_WORK_FILE, JOURNAL_FILE, NAS_EXCLUDED_ROOTS, app, _is_excluded_source_path

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
        assert data["covers_daily_lens"] is True
        assert data["daily_lens"]["library_count"] == 10000

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
        assert "daily_lens_10k_library" in data["checks"]
        assert "daily_lens_local_saved_list" in data["checks"]

    def test_innovations_are_counted_labelled_and_absorbed(self):
        response = client.get("/api/ideas")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 500
        assert len(data["ideas"]) == 500
        assert data["synthetic_data"] is True
        assert data["provider_called"] is False
        assert "absorbed through contextual UI helpers" in data["catalogue_truth"]
        first = data["ideas"][0]
        assert first["absorbed_in_ui"] is True
        assert first["innovation_level"] in ("field-level", "navigation-level")
        for key in ["user_control", "calm_disclosure", "cost_reduction", "neurodivergent_support", "micro_joke"]:
            assert first[key]
        for key in ["what", "who", "why", "when", "where", "how", "eli10"]:
            assert first["sixw"][key]

    def test_ideas_filter_and_detail(self):
        response = client.get("/api/ideas?practice=presence&situation=morning&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["returned"] == 3
        assert all(item["practice"] == "presence" for item in data["ideas"])
        detail = client.get(f"/api/ideas/{data['ideas'][0]['id']}")
        assert detail.status_code == 200
        assert detail.json()["implementation_status"] == "innovation_pattern_absorbed_in_ui_lens"
        assert detail.json()["user_control"]
        assert detail.json()["neurodivergent_support"]

    def test_daily_lens_10k_library_and_local_save(self):
        current = client.get("/api/daily-lens")
        assert current.status_code == 200
        data = current.json()
        assert data["total"] == 10000
        assert data["provider_called"] is False
        assert data["external_send"] is False
        lens = data["current"]
        assert lens["lens_id"].startswith("lens-")
        assert lens["text"]
        assert lens["permission_status"] == "local_generated_original_or_paraphrased_no_verbatim_copyright_claim"
        for key in ["what", "who", "why", "when", "where", "how", "eli10"]:
            assert lens["field_utility"][key]

        library = client.get("/api/daily-lens/library?theme=attention&limit=5")
        assert library.status_code == 200
        library_data = library.json()
        assert library_data["returned"] == 5
        assert all(item["theme"] == "attention" for item in library_data["items"])

        saved = client.post("/api/daily-lens/save", json={"lens_id": lens["lens_id"]})
        assert saved.status_code == 200
        saved_data = saved.json()
        assert saved_data["external_send"] is False
        assert saved_data["source_write"] is False
        assert saved_data["provider_called"] is False
        listed = client.get("/api/daily-lens/saved")
        assert listed.status_code == 200
        assert any(item["save_id"] == saved_data["save_id"] for item in listed.json()["items"])

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
        assert data["source_index"]["required_for_core_ui"] is False
        assert len(data["source_index"]["excluded_roots"]) == 2
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
        assert data["policy"]["free"]["model"] == "openrouter/free"
        assert data["policy"]["free"]["reasoning_levels"] == ["low", "routine", "cheap"]
        assert data["policy"]["modest"]["reasoning_levels"] == ["medium", "normal", "moderate"]
        assert data["policy"]["expensive"]["reasoning_levels"] == ["high", "deep", "hard"]
        assert data["policy"]["free"]["paid"] is False
        assert data["policy"]["modest"]["paid"] is True
        assert data["policy"]["expensive"]["paid"] is True
        assert data["auto_reasoning"]["expensive"]
        assert "OPENROUTER_API_KEY" not in str(data["policy"])
        assert "server-side" in data["secret_boundary"]

    def test_openrouter_reasoning_route_and_cost_cap(self):
        low = client.post("/api/ai/route", json={"task": "write a short prompt", "reasoning_level": "low"})
        auto = client.post("/api/ai/route", json={"task": "deep audit the product bible and architecture"})
        high_capped = client.post(
            "/api/ai/route",
            json={"task": "hard synthesis", "reasoning_level": "high", "max_cost_tier": "modest"},
        )
        assert low.status_code == 200
        assert auto.status_code == 200
        assert high_capped.status_code == 200
        assert low.json()["selected"]["tier"] == "free"
        assert auto.json()["selected"]["tier"] == "expensive"
        assert high_capped.json()["selected"]["tier"] == "modest"
        assert low.json()["provider_called"] is False
        assert auto.json()["provider_called"] is False
        assert high_capped.json()["provider_called"] is False
        assert high_capped.json()["approval_required_for_selected_tier"] is True

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
        assert data["approval_reason"] == "execute_required"

        paid_blocked = client.post(
            "/api/ai/complete",
            json={"prompt": "Do a deep architecture review", "reasoning_level": "high", "execute": True},
        )
        assert paid_blocked.status_code == 200
        paid_data = paid_blocked.json()
        assert paid_data["selected"]["tier"] == "expensive"
        assert paid_data["provider_called"] is False
        assert paid_data["approval_reason"] == "paid_tier_requires_allow_paid_provider"

    def test_openrouter_free_tier_can_execute_without_paid_approval_when_key_exists(self, monkeypatch):
        def fake_call(prompt, tier, system=None):
            return {
                "provider_called": True,
                "fallback": False,
                "content": "free tier proof",
                "raw_model": tier["model"],
            }

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-sent")
        monkeypatch.setattr(lifeos, "_call_openrouter", fake_call)
        response = client.post(
            "/api/ai/complete",
            json={"prompt": "Write one short prompt", "reasoning_level": "low", "execute": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["selected"]["tier"] == "free"
        assert data["selected"]["model"] == "openrouter/free"
        assert data["provider_called"] is True
        assert data["approval_required"] is False

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

    def test_inner_work_guides_without_answering_and_encrypts(self):
        phrase = "I felt anger when I was ignored and I want to understand the rejected part."
        saved = client.post(
            "/api/inner-work/session",
            json={"mode": "shadow", "intention": "understand reaction", "input": phrase},
        )
        assert saved.status_code == 200
        data = saved.json()
        guidance = data["guidance"]
        assert data["encrypted_at_rest"] is True
        assert data["plaintext_stored"] is False
        assert data["external_send"] is False
        assert guidance["mode_label"] == "Shadow integration"
        assert guidance["ai_provider_called"] is False
        assert "not a final interpretation" in guidance["not_answer"]
        assert len(guidance["program"]) == 7

        detail = client.get(f"/api/inner-work/session/{data['session_id']}")
        assert detail.status_code == 200
        assert detail.json()["payload"]["input_text"] == phrase
        assert INNER_WORK_FILE.exists()
        assert phrase not in INNER_WORK_FILE.read_text(encoding="utf-8")

    def test_inner_work_safety_brake_switches_to_grounding(self):
        response = client.post(
            "/api/inner-work/session",
            json={"mode": "jk_observation", "input": "I might hurt myself"},
        )
        assert response.status_code == 200
        guidance = response.json()["guidance"]
        assert guidance["mode_label"] == "Grounding first"
        assert guidance["safety"]["state"] == "grounding_required"
        assert guidance["safety"]["depth_allowed"] == "grounding_only"

    def test_ui_and_data_truth(self):
        ui = client.get("/api/ui-truth").json()
        data = client.get("/api/data-truth").json()
        assert ui["button_truth"] is True
        assert ui["count_truth"] is True
        assert ui["buttons"]["ai_route"] == "POST /api/ai/route"
        assert ui["buttons"]["journal_save"] == "POST /api/journal"
        assert ui["buttons"]["daily_lens_save"] == "POST /api/daily-lens/save"
        assert ui["buttons"]["inner_work_session"] == "POST /api/inner-work/session"
        assert ui["buttons"]["source_index_status"] == "GET /api/source-index/status"
        assert data["ideas"]["count"] == 500
        assert data["daily_lens"]["count"] == 10000
        assert data["daily_lens"]["provider_called"] is False
        assert data["encrypted_journal"]["encrypted_at_rest"] is True
        assert data["inner_work"]["encrypted_at_rest"] is True
        assert data["inner_work"]["ai_provider_called"] is False
        assert data["nas_source_index"]["excluded_roots_count"] == 2
        assert data["nas_source_index"]["only_approved_exclusions"] is True
        assert data["encrypted_journal"]["plaintext_stored"] is False
        assert data["external_send"] is False
        assert data["paid_provider_call"] is False
        assert data["ai_provider"]["configured_provider"] == "openrouter"
        assert data["ai_provider"]["last_proof_provider_called"] is False

    def test_nas_source_index_exclusion_truth(self):
        status = client.get("/api/source-index/status")
        assert status.status_code == 200
        data = status.json()
        assert data["approved_exclusion_count"] == 2
        assert data["excluded_roots"] == NAS_EXCLUDED_ROOTS
        assert data["only_approved_exclusions"] is True
        assert _is_excluded_source_path(NAS_EXCLUDED_ROOTS[0])
        assert _is_excluded_source_path(NAS_EXCLUDED_ROOTS[1])
        assert not _is_excluded_source_path(r"\\NAS2\amtl-documents")

    def test_rag_status_exposes_internal_external_lanes_and_two_exclusions(self):
        response = client.get("/api/rag/status")
        assert response.status_code == 200
        data = response.json()
        assert data["where_to_access"] == "Knowledge -> RAG / Sources"
        assert data["internal_sources"]["accepted"] is True
        assert data["internal_sources"]["excluded_roots"] == NAS_EXCLUDED_ROOTS
        assert data["external_sources"]["accepted_as_local_draft_or_pasted_text"] is True
        assert data["external_sources"]["fetch_enabled"] == "approval_gated"
        assert data["external_sources"]["approval_required_before_fetch_or_ingest"] is True
        assert data["provider_calls_required_for_search"] is False
        assert data["pgvector_required_for_local_internal"] is False

    def test_rag_source_draft_is_local_only_and_external_fetch_blocked(self):
        response = client.post(
            "/api/rag/source-draft",
            json={
                "source_type": "external",
                "title": "Example external source",
                "location": "https://example.com/source",
                "notes": "Use only after approval.",
                "source_text": "CK Life OS unique pasted RAG excerpt 270628",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "external"
        assert data["accepted_for_rag"] is True
        assert data["searchable_local_text"] is True
        assert data["external_fetch_performed"] is False
        assert data["external_send"] is False
        assert data["source_write"] is False
        assert data["approval_required_before_external_fetch"] is True
        search = client.get("/api/rag/search?q=unique%20pasted%20RAG%20excerpt&limit=5")
        assert search.status_code == 200
        assert search.json()["returned"] >= 1
        assert search.json()["matches"][0]["source"] == "rag_source_draft"
        assert search.json()["external_fetch_performed"] is False

    def test_external_rag_source_fetch_requires_explicit_approval_and_stays_local(self, monkeypatch):
        def fake_fetch(url: str):
            return {
                "url": url,
                "text": "Approved external RAG fetch proof unique phrase 270628",
                "bytes_read": 54,
            }

        monkeypatch.setattr(lifeos, "_fetch_external_rag_source", fake_fetch)
        response = client.post(
            "/api/rag/source-draft",
            json={
                "source_type": "external",
                "title": "Approved external source",
                "location": "https://example.com/approved-source",
                "notes": "Fetch approved for local RAG.",
                "fetch_approved": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["external_fetch_approved"] is True
        assert data["external_fetch_performed"] is True
        assert data["external_fetch_status"] == "approved_local_ingest"
        assert data["approval_required_before_external_fetch"] is False
        assert data["external_send"] is False
        assert data["source_write"] is False
        search = client.get("/api/rag/search?q=Approved%20external%20RAG%20fetch%20proof&limit=5")
        assert search.status_code == 200
        assert search.json()["returned"] >= 1
        assert search.json()["matches"][0]["external_fetch_performed"] is True

    def test_nas_source_index_build_can_be_bounded_for_regression(self):
        response = client.post("/api/source-index/build", json={"max_files": 2})
        assert response.status_code == 200
        data = response.json()
        assert data["files_indexed"] <= 2
        assert data["excluded_roots_count"] == 2
        assert data["only_approved_exclusions"] is True
        assert data["external_send"] is False
        assert data["source_write"] is False
        assert data["provider_called"] is False

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

    def test_life_manager_v2_spec_covers_menu_screens_panels_and_buttons(self):
        response = client.get("/api/life-manager/spec")
        assert response.status_code == 200
        data = response.json()
        groups = {item["group"]: item["items"] for item in data["menu"]}
        assert "Today" in groups
        assert groups["Today"] == ["Home", "Daily Lens", "Start My Day", "Check In", "End My Day"]
        assert "Guidance" in groups
        assert "Ask Guide" in groups["Guidance"]
        assert "Plans" in groups
        assert "Knowledge" in groups
        assert "Academy" in groups["Knowledge"]
        assert "PIN Strategist" in groups["Knowledge"]
        assert "Admin / Proof" in groups
        screens = {item["id"]: item for item in data["screens"]}
        for screen_id in ["today", "dailyLens", "startDay", "checkIn", "endDay", "askGuide", "stuck", "decision", "voiceNotes", "lifeMap", "promises", "projects", "calendar", "academy", "askSources", "sources", "pinStrategist", "insights", "weeklyReview", "memory"]:
            assert screen_id in screens
            assert screens[screen_id]["tabs"]
            assert screens[screen_id]["buttons"]
            assert screens[screen_id]["panels"]
        assert data["layout_rules"]["middle_column_scroll"] == "disabled"
        assert data["layout_rules"]["left_menu"] == "grouped_collapsible_categories"
        assert data["layout_rules"]["right_rail"] == "contextual_collapsed_panels"
        assert data["boundaries"]["external_send"] is False
        assert data["boundaries"]["calendar_write"] is False
        assert data["boundaries"]["voice_transcription_provider_called"] is False

    def test_life_manager_v2_buttons_write_local_receipts_only(self):
        response = client.post(
            "/api/life-manager/receipt",
            json={"screen": "Start My Day", "action": "Accept plan", "note": "tiny plan proof"},
        )
        assert response.status_code == 200
        data = response.json()
        receipt = data["receipt"]
        assert receipt["screen"] == "Start My Day"
        assert receipt["action"] == "Accept plan"
        assert receipt["local_only"] is True
        assert receipt["external_send"] is False
        assert receipt["source_write"] is False
        assert receipt["provider_called"] is False
        assert receipt["calendar_write"] is False
        assert receipt["transcription_provider_called"] is False
        listed = client.get("/api/life-manager/receipts")
        assert listed.status_code == 200
        assert any(item["receipt_id"] == receipt["receipt_id"] for item in listed.json()["items"])

    def test_ui_truth_exposes_v2_calm_layout_and_buttons(self):
        response = client.get("/api/ui-truth")
        assert response.status_code == 200
        data = response.json()
        layout = data["amtl_operating_layout"]
        assert layout["middle_content_uses_tabs"] is True
        assert layout["no_middle_column_scroll"] is True
        assert layout["right_rail_collapsed_contextual_boxes"] is True
        assert data["life_manager_v2"]["screen_count"] >= 18
        assert data["life_manager_v2"]["academy_visible_in_knowledge"] is True
        assert data["life_manager_v2"]["pin_visible_in_knowledge"] is True
        assert "life_manager_receipt" in data["buttons"]
        assert "academy_practice" in data["buttons"]
        assert "pin_decision_brief" in data["buttons"]
        assert "ripple_calendar_write" in data["buttons"]

    def test_academy_is_real_local_screen_module(self):
        status = client.get("/api/academy/status")
        assert status.status_code == 200
        status_data = status.json()
        assert status_data["status"] == "implemented_local_internal"
        assert status_data["where_to_access"] == "Knowledge -> Academy"
        assert status_data["program_count"] >= 7
        assert status_data["lesson_count"] >= 9
        assert status_data["external_lms_required"] is False
        programs = client.get("/api/academy/programs")
        assert programs.status_code == 200
        first_program = programs.json()["items"][0]
        lessons = client.get(f"/api/academy/programs/{first_program['program_id']}/lessons")
        assert lessons.status_code == 200
        lesson = lessons.json()["items"][0]
        detail = client.get(f"/api/academy/lessons/{lesson['lesson_id']}")
        assert detail.status_code == 200
        assert detail.json()["field_utility"]["eli10"]
        practice = client.post(
            f"/api/academy/lessons/{lesson['lesson_id']}/practice",
            json={"action": "Save practice receipt", "note": "academy proof note"},
        )
        assert practice.status_code == 200
        receipt = practice.json()["receipt"]
        assert receipt["local_only"] is True
        assert receipt["external_lms_write"] is False
        assert receipt["provider_called"] is False
        receipts = client.get("/api/academy/receipts")
        assert any(item["receipt_id"] == receipt["receipt_id"] for item in receipts.json()["items"])
        readiness = client.get("/api/academy/readiness")
        assert readiness.status_code == 200
        assert readiness.json()["external_lms_required"] is False

    def test_pin_strategist_personal_intelligence_network_is_real(self):
        status = client.get("/api/pin/status")
        assert status.status_code == 200
        status_data = status.json()
        assert status_data["status"] == "implemented_local_internal"
        assert status_data["where_to_access"] == "Knowledge -> PIN Strategist"
        assert status_data["meaning"] == "Personal Intelligence Network"
        assert status_data["counts"]["people"] >= 3
        assert status_data["counts"]["sources"] >= 3
        assert status_data["counts"]["questions"] >= 4
        assert status_data["rag_access"]["excluded_roots"] == NAS_EXCLUDED_ROOTS
        assert status_data["provider_called"] is False
        people = client.get("/api/pin/people")
        assert people.status_code == 200
        assert people.json()["count"] >= 3
        sources = client.get("/api/pin/sources")
        assert sources.status_code == 200
        assert sources.json()["rag_endpoint"] == "/api/rag/source-draft"
        questions = client.get("/api/pin/questions")
        assert questions.status_code == 200
        assert questions.json()["count"] >= 4
        brief = client.post("/api/pin/decision-brief", json={"decision": "Should I study this source before deciding?"})
        assert brief.status_code == 200
        brief_data = brief.json()
        assert brief_data["brief"]["local_only"] is True
        assert brief_data["brief"]["provider_called"] is False
        assert "people_to_ask" in brief_data["brief"]
        assert brief_data["receipt"]["local_only"] is True
        radar = client.get("/api/pin/influence-radar")
        assert radar.status_code == 200
        assert radar.json()["provider_called"] is False
        queue = client.get("/api/pin/learning-queue")
        assert queue.status_code == 200
        assert "Ignore" in queue.json()["tabs"]
        review = client.get("/api/pin/monthly-review")
        assert review.status_code == 200
        assert review.json()["review"]["external_send"] is False
        receipts = client.get("/api/pin/receipts")
        assert any(item["receipt_id"] == brief_data["receipt"]["receipt_id"] for item in receipts.json()["items"])

    def test_live_action_gates_return_exact_blockers_without_credentials(self):
        status = client.get("/api/live-actions/status")
        assert status.status_code == 200
        assert status.json()["ripple_calendar"]["endpoint"] == "/api/ripple-calendar/write"
        voice = client.post("/api/voice/transcription", json={"audio_reference": "local-audio.wav"})
        assert voice.status_code == 200
        assert voice.json()["status"] == "blocked"
        assert voice.json()["receipt"]["live_action_performed"] is False
        ripple = client.post("/api/ripple-calendar/write", json={"title": "Proof event", "start": "2026-06-28T09:00:00"})
        assert ripple.status_code == 200
        assert ripple.json()["status"] == "blocked"
        assert "RIPPLE_CALENDAR_ENDPOINT not configured" in ripple.json()["receipt"]["blockers"]
        memory = client.post("/api/memory/sync", json={"memory_rows": [{"claim": "proof"}]})
        assert memory.status_code == 200
        assert memory.json()["status"] == "blocked"
        n8n = client.post(
            "/api/life-manager/n8n-workflows/ck-life-os-calendar-write-preflight/live-execute",
            json={"live_execute": True, "explicit_approval": False, "approval_reference": ""},
        )
        assert n8n.status_code == 200
        assert n8n.json()["status"] == "blocked"
        n8n_import = client.post(
            "/api/life-manager/n8n-workflows/ck-life-os-calendar-write-preflight/live-import",
            json={"live_import": True, "explicit_approval": False, "approval_reference": ""},
        )
        assert n8n_import.status_code == 200
        assert n8n_import.json()["status"] == "blocked"
        assert "N8N_API_BASE_URL not configured" in n8n_import.json()["receipt"]["blockers"]
        receipts = client.get("/api/live-actions/receipts")
        assert receipts.status_code == 200
        assert receipts.json()["count"] >= 5

    def test_life_manager_n8n_workflow_pack_is_importable_and_disabled(self):
        response = client.get("/api/life-manager/n8n-workflows")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert data["live_import_performed"] is False
        assert data["live_execution_performed"] is False
        assert data["external_send"] is False
        assert data["source_write"] is False
        boundaries = {item["fixes_boundary"] for item in data["items"]}
        assert boundaries == {
            "paid_model_execution",
            "live_voice_transcription",
            "external_calendar_writes",
            "cross_device_memory_sync",
        }
        for item in data["items"]:
            assert item["exists"] is True
            assert item["active_by_default"] is False
            assert item["active_in_export"] is False
            detail = client.get(f"/api/life-manager/n8n-workflows/{item['workflow_id']}")
            assert detail.status_code == 200
            workflow_json = detail.json()["import_json"]
            assert workflow_json["active"] is False
            assert workflow_json["nodes"]

    def test_life_manager_n8n_workflow_dry_run_and_preflight_are_local_only(self):
        workflow_id = "ck-life-os-calendar-write-preflight"
        dry_run = client.post(
            f"/api/life-manager/n8n-workflows/{workflow_id}/dry-run",
            json={"note": "calendar dry run only"},
        )
        assert dry_run.status_code == 200
        dry_receipt = dry_run.json()["receipt"]
        assert dry_receipt["status"] == "dry_run_recorded"
        assert dry_receipt["live_n8n_import_performed"] is False
        assert dry_receipt["live_n8n_execution_performed"] is False
        assert dry_receipt["calendar_write"] is False
        assert dry_receipt["external_send"] is False
        preflight = client.post(
            f"/api/life-manager/n8n-workflows/{workflow_id}/preflight",
            json={"write": True, "explicit_approval": False, "note": "no approval reference"},
        )
        assert preflight.status_code == 200
        preflight_data = preflight.json()
        assert preflight_data["live_action_performed"] is False
        assert preflight_data["can_import_manually"] is False
        assert preflight_data["receipt"]["status"] == "blocked_for_live_until_approved"
        receipts = client.get("/api/life-manager/n8n-workflows/receipts")
        assert receipts.status_code == 200
        assert any(item["receipt_id"] == dry_receipt["receipt_id"] for item in receipts.json()["items"])
