"""
Unit tests for the AgentPersonality value object.

Re-exports from the detailed test file in tests/domain/value_objects/.
AgentPersonality is a pure Python Enum — zero IO, zero mocks.
"""

# All tests are in tests/domain/value_objects/test_agent_personality.py.
# Import them here so pytest collects them when running tests/domain/ only.
from tests.domain.value_objects.test_agent_personality import *  # noqa: F401, F403
