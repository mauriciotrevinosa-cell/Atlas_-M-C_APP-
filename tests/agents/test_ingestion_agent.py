import pytest
from unittest.mock import Mock

from core.ai_assistant.agents.base import AgentTask
from core.ai_assistant.agents.ingestion_agent import IngestionAgent

def test_ingestion_agent_success():
    mock_llm = Mock()
    mock_llm.generate.return_value = '{"fake": "response"}'
    
    mock_prompt_loader = Mock()
    mock_prompt_loader.load.return_value = "Template: {OBJETIVO} {DATOS_RAW}"
    
    mock_validator = Mock()
    mock_validator._parse_json.return_value = {
        "executive_summary": "Summary",
        "key_concepts": ["Concept 1"],
        "entities": [{"type": "role", "name": "Owner"}],
        "relations": [{"from": "O", "to": "W", "relation": "M"}],
        "actionable_data": ["Data 1"],
        "ambiguities": ["Amb 1"],
        "knowledge_pack": {"domain": "atlas", "version": "v1", "facts": []},
        "summary": "Ingestion completed successfully"
    }

    agent = IngestionAgent(mock_llm, mock_prompt_loader, mock_validator)
    
    task = AgentTask(
        task_id="401",
        agent_name="ingestion_agent",
        objective="Ingest Repo",
        context={},
        inputs={"raw_data": "data"}
    )
    
    result = agent.run(task)
    
    assert result.status == "success"
    assert result.task_id == "401"
    assert "Data 1" in result.result["actionable_data"]

def test_ingestion_agent_validation_error():
    mock_llm = Mock()
    mock_prompt_loader = Mock()
    mock_validator = Mock()
    
    # Missing 'knowledge_pack'
    mock_validator._parse_json.return_value = {
        "executive_summary": "Summary",
        "key_concepts": [],
        "entities": [],
        "relations": [],
        "actionable_data": [],
        "ambiguities": []
    }

    agent = IngestionAgent(mock_llm, mock_prompt_loader, mock_validator)
    task = AgentTask(task_id="401", agent_name="ingest", objective="Ingest", context={}, inputs={})
    
    with pytest.raises(ValueError, match="Ingestion agent output missing key: knowledge_pack"):
        agent.run(task)
