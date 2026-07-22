"""Exceptions raised by the agent module."""


class AgentError(Exception):
    """Base exception for agent errors."""


class EmptyQuestionError(AgentError):
    """Raised when the question is empty."""


class AgentRoutingError(AgentError):
    """Raised when the agent cannot determine a routing strategy."""