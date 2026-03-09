import pytest
from unittest.mock import Mock

from core.ai_assistant.agents.base import AgentTask
from core.ai_assistant.agents.repo_scout_agent import RepoScoutAgent

def test_repo_scout_agent_success():
    mock_llm = Mock()
    mock_llm.generate.return_value = '{"fake": "response"}'
    
    mock_prompt_loader = Mock()
    mock_prompt_loader.load.return_value = "Template: {OBJETIVO} {CONTEXTO}"
    
    mock_validator = Mock()
    mock_validator._parse_json.return_value = {
        "solution_categories": ["Categories 1"],
        "repeated_patterns": ["Pattern 1"],
        "copy_conceptually": ["Concept 1"],
        "avoid_copying": ["Avoid 1"],
        "adoption_risks": ["Risk 1"],
        "proposal_for_atlas": ["Proposal 1"],
        "references": [{"name": "ref", "reason": "reason"}],
        "summary": "Scout generated successfully"
    }

    agent = RepoScoutAgent(mock_llm, mock_prompt_loader, mock_validator)
    
    task = AgentTask(
        task_id="301",
        agent_name="repo_scout_agent",
        objective="Scout Repo",
        context={},
        inputs={}
    )
    
    result = agent.run(task)
    
    assert result.status == "success"
    assert result.task_id == "301"
    assert "Pattern 1" in result.result["repeated_patterns"]

def test_repo_scout_agent_validation_error():
    mock_llm = Mock()
    mock_prompt_loader = Mock()
    mock_validator = Mock()
    
    # Missing 'references'
    mock_validator._parse_json.return_value = {
        "solution_categories": [],
        "repeated_patterns": [],
        "copy_conceptually": [],
        "avoid_copying": [],
        "adoption_risks": [],
        "proposal_for_atlas": []
    }

    agent = RepoScoutAgent(mock_llm, mock_prompt_loader, mock_validator)
    task = AgentTask(task_id="301", agent_name="scout", objective="Scout", context={}, inputs={})
    
    with pytest.raises(ValueError, match="Repo scout output missing key: references"):
        agent.run(task)
