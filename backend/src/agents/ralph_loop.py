"""
Ralph-wiggum Loop Pattern
Agent retry mechanism that iterates until problem solved or HITL required.
"""

from typing import Any, Dict, Optional, List, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class LoopResult(Enum):
    """Result of loop execution."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    HITL_REQUIRED = "hitl_required"


@dataclass
class ValidationResult:
    """Result from validator."""
    status: str  # "success", "partial", "failure"
    issues: List[str] = field(default_factory=list)
    error: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ConversationEntry:
    """Single conversation log entry."""
    from_agent: str
    to_agent: str
    message_type: str  # instruction, response, question, answer, error, escalation, feedback
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict = field(default_factory=dict)


class RalphWiggumLoop:
    """
    Agent execution loop with retry strategies.
    Iterates until problem solved, max attempts reached, or HITL required.
    """

    DEFAULT_STRATEGIES = ["default", "simplified", "decomposed"]

    def __init__(
        self,
        max_attempts: int = 3,
        retry_strategies: Optional[List[str]] = None
    ):
        self.max_attempts = max_attempts
        self.retry_strategies = retry_strategies or self.DEFAULT_STRATEGIES
        self.conversation_log: List[ConversationEntry] = []

    async def execute_with_loop(
        self,
        agent: Any,
        task_state: Dict,
        validator: Callable[[Dict], ValidationResult]
    ) -> Tuple[LoopResult, Optional[Dict], List[ConversationEntry]]:
        """
        Execute agent in loop until success or HITL required.

        Args:
            agent: Agent instance with async run() method
            task_state: Initial task state
            validator: Async function to validate results

        Returns:
            Tuple of (LoopResult, final_state, conversation_log)
        """
        attempt = 0
        current_strategy_idx = 0
        last_result = None

        while attempt < self.max_attempts:
            attempt += 1
            strategy = self._get_strategy(current_strategy_idx)

            # Log instruction
            self._log_conversation(
                from_agent="RalphLoop",
                to_agent=getattr(agent, 'name', 'Agent'),
                message_type="instruction",
                content=f"Attempt {attempt}/{self.max_attempts}, strategy: {strategy}",
                metadata={"attempt": attempt, "strategy": strategy}
            )

            try:
                # Execute agent
                result = await agent.run(task_state, strategy=strategy)

                # Log response
                self._log_conversation(
                    from_agent=getattr(agent, 'name', 'Agent'),
                    to_agent="RalphLoop",
                    message_type="response",
                    content=result.get('summary', 'Execution completed'),
                    metadata={"attempt": attempt}
                )

                # Validate result
                validation = await self._validate(validator, result)

                if validation.status == "success":
                    self._log_conversation(
                        from_agent="Validator",
                        to_agent="RalphLoop",
                        message_type="feedback",
                        content="Validation passed. Task complete."
                    )
                    return LoopResult.SUCCESS, result, self.conversation_log

                elif validation.status == "partial":
                    last_result = result
                    current_strategy_idx += 1
                    self._log_conversation(
                        from_agent="Validator",
                        to_agent="RalphLoop",
                        message_type="feedback",
                        content=f"Partial success. Issues: {validation.issues}",
                        metadata={"issues": validation.issues}
                    )

                else:  # failure
                    current_strategy_idx += 1
                    self._log_conversation(
                        from_agent="Validator",
                        to_agent="RalphLoop",
                        message_type="error",
                        content=f"Failed. Error: {validation.error}",
                        metadata={"error": validation.error}
                    )

            except Exception as e:
                logger.exception(f"Agent execution error on attempt {attempt}")
                self._log_conversation(
                    from_agent=getattr(agent, 'name', 'Agent'),
                    to_agent="RalphLoop",
                    message_type="error",
                    content=f"Exception: {str(e)}"
                )
                current_strategy_idx += 1

        # Max attempts reached - escalate to HITL
        self._log_conversation(
            from_agent="RalphLoop",
            to_agent="HITL",
            message_type="escalation",
            content=f"Max attempts ({self.max_attempts}) reached. Human intervention required.",
            metadata={
                "attempts_made": attempt,
                "strategies_tried": self.retry_strategies[:current_strategy_idx + 1]
            }
        )

        return LoopResult.HITL_REQUIRED, last_result, self.conversation_log

    async def execute_with_hitl_guidance(
        self,
        agent: Any,
        task_state: Dict,
        validator: Callable[[Dict], ValidationResult],
        hitl_guidance: str
    ) -> Tuple[LoopResult, Optional[Dict], List[ConversationEntry]]:
        """
        Resume execution with human guidance.

        Args:
            agent: Agent instance
            task_state: Current task state
            validator: Validation function
            hitl_guidance: Human-provided guidance

        Returns:
            Tuple of (LoopResult, final_state, conversation_log)
        """
        self._log_conversation(
            from_agent="Human",
            to_agent="RalphLoop",
            message_type="answer",
            content=hitl_guidance
        )

        # Add guidance to task state
        task_state["hitl_guidance"] = hitl_guidance

        # Reset with reduced attempts after HITL
        self.max_attempts = 2
        self.conversation_log = []  # Fresh log for guided attempt

        return await self.execute_with_loop(agent, task_state, validator)

    def _get_strategy(self, idx: int) -> str:
        """Get retry strategy by index."""
        return self.retry_strategies[min(idx, len(self.retry_strategies) - 1)]

    async def _validate(
        self,
        validator: Callable,
        result: Dict
    ) -> ValidationResult:
        """Run validator on result."""
        if asyncio.iscoroutinefunction(validator):
            return await validator(result)
        return validator(result)

    def _log_conversation(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Add entry to conversation log."""
        entry = ConversationEntry(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            metadata=metadata or {}
        )
        self.conversation_log.append(entry)
        logger.debug(f"[{from_agent} -> {to_agent}] {message_type}: {content[:100]}...")

    def get_conversation_log_dict(self) -> List[Dict]:
        """Return conversation log as list of dicts."""
        return [
            {
                "from_agent": e.from_agent,
                "to_agent": e.to_agent,
                "message_type": e.message_type,
                "content": e.content,
                "timestamp": e.timestamp,
                "metadata": e.metadata
            }
            for e in self.conversation_log
        ]


# Factory function for common use case
def create_ralph_loop(
    max_attempts: int = 3,
    strategies: Optional[List[str]] = None
) -> RalphWiggumLoop:
    """Create a Ralph-wiggum loop instance."""
    return RalphWiggumLoop(
        max_attempts=max_attempts,
        retry_strategies=strategies
    )
