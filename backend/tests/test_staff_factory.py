"""
Comprehensive Unit Tests for Staff Agent Factory

Target Coverage:
- StaffAgentFactory class methods
- StaffAgentType enum
- Agent creation (individual, all, by task)
- Caching behavior
- Error handling
- Convenience functions

Coverage Target: 80%+
Test Count: 40+ tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.agents.staff_factory import (
    StaffAgentFactory,
    StaffAgentType,
    StaffAgent,
    get_factory,
    create_staff_agent,
    _default_factory,
)
from src.agents.staff_agents import (
    ExcelParserAgent,
    StandardRetrieverAgent,
    VouchingAssistantAgent,
    WorkPaperGeneratorAgent,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def factory() -> StaffAgentFactory:
    """Create a fresh StaffAgentFactory for testing."""
    return StaffAgentFactory(default_model="gpt-4o-test")


@pytest.fixture
def mock_llm():
    """Mock LLM for agent initialization."""
    with patch("src.agents.staff_agents.ChatOpenAI") as mock:
        mock.return_value = MagicMock()
        yield mock


# ============================================================================
# TEST: StaffAgentType ENUM
# ============================================================================

class TestStaffAgentType:
    """Tests for the StaffAgentType enumeration."""

    def test_enum_values_exist(self):
        """Test that all expected enum values exist."""
        assert hasattr(StaffAgentType, "EXCEL_PARSER")
        assert hasattr(StaffAgentType, "STANDARD_RETRIEVER")
        assert hasattr(StaffAgentType, "VOUCHING_ASSISTANT")
        assert hasattr(StaffAgentType, "WORKPAPER_GENERATOR")

    def test_enum_values_are_strings(self):
        """Test that enum values are strings."""
        assert StaffAgentType.EXCEL_PARSER.value == "excel_parser"
        assert StaffAgentType.STANDARD_RETRIEVER.value == "standard_retriever"
        assert StaffAgentType.VOUCHING_ASSISTANT.value == "vouching_assistant"
        assert StaffAgentType.WORKPAPER_GENERATOR.value == "workpaper_generator"

    def test_enum_count(self):
        """Test that we have exactly 4 agent types."""
        assert len(list(StaffAgentType)) == 4

    def test_enum_is_string_subclass(self):
        """Test that enum values work as strings."""
        assert isinstance(StaffAgentType.EXCEL_PARSER, str)
        assert StaffAgentType.EXCEL_PARSER == "excel_parser"

    def test_enum_from_string(self):
        """Test creating enum from string value."""
        agent_type = StaffAgentType("excel_parser")
        assert agent_type == StaffAgentType.EXCEL_PARSER

    def test_enum_invalid_value_raises(self):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            StaffAgentType("invalid_type")


# ============================================================================
# TEST: StaffAgentFactory INITIALIZATION
# ============================================================================

class TestStaffAgentFactoryInit:
    """Tests for StaffAgentFactory initialization."""

    def test_factory_creates_with_default_model(self):
        """Test factory initializes with default model."""
        factory = StaffAgentFactory()
        assert factory.default_model == "gpt-4o"

    def test_factory_creates_with_custom_model(self):
        """Test factory initializes with custom model."""
        factory = StaffAgentFactory(default_model="gpt-4")
        assert factory.default_model == "gpt-4"

    def test_factory_starts_with_empty_cache(self):
        """Test factory starts with no cached agents."""
        factory = StaffAgentFactory()
        assert len(factory._created_agents) == 0

    def test_factory_has_agent_registry(self):
        """Test factory has all agent types in registry."""
        factory = StaffAgentFactory()
        assert len(factory._AGENT_REGISTRY) == 4

    def test_factory_has_agent_descriptions(self):
        """Test factory has descriptions for all types."""
        factory = StaffAgentFactory()
        for agent_type in StaffAgentType:
            assert agent_type in factory._AGENT_DESCRIPTIONS


# ============================================================================
# TEST: create_agent() METHOD
# ============================================================================

class TestCreateAgent:
    """Tests for the create_agent() method."""

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_excel_parser(self, mock_llm, factory):
        """Test creating ExcelParserAgent."""
        agent = factory.create_agent(StaffAgentType.EXCEL_PARSER)
        assert isinstance(agent, ExcelParserAgent)
        assert agent.agent_name == "Staff_Excel_Parser"

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_standard_retriever(self, mock_llm, factory):
        """Test creating StandardRetrieverAgent."""
        agent = factory.create_agent(StaffAgentType.STANDARD_RETRIEVER)
        assert isinstance(agent, StandardRetrieverAgent)
        assert agent.agent_name == "Staff_Standard_Retriever"

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_vouching_assistant(self, mock_llm, factory):
        """Test creating VouchingAssistantAgent."""
        agent = factory.create_agent(StaffAgentType.VOUCHING_ASSISTANT)
        assert isinstance(agent, VouchingAssistantAgent)
        assert agent.agent_name == "Staff_Vouching_Assistant"

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_workpaper_generator(self, mock_llm, factory):
        """Test creating WorkPaperGeneratorAgent."""
        agent = factory.create_agent(StaffAgentType.WORKPAPER_GENERATOR)
        assert isinstance(agent, WorkPaperGeneratorAgent)
        assert agent.agent_name == "Staff_WorkPaper_Generator"

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_with_custom_model(self, mock_llm, factory):
        """Test creating agent with custom model."""
        factory.create_agent(StaffAgentType.EXCEL_PARSER, model_name="gpt-4")
        mock_llm.assert_called_with(model="gpt-4")

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_with_default_model(self, mock_llm, factory):
        """Test creating agent uses factory default model."""
        factory.create_agent(StaffAgentType.EXCEL_PARSER)
        mock_llm.assert_called_with(model="gpt-4o-test")

    def test_create_invalid_type_raises_typeerror(self, factory):
        """Test that passing non-enum type raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            factory.create_agent("excel_parser")  # type: ignore
        assert "StaffAgentType enum" in str(exc_info.value)

    def test_create_none_type_raises_typeerror(self, factory):
        """Test that passing None raises TypeError."""
        with pytest.raises(TypeError):
            factory.create_agent(None)  # type: ignore


