import pytest


@pytest.mark.asyncio
async def test_list_templates_returns_full_catalog(async_client):
    resp = await async_client.get("/api/v1/templates")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    templates = body["result"]
    assert len(templates) == 127

    ids = {t["id"] for t in templates}
    # Original brief representatives
    assert "title_reveal" in ids
    assert "callout_zoom" in ids
    assert "subscribe_smash" in ids
    # New entries from the expanded catalog
    assert "kinetic_typography" in ids
    assert "camera_pan" in ids
    assert "screen_shake" in ids


@pytest.mark.asyncio
async def test_manic_count_matches_spec(async_client):
    resp = await async_client.get("/api/v1/templates")
    templates = resp.json()["result"]
    manic = [t for t in templates if t["manic_compatible"]]
    # 9 original manic + 7 from the all-manic Reactions/shorts vernacular category.
    assert len(manic) == 16


@pytest.mark.asyncio
async def test_category_coverage(async_client):
    resp = await async_client.get("/api/v1/templates")
    templates = resp.json()["result"]
    categories = {t["category"] for t in templates}
    assert categories == {
        "text_titles",
        "math_equations",
        "data_charts",
        "diagrams",
        "compare_contrast",
        "emphasis_reveals",
        "motion_geometry",
        "camera_transitions",
        "outros_ctas",
        "media",
        "reactions_shorts",
    }


@pytest.mark.asyncio
async def test_implemented_flag(async_client):
    resp = await async_client.get("/api/v1/templates")
    templates = resp.json()["result"]
    by_id = {t["id"]: t for t in templates}
    # Only title_reveal has a defs file so far.
    assert by_id["title_reveal"]["implemented"] is True
    assert by_id["text_pop"]["implemented"] is False


@pytest.mark.asyncio
async def test_get_template_detail_for_implemented(async_client):
    resp = await async_client.get("/api/v1/templates/title_reveal")
    assert resp.status_code == 200
    body = resp.json()["result"]
    assert body["id"] == "title_reveal"
    assert body["version"] == "1.0.0"
    assert body["manic_compatible"] is True
    assert len(body["content_hash"]) == 64  # sha256 hex
    # Param spec is preserved as data
    param_names = [p["name"] for p in body["params"]]
    assert "title" in param_names
    assert "color" in param_names
    # Steps reference primitives
    primitives = {s["primitive"] for s in body["steps"]}
    assert "text_reveal" in primitives
    assert "hold" in primitives
    # Manic preset declared
    assert "manic" in body["style_modifiers"]


@pytest.mark.asyncio
async def test_get_template_detail_for_unimplemented_returns_404(async_client):
    resp = await async_client.get("/api/v1/templates/text_pop")  # in catalog, no def
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_template_detail_for_unknown_returns_404(async_client):
    resp = await async_client.get("/api/v1/templates/not_a_real_template")
    assert resp.status_code == 404
