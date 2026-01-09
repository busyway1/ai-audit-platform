"""Tests for Ralph-wiggum loop pattern."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.ralph_loop import (
    RalphWiggumLoop,
    LoopResult,
    ValidationResult,
    create_ralph_loop
)


class MockAgent:
    """Mock agent for testing."""
    name = "TestAgent"
    call_count = 0

    async def run(self, task_state, strategy="default"):
        self.call_count += 1
        return {
            "summary": f"Executed with {strategy}",
            "strategy_used": strategy,
            "attempt": self.call_count
        }


@pytest.fixture
def mock_agent():
    return MockAgent()


@pytest.fixture
def ralph_loop():
    return RalphWiggumLoop(max_attempts=3)


class TestRalphWiggumLoop:
    """Test Ralph-wiggum loop functionality."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, ralph_loop, mock_agent):
        """Should complete on first successful attempt."""
        async def validator(result):
            return ValidationResult(status="success")

        result, state, log = await ralph_loop.execute_with_loop(
            mock_agent, {}, validator
        )

        assert result == LoopResult.SUCCESS
        assert mock_agent.call_count == 1
        assert len(log) >= 2  # At least instruction + response + validation

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, ralph_loop, mock_agent):
        """Should retry with different strategy on failure."""
        attempt = 0

        async def validator(result):
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                return ValidationResult(status="failure", error="Not ready")
            return ValidationResult(status="success")

        result, state, log = await ralph_loop.execute_with_loop(
            mock_agent, {}, validator
        )

        assert result == LoopResult.SUCCESS
        assert mock_agent.call_count == 3

    @pytest.mark.asyncio
    async def test_hitl_after_max_attempts(self, ralph_loop, mock_agent):
        """Should request HITL after max attempts exhausted."""
        async def validator(result):
            return ValidationResult(status="failure", error="Always fails")

        result, state, log = await ralph_loop.execute_with_loop(
            mock_agent, {}, validator
        )

        assert result == LoopResult.HITL_REQUIRED
        assert mock_agent.call_count == 3

        # Check escalation logged
        escalation = [e for e in log if e.message_type == "escalation"]
        assert len(escalation) == 1
        assert "Human intervention required" in escalation[0].content

    @pytest.mark.asyncio
    async def test_partial_success_retry(self, ralph_loop, mock_agent):
        """Should retry on partial success."""
        attempt = 0

        async def validator(result):
            nonlocal attempt
            attempt += 1
            if attempt < 2:
                return ValidationResult(
                    status="partial",
                    issues=["Missing field X"]
                )
            return ValidationResult(status="success")

        result, state, log = await ralph_loop.execute_with_loop(
            mock_agent, {}, validator
        )

        assert result == LoopResult.SUCCESS
        assert mock_agent.call_count == 2

    @pytest.mark.asyncio
    async def test_hitl_guidance_continues_loop(self, ralph_loop, mock_agent):
        """Should use HITL guidance in retry."""
        async def validator(result):
            if result.get("has_guidance"):
                return ValidationResult(status="success")
            return ValidationResult(status="failure", error="Need guidance")

        # First run - fails
        mock_agent_with_guidance = MockAgent()

        async def run_with_guidance(task_state, strategy="default"):
            return {
                "summary": "Executed",
                "has_guidance": "hitl_guidance" in task_state
            }
        mock_agent_with_guidance.run = run_with_guidance

        # Simulate HITL response
        result, state, log = await ralph_loop.execute_with_hitl_guidance(
            mock_agent_with_guidance,
            {},
            validator,
            "Try using method X instead"
        )

        assert result == LoopResult.SUCCESS

    @pytest.mark.asyncio
    async def test_conversation_log_format(self, ralph_loop, mock_agent):
        """Should produce proper conversation log format."""
        async def validator(result):
            return ValidationResult(status="success")

        result, state, log = await ralph_loop.execute_with_loop(
            mock_agent, {}, validator
        )

        log_dicts = ralph_loop.get_conversation_log_dict()

        assert all("from_agent" in e for e in log_dicts)
        assert all("to_agent" in e for e in log_dicts)
        assert all("message_type" in e for e in log_dicts)
        assert all("content" in e for e in log_dicts)
        assert all("timestamp" in e for e in log_dicts)

    @pytest.mark.asyncio
    async def test_exception_handling(self, ralph_loop):
        """Should handle agent exceptions gracefully."""
        class FailingAgent:
            name = "FailingAgent"
            attempt = 0

            async def run(self, task_state, strategy="default"):
                self.attempt += 1
                if self.attempt < 3:
                    raise ValueError("Simulated error")
                return {"summary": "Finally worked"}

        async def validator(result):
            return ValidationResult(status="success")

        agent = FailingAgent()
        result, state, log = await ralph_loop.execute_with_loop(
            agent, {}, validator
        )

        assert result == LoopResult.SUCCESS
        error_logs = [e for e in log if e.message_type == "error"]
        assert len(error_logs) == 2


class TestCreateRalphLoop:
    """Test factory function."""

    def test_default_creation(self):
        loop = create_ralph_loop()
        assert loop.max_attempts == 3
        assert len(loop.retry_strategies) == 3

    def test_custom_parameters(self):
        loop = create_ralph_loop(
            max_attempts=5,
            strategies=["fast", "thorough", "expert"]
        )
        assert loop.max_attempts == 5
        assert loop.retry_strategies == ["fast", "thorough", "expert"]