# ============================================================================
# TEST: CACHING BEHAVIOR
# ============================================================================

class TestCaching:
    """Tests for agent caching behavior."""

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_cache_disabled_creates_new_instances(self, mock_llm, factory):
        """Test that caching disabled creates new instances each time."""
        agent1 = factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=False)
        agent2 = factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=False)
        assert agent1 is not agent2

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_cache_enabled_returns_same_instance(self, mock_llm, factory):
        """Test that caching enabled returns same instance."""
        agent1 = factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=True)
        agent2 = factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=True)
        assert agent1 is agent2

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_clear_cache_removes_instances(self, mock_llm, factory):
        """Test that clear_cache removes cached instances."""
        factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=True)
        assert len(factory._created_agents) == 1

        factory.clear_cache()
        assert len(factory._created_agents) == 0

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_different_types_cached_separately(self, mock_llm, factory):
        """Test that different agent types are cached separately."""
        agent1 = factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=True)
        agent2 = factory.create_agent(StaffAgentType.VOUCHING_ASSISTANT, cache=True)

        assert len(factory._created_agents) == 2
        assert agent1 is not agent2


# ============================================================================
# TEST: get_agent() METHOD (STRING-BASED)
# ============================================================================

class TestGetAgent:
    """Tests for the get_agent() string-based method."""

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_get_agent_by_string(self, mock_llm, factory):
        """Test getting agent by string identifier."""
        agent = factory.get_agent("excel_parser")
        assert isinstance(agent, ExcelParserAgent)

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_get_agent_case_insensitive(self, mock_llm, factory):
        """Test that get_agent is case insensitive."""
        agent1 = factory.get_agent("EXCEL_PARSER")
        agent2 = factory.get_agent("Excel_Parser")
        assert isinstance(agent1, ExcelParserAgent)
        assert isinstance(agent2, ExcelParserAgent)

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_get_agent_strips_whitespace(self, mock_llm, factory):
        """Test that get_agent strips whitespace."""
        agent = factory.get_agent("  excel_parser  ")
        assert isinstance(agent, ExcelParserAgent)

    def test_get_agent_invalid_string_raises(self, factory):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            factory.get_agent("invalid_agent")
        assert "Invalid agent type string" in str(exc_info.value)
        assert "Available types" in str(exc_info.value)

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_get_agent_with_model(self, mock_llm, factory):
        """Test get_agent with custom model."""
        factory.get_agent("excel_parser", model_name="gpt-4")
        mock_llm.assert_called_with(model="gpt-4")


# ============================================================================
# TEST: create_all_agents() METHOD
# ============================================================================

