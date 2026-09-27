import pytest
from app.providers.llm.fallback_rule_llm import FallbackRuleLLMProvider
from app.schemas.schemas import LLMScriptBreakdown

@pytest.mark.asyncio
async def test_fallback_rule_llm_analysis():
    provider = FallbackRuleLLMProvider()
    script = """
    India, Russia and China: A Changing Relationship.
    India and Russia have maintained a strong economic and defense relationship for decades.
    Trade between the nations continues to expand with energy and technology partnerships.
    """
    style = {"default_scene_duration": 6.0}
    result = await provider.generate_scene_plan(script, style, [])
    
    assert isinstance(result, LLMScriptBreakdown)
    assert len(result.scenes) >= 2
    for sc in result.scenes:
        assert sc.narration
        assert sc.duration > 0
        assert sc.caption
        assert sc.transition

from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)

def test_create_script_api_endpoint():
    # 1. Create a Project first
    res_proj = client.post("/api/projects", json={"name": "Script Test Project", "description": "Desc"})
    assert res_proj.status_code == 200, res_proj.text
    project_id = res_proj.json()["id"]

    # 2. Create Script for Project
    res_script = client.post(f"/api/projects/{project_id}/scripts", json={
        "title": "Script Title",
        "content": "Line 1.\nLine 2.\nLine 3."
    })
    assert res_script.status_code == 200, res_script.text
    script_data = res_script.json()
    assert script_data["title"] == "Script Title"
    assert script_data["project_id"] == project_id

