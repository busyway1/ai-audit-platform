"""
Staff Agent Factory for AI Audit Platform

This module implements the Factory pattern for creating specialized Staff agents.
The factory provides a centralized way to instantiate Staff agents based on type,
supporting dynamic agent allocation by the Manager agent.

Staff Agent Types:
1. ExcelParserAgent: Parse Excel files and extract financial data
2. StandardRetrieverAgent: RAG-based standard retrieval (K-IFRS/K-GAAS)
3. VouchingAssistantAgent: Perform vouching procedures with LLM reasoning
4. WorkPaperGeneratorAgent: Generate audit workpaper drafts

Reference:
- Specification: Section 4.3 (Agent Personas and Prompts)
- Manager Agent: backend/src/agents/manager_agent.py (StaffType enum)
- Staff Agents: backend/src/agents/staff_agents.py
"""

from typing import Dict, Any, List, Optional, Type, Union
from enum import Enum
import logging

from .staff_agents import (
    ExcelParserAgent,
    StandardRetrieverAgent,
    VouchingAssistantAgent,
    WorkPaperGeneratorAgent,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# STAFF AGENT TYPE ENUM
# ============================================================================

class StaffAgentType(str, Enum):
    """
    Enumeration of available Staff agent types.

    This enum mirrors StaffType from manager_agent.py but is specific to
    the factory pattern. Use this enum when requesting agent creation.

    Values match the naming convention: snake_case for consistency with
    StaffType in manager_agent.py.
    """
    EXCEL_PARSER = "excel_parser"
    STANDARD_RETRIEVER = "standard_retriever"
    VOUCHING_ASSISTANT = "vouching_assistant"
    WORKPAPER_GENERATOR = "workpaper_generator"


# Type alias for any Staff agent instance
StaffAgent = Union[
    ExcelParserAgent,
    StandardRetrieverAgent,
    VouchingAssistantAgent,
    WorkPaperGeneratorAgent,
]


# ============================================================================
# STAFF AGENT FACTORY
# ============================================================================

class StaffAgentFactory:
    """
    Factory class for creating specialized Staff agents.

    This factory provides centralized agent instantiation with:
    - Type-safe agent creation via enum
    - Consistent model configuration across agents
    - Agent registry for validation and introspection
    - Error handling for invalid agent types

    Usage:
        factory = StaffAgentFactory()

        # Create single agent
        excel_agent = factory.create_agent(StaffAgentType.EXCEL_PARSER)

        # Create agent with custom model
        vouching_agent = factory.create_agent(
            StaffAgentType.VOUCHING_ASSISTANT,
            model_name="gpt-4"
        )

        # Create all agents
        all_agents = factory.create_all_agents()

        # Get agent by string type (for dynamic allocation)
        agent = factory.get_agent("excel_parser")
    """

    # Registry mapping agent types to their classes
    _AGENT_REGISTRY: Dict[StaffAgentType, Type[StaffAgent]] = {
        StaffAgentType.EXCEL_PARSER: ExcelParserAgent,
        StaffAgentType.STANDARD_RETRIEVER: StandardRetrieverAgent,
        StaffAgentType.VOUCHING_ASSISTANT: VouchingAssistantAgent,
        StaffAgentType.WORKPAPER_GENERATOR: WorkPaperGeneratorAgent,
    }

    # Agent descriptions for documentation and logging
    _AGENT_DESCRIPTIONS: Dict[StaffAgentType, str] = {
        StaffAgentType.EXCEL_PARSER: "Parse Excel files and extract financial data",
        StaffAgentType.STANDARD_RETRIEVER: "RAG-based K-IFRS/K-GAAS standard retrieval",
        StaffAgentType.VOUCHING_ASSISTANT: "Perform vouching procedures with LLM reasoning",
        StaffAgentType.WORKPAPER_GENERATOR: "Generate audit workpaper drafts",
    }

    def __init__(self, default_model: str = "gpt-4o"):
        """
        Initialize the Staff Agent Factory.

        Args:
            default_model: Default LLM model to use for agent initialization.
                          Individual agents can override this at creation time.
        """
        self.default_model = default_model
        self._created_agents: Dict[StaffAgentType, StaffAgent] = {}
        logger.info(f"StaffAgentFactory initialized with default model: {default_model}")

    def create_agent(
        self,
        agent_type: StaffAgentType,
        model_name: Optional[str] = None,
        cache: bool = False,
    ) -> StaffAgent:
        """
        Create a Staff agent of the specified type.

        Args:
            agent_type: The type of Staff agent to create (StaffAgentType enum)
            model_name: Optional model name override. If None, uses factory default.
            cache: If True, caches the created agent for reuse. Default False.

        Returns:
            Instance of the requested Staff agent type

        Raises:
            ValueError: If agent_type is not a valid StaffAgentType
            TypeError: If agent_type is not a StaffAgentType enum

        Example:
            >>> factory = StaffAgentFactory()
            >>> agent = factory.create_agent(StaffAgentType.EXCEL_PARSER)
            >>> isinstance(agent, ExcelParserAgent)
            True
        """
        # Validate agent type
        if not isinstance(agent_type, StaffAgentType):
            raise TypeError(
                f"agent_type must be a StaffAgentType enum, got {type(agent_type).__name__}"
            )

        if agent_type not in self._AGENT_REGISTRY:
            raise ValueError(
                f"Unknown agent type: {agent_type}. "
                f"Available types: {[t.value for t in StaffAgentType]}"
            )

        # Check cache if enabled
        if cache and agent_type in self._created_agents:
            logger.debug(f"Returning cached {agent_type.value} agent")
            return self._created_agents[agent_type]

        # Determine model to use
        model = model_name or self.default_model

        # Get agent class and create instance
        agent_class = self._AGENT_REGISTRY[agent_type]
        agent = agent_class(model_name=model)

        logger.info(
            f"Created {agent_type.value} agent with model {model}. "
            f"Description: {self._AGENT_DESCRIPTIONS.get(agent_type, 'N/A')}"
        )

        # Cache if requested
        if cache:
            self._created_agents[agent_type] = agent

        return agent

    def get_agent(
        self,
        agent_type_str: str,
        model_name: Optional[str] = None,
        cache: bool = False,
    ) -> StaffAgent:
        """
        Create a Staff agent from a string type identifier.

        This method is useful for dynamic agent allocation where the agent
        type is determined at runtime (e.g., from task requirements).

        Args:
            agent_type_str: String identifier for the agent type.
                           Must match one of StaffAgentType values.
            model_name: Optional model name override.
            cache: If True, caches the created agent for reuse.

        Returns:
            Instance of the requested Staff agent type

        Raises:
            ValueError: If agent_type_str is not a valid agent type string

        Example:
            >>> factory = StaffAgentFactory()
            >>> agent = factory.get_agent("excel_parser")
            >>> isinstance(agent, ExcelParserAgent)
            True
        """
        # Normalize input
        normalized = agent_type_str.lower().strip()

        # Try to convert string to enum
        try:
            agent_type = StaffAgentType(normalized)
        except ValueError:
            available = [t.value for t in StaffAgentType]
            raise ValueError(
                f"Invalid agent type string: '{agent_type_str}'. "
                f"Available types: {available}"
            )

        return self.create_agent(agent_type, model_name, cache)

    def create_all_agents(
        self,
        model_name: Optional[str] = None,
        cache: bool = True,
    ) -> Dict[StaffAgentType, StaffAgent]:
        """
        Create instances of all available Staff agent types.

        This method is useful when you need to initialize the full
        Staff agent pool for a workflow.

        Args:
            model_name: Optional model name to use for all agents.
                       If None, uses factory default.
            cache: If True (default), caches all created agents.

        Returns:
            Dictionary mapping agent types to their instances

        Example:
            >>> factory = StaffAgentFactory()
            >>> agents = factory.create_all_agents()
            >>> len(agents)
            4
            >>> StaffAgentType.EXCEL_PARSER in agents
            True
        """
        agents: Dict[StaffAgentType, StaffAgent] = {}

        for agent_type in StaffAgentType:
            agents[agent_type] = self.create_agent(agent_type, model_name, cache)

        logger.info(f"Created all {len(agents)} Staff agents")
        return agents

    def create_agents_for_task(
        self,
        required_types: List[StaffAgentType],
        model_name: Optional[str] = None,
        cache: bool = False,
    ) -> Dict[StaffAgentType, StaffAgent]:
        """
        Create a subset of Staff agents required for a specific task.

        This method supports selective agent creation based on task
        requirements, as determined by the Manager agent's allocation logic.

        Args:
            required_types: List of agent types needed for the task
            model_name: Optional model name to use for all agents
            cache: If True, caches the created agents

        Returns:
            Dictionary mapping requested agent types to their instances

        Raises:
            ValueError: If any type in required_types is invalid

        Example:
            >>> factory = StaffAgentFactory()
            >>> agents = factory.create_agents_for_task([
            ...     StaffAgentType.EXCEL_PARSER,
            ...     StaffAgentType.VOUCHING_ASSISTANT
            ... ])
            >>> len(agents)
            2
        """
        agents: Dict[StaffAgentType, StaffAgent] = {}

        for agent_type in required_types:
            agents[agent_type] = self.create_agent(agent_type, model_name, cache)

        logger.info(
            f"Created {len(agents)} Staff agents for task: "
            f"{[t.value for t in required_types]}"
        )
        return agents

    def clear_cache(self) -> None:
        """
        Clear all cached agent instances.

        Call this method to force fresh agent creation on subsequent
        calls when caching is enabled.
        """
        count = len(self._created_agents)
        self._created_agents.clear()
        logger.info(f"Cleared {count} cached agent instances")

    @classmethod
    def get_available_types(cls) -> List[StaffAgentType]:
        """
        Get a list of all available Staff agent types.

        Returns:
            List of all StaffAgentType enum values

        Example:
            >>> types = StaffAgentFactory.get_available_types()
            >>> StaffAgentType.EXCEL_PARSER in types
            True
        """
        return list(StaffAgentType)

    @classmethod
    def get_agent_description(cls, agent_type: StaffAgentType) -> str:
        """
        Get the description for a specific agent type.

        Args:
            agent_type: The agent type to get description for

        Returns:
            Description string for the agent type

        Raises:
            ValueError: If agent_type is not valid
        """
        if agent_type not in cls._AGENT_DESCRIPTIONS:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return cls._AGENT_DESCRIPTIONS[agent_type]

    @classmethod
    def get_agent_class(cls, agent_type: StaffAgentType) -> Type[StaffAgent]:
        """
        Get the class for a specific agent type without instantiation.

        Args:
            agent_type: The agent type to get class for

        Returns:
            The agent class (not an instance)

        Raises:
            ValueError: If agent_type is not valid
        """
        if agent_type not in cls._AGENT_REGISTRY:
            raise ValueError(f"Unknown agent type: {agent_type}")
        return cls._AGENT_REGISTRY[agent_type]

    @staticmethod
    def type_from_string(type_string: str) -> StaffAgentType:
        """
        Convert a string to StaffAgentType enum.

        Utility method for converting string identifiers to enums
        with proper error handling.

        Args:
            type_string: String representation of agent type

        Returns:
            Corresponding StaffAgentType enum value

        Raises:
            ValueError: If string doesn't match any agent type
        """
        normalized = type_string.lower().strip()
        try:
            return StaffAgentType(normalized)
        except ValueError:
            available = [t.value for t in StaffAgentType]
            raise ValueError(
                f"Invalid agent type string: '{type_string}'. "
                f"Available types: {available}"
            )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Module-level factory instance for convenience
_default_factory: Optional[StaffAgentFactory] = None


def get_factory(default_model: str = "gpt-4o") -> StaffAgentFactory:
    """
    Get or create the default Staff Agent Factory instance.

    This function provides a singleton-like access pattern for the factory,
    avoiding repeated instantiation in workflows.

    Args:
        default_model: Model to use if creating a new factory instance

    Returns:
        StaffAgentFactory instance

    Example:
        >>> factory = get_factory()
        >>> agent = factory.create_agent(StaffAgentType.EXCEL_PARSER)
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = StaffAgentFactory(default_model=default_model)
    return _default_factory


def create_staff_agent(
    agent_type: Union[StaffAgentType, str],
    model_name: Optional[str] = None,
) -> StaffAgent:
    """
    Convenience function to create a Staff agent without explicit factory.

    This is a shortcut for common use cases where you just need to create
    a single agent without managing the factory instance.

    Args:
        agent_type: Either StaffAgentType enum or string identifier
        model_name: Optional model name override

    Returns:
        Instance of the requested Staff agent type

    Example:
        >>> agent = create_staff_agent(StaffAgentType.EXCEL_PARSER)
        >>> # Or with string:
        >>> agent = create_staff_agent("vouching_assistant")
    """
    factory = get_factory()

    if isinstance(agent_type, str):
        return factory.get_agent(agent_type, model_name)
    else:
        return factory.create_agent(agent_type, model_name)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def demo_factory():
        """Demonstrate Staff Agent Factory usage."""

        print("=== Staff Agent Factory Demo ===\n")

        # 1. Create factory
        factory = StaffAgentFactory(default_model="gpt-4o")

        # 2. List available agent types
        print("Available agent types:")
        for agent_type in factory.get_available_types():
            desc = factory.get_agent_description(agent_type)
            print(f"  - {agent_type.value}: {desc}")

        print()

        # 3. Create individual agent
        print("Creating Excel Parser agent...")
        excel_agent = factory.create_agent(StaffAgentType.EXCEL_PARSER)
        print(f"  Created: {excel_agent.agent_name}")

        # 4. Create agent from string
        print("\nCreating agent from string 'vouching_assistant'...")
        vouching_agent = factory.get_agent("vouching_assistant")
        print(f"  Created: {vouching_agent.agent_name}")

        # 5. Create all agents
        print("\nCreating all agents...")
        all_agents = factory.create_all_agents()
        for agent_type, agent in all_agents.items():
            print(f"  {agent_type.value}: {agent.agent_name}")

        # 6. Create agents for specific task
        print("\nCreating agents for task (parser + retriever)...")
        task_agents = factory.create_agents_for_task([
            StaffAgentType.EXCEL_PARSER,
            StaffAgentType.STANDARD_RETRIEVER,
        ])
        for agent_type, agent in task_agents.items():
            print(f"  {agent_type.value}: {agent.agent_name}")

        # 7. Test convenience function
        print("\nUsing convenience function...")
        agent = create_staff_agent("workpaper_generator")
        print(f"  Created: {agent.agent_name}")

        print("\n=== Demo Complete ===")

    asyncio.run(demo_factory())