class TestCreateAllAgents:
    """Tests for the create_all_agents() method."""

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_all_returns_all_types(self, mock_llm, factory):
        """Test that create_all_agents returns all 4 agent types."""
        agents = factory.create_all_agents()
        assert len(agents) == 4
        assert StaffAgentType.EXCEL_PARSER in agents
        assert StaffAgentType.STANDARD_RETRIEVER in agents
        assert StaffAgentType.VOUCHING_ASSISTANT in agents
        assert StaffAgentType.WORKPAPER_GENERATOR in agents

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_all_correct_types(self, mock_llm, factory):
        """Test that create_all_agents returns correct agent types."""
        agents = factory.create_all_agents()
        assert isinstance(agents[StaffAgentType.EXCEL_PARSER], ExcelParserAgent)
        assert isinstance(agents[StaffAgentType.STANDARD_RETRIEVER], StandardRetrieverAgent)
        assert isinstance(agents[StaffAgentType.VOUCHING_ASSISTANT], VouchingAssistantAgent)
        assert isinstance(agents[StaffAgentType.WORKPAPER_GENERATOR], WorkPaperGeneratorAgent)

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_all_caches_by_default(self, mock_llm, factory):
        """Test that create_all_agents caches agents by default."""
        factory.create_all_agents()
        assert len(factory._created_agents) == 4

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_all_no_cache_option(self, mock_llm, factory):
        """Test create_all_agents with cache disabled."""
        factory.create_all_agents(cache=False)
        assert len(factory._created_agents) == 0


# ============================================================================
# TEST: create_agents_for_task() METHOD
# ============================================================================

class TestCreateAgentsForTask:
    """Tests for the create_agents_for_task() method."""

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_subset_of_agents(self, mock_llm, factory):
        """Test creating a subset of agents for a task."""
        agents = factory.create_agents_for_task([
            StaffAgentType.EXCEL_PARSER,
            StaffAgentType.VOUCHING_ASSISTANT,
        ])
        assert len(agents) == 2
        assert StaffAgentType.EXCEL_PARSER in agents
        assert StaffAgentType.VOUCHING_ASSISTANT in agents

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_single_agent_for_task(self, mock_llm, factory):
        """Test creating single agent for task."""
        agents = factory.create_agents_for_task([StaffAgentType.EXCEL_PARSER])
        assert len(agents) == 1
        assert isinstance(agents[StaffAgentType.EXCEL_PARSER], ExcelParserAgent)

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_empty_list_for_task(self, mock_llm, factory):
        """Test creating with empty list."""
        agents = factory.create_agents_for_task([])
        assert len(agents) == 0


# ============================================================================
# TEST: CLASS METHODS
# ============================================================================

class TestClassMethods:
    """Tests for class-level methods."""

    def test_get_available_types(self):
        """Test get_available_types returns all types."""
        types = StaffAgentFactory.get_available_types()
        assert len(types) == 4
        assert all(isinstance(t, StaffAgentType) for t in types)

    def test_get_agent_description(self):
        """Test get_agent_description returns description."""
        desc = StaffAgentFactory.get_agent_description(StaffAgentType.EXCEL_PARSER)
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_get_agent_description_invalid_raises(self):
        """Test get_agent_description with invalid type raises."""
        with pytest.raises(ValueError):
            StaffAgentFactory.get_agent_description("invalid")  # type: ignore

    def test_get_agent_class(self):
        """Test get_agent_class returns correct class."""
        agent_class = StaffAgentFactory.get_agent_class(StaffAgentType.EXCEL_PARSER)
        assert agent_class == ExcelParserAgent

    def test_get_agent_class_invalid_raises(self):
        """Test get_agent_class with invalid type raises."""
        with pytest.raises(ValueError):
            StaffAgentFactory.get_agent_class("invalid")  # type: ignore

    def test_type_from_string(self):
        """Test type_from_string converts correctly."""
        agent_type = StaffAgentFactory.type_from_string("excel_parser")
        assert agent_type == StaffAgentType.EXCEL_PARSER

    def test_type_from_string_case_insensitive(self):
        """Test type_from_string is case insensitive."""
        agent_type = StaffAgentFactory.type_from_string("EXCEL_PARSER")
        assert agent_type == StaffAgentType.EXCEL_PARSER

    def test_type_from_string_invalid_raises(self):
        """Test type_from_string with invalid string raises."""
        with pytest.raises(ValueError) as exc_info:
            StaffAgentFactory.type_from_string("invalid")
        assert "Invalid agent type string" in str(exc_info.value)


# ============================================================================
# TEST: CONVENIENCE FUNCTIONS
# ============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_factory_creates_factory(self):
        """Test get_factory creates a factory instance."""
        # Reset module state
        import src.agents.staff_factory as sf
        sf._default_factory = None

        factory = get_factory()
        assert isinstance(factory, StaffAgentFactory)

    def test_get_factory_returns_singleton(self):
        """Test get_factory returns same instance."""
        import src.agents.staff_factory as sf
        sf._default_factory = None

        factory1 = get_factory()
        factory2 = get_factory()
        assert factory1 is factory2

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_staff_agent_with_enum(self, mock_llm):
        """Test create_staff_agent with enum type."""
        agent = create_staff_agent(StaffAgentType.EXCEL_PARSER)
        assert isinstance(agent, ExcelParserAgent)

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_staff_agent_with_string(self, mock_llm):
        """Test create_staff_agent with string type."""
        agent = create_staff_agent("vouching_assistant")
        assert isinstance(agent, VouchingAssistantAgent)

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_staff_agent_with_model(self, mock_llm):
        """Test create_staff_agent with custom model."""
        create_staff_agent(StaffAgentType.EXCEL_PARSER, model_name="gpt-4")
        mock_llm.assert_called_with(model="gpt-4")


# ============================================================================
# TEST: INTEGRATION SCENARIOS
# ============================================================================

class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_audit_workflow_agent_creation(self, mock_llm, factory):
        """Test creating agents for a typical audit workflow."""
        # Phase 1: Excel parsing
        excel_agent = factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=True)
        assert isinstance(excel_agent, ExcelParserAgent)

        # Phase 2: Standard retrieval
        retriever_agent = factory.create_agent(StaffAgentType.STANDARD_RETRIEVER, cache=True)
        assert isinstance(retriever_agent, StandardRetrieverAgent)

        # Phase 3: Vouching
        vouching_agent = factory.create_agent(StaffAgentType.VOUCHING_ASSISTANT, cache=True)
        assert isinstance(vouching_agent, VouchingAssistantAgent)

        # Phase 4: Workpaper generation
        workpaper_agent = factory.create_agent(StaffAgentType.WORKPAPER_GENERATOR, cache=True)
        assert isinstance(workpaper_agent, WorkPaperGeneratorAgent)

        # All 4 agents should be cached
        assert len(factory._created_agents) == 4

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_dynamic_agent_allocation(self, mock_llm, factory):
        """Test dynamic agent allocation based on task requirements."""
        # Simulate Manager agent determining required staff
        required_types_from_task = ["excel_parser", "vouching_assistant"]

        agents = {}
        for type_str in required_types_from_task:
            agents[type_str] = factory.get_agent(type_str)

        assert len(agents) == 2
        assert "excel_parser" in agents
        assert "vouching_assistant" in agents

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_factory_reuse_across_tasks(self, mock_llm, factory):
        """Test factory reuse across multiple tasks."""
        # Task 1: Sales audit
        task1_agents = factory.create_agents_for_task([
            StaffAgentType.EXCEL_PARSER,
            StaffAgentType.STANDARD_RETRIEVER,
        ], cache=True)

        # Task 2: Inventory audit
        task2_agents = factory.create_agents_for_task([
            StaffAgentType.EXCEL_PARSER,  # Should reuse cached
            StaffAgentType.VOUCHING_ASSISTANT,
        ], cache=True)

        # Excel parser should be same instance
        assert task1_agents[StaffAgentType.EXCEL_PARSER] is task2_agents[StaffAgentType.EXCEL_PARSER]

        # Total 3 unique agents created
        assert len(factory._created_agents) == 3


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_invalid_enum_value_error_message(self, factory):
        """Test that error message for invalid type is helpful."""
        with pytest.raises(TypeError) as exc_info:
            factory.create_agent(123)  # type: ignore
        error_message = str(exc_info.value)
        assert "StaffAgentType enum" in error_message

    def test_invalid_string_error_includes_available(self, factory):
        """Test that error for invalid string includes available types."""
        with pytest.raises(ValueError) as exc_info:
            factory.get_agent("nonexistent_agent")
        error_message = str(exc_info.value)
        assert "excel_parser" in error_message
        assert "Available types" in error_message

    def test_type_from_string_error_is_descriptive(self):
        """Test that type_from_string error is descriptive."""
        with pytest.raises(ValueError) as exc_info:
            StaffAgentFactory.type_from_string("bad_type")
        error_message = str(exc_info.value)
        assert "Invalid agent type string" in error_message
        assert "bad_type" in error_message


# ============================================================================
# TEST: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_create_same_type_multiple_times_no_cache(self, mock_llm, factory):
        """Test creating same type multiple times without cache."""
        agents = [
            factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=False)
            for _ in range(5)
        ]
        # All should be different instances
        for i, agent1 in enumerate(agents):
            for agent2 in agents[i+1:]:
                assert agent1 is not agent2

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_clear_cache_then_recreate(self, mock_llm, factory):
        """Test that agents can be recreated after cache clear."""
        agent1 = factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=True)
        factory.clear_cache()
        agent2 = factory.create_agent(StaffAgentType.EXCEL_PARSER, cache=True)

        assert agent1 is not agent2

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_empty_string_type_raises(self, mock_llm, factory):
        """Test that empty string raises appropriate error."""
        with pytest.raises(ValueError):
            factory.get_agent("")

    @patch("src.agents.staff_agents.ChatOpenAI")
    def test_whitespace_only_string_raises(self, mock_llm, factory):
        """Test that whitespace-only string raises error."""
        with pytest.raises(ValueError):
            factory.get_agent("   ")
