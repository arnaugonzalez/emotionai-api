"""
Unit tests for application layer exceptions.

Although these live in src/application/exceptions.py, the plan requests them
in tests/domain/ because they represent business rule violations — pure Python
with no framework dependencies, zero mocks needed.
"""

import pytest
from src.application.exceptions import (
    ApplicationException,
    ValidationException,
    UserNotFoundException,
    AgentServiceException,
    TaggingServiceException,
    UserKnowledgeServiceException,
    RepositoryException,
    ExternalServiceException,
    BusinessRuleViolationException,
    InsufficientPermissionsException,
    ResourceLimitExceededException,
)


# ---------------------------------------------------------------------------
# ApplicationException (base)
# ---------------------------------------------------------------------------

def test_application_exception_message():
    exc = ApplicationException("something went wrong")
    assert exc.message == "something went wrong"
    assert str(exc) == "something went wrong"


def test_application_exception_empty_details_by_default():
    exc = ApplicationException("error")
    assert exc.details == {}


def test_application_exception_with_details():
    exc = ApplicationException("error", details={"field": "email", "value": "bad"})
    assert exc.details["field"] == "email"
    assert exc.details["value"] == "bad"


def test_application_exception_is_exception():
    exc = ApplicationException("error")
    assert isinstance(exc, Exception)


def test_application_exception_can_be_raised_and_caught():
    with pytest.raises(ApplicationException) as exc_info:
        raise ApplicationException("test error")
    assert exc_info.value.message == "test error"


# ---------------------------------------------------------------------------
# ValidationException
# ---------------------------------------------------------------------------

def test_validation_exception_message():
    exc = ValidationException("email is required")
    assert exc.message == "email is required"


def test_validation_exception_inherits_application_exception():
    exc = ValidationException("invalid")
    assert isinstance(exc, ApplicationException)


def test_validation_exception_field_and_value():
    exc = ValidationException("invalid email", field="email", value="not-an-email")
    assert exc.field == "email"
    assert exc.value == "not-an-email"


def test_validation_exception_none_field_by_default():
    exc = ValidationException("error")
    assert exc.field is None
    assert exc.value is None


# ---------------------------------------------------------------------------
# UserNotFoundException
# ---------------------------------------------------------------------------

def test_user_not_found_exception_message_contains_id():
    exc = UserNotFoundException("abc-123")
    assert "abc-123" in exc.message


def test_user_not_found_exception_stores_user_id():
    exc = UserNotFoundException("abc-123")
    assert exc.user_id == "abc-123"


def test_user_not_found_exception_inherits_application_exception():
    exc = UserNotFoundException("xyz")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# AgentServiceException
# ---------------------------------------------------------------------------

def test_agent_service_exception_message():
    exc = AgentServiceException("agent failed")
    assert exc.message == "agent failed"


def test_agent_service_exception_agent_type():
    exc = AgentServiceException("failed", agent_type="therapy")
    assert exc.agent_type == "therapy"


def test_agent_service_exception_agent_type_none_by_default():
    exc = AgentServiceException("failed")
    assert exc.agent_type is None


def test_agent_service_exception_inherits_application_exception():
    exc = AgentServiceException("error")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# TaggingServiceException
# ---------------------------------------------------------------------------

def test_tagging_service_exception_message():
    exc = TaggingServiceException("tagging failed")
    assert exc.message == "tagging failed"


def test_tagging_service_exception_content_type():
    exc = TaggingServiceException("failed", content_type="message")
    assert exc.content_type == "message"


def test_tagging_service_exception_inherits_application_exception():
    exc = TaggingServiceException("error")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# UserKnowledgeServiceException
# ---------------------------------------------------------------------------

def test_user_knowledge_service_exception_message():
    exc = UserKnowledgeServiceException("knowledge error")
    assert exc.message == "knowledge error"


def test_user_knowledge_service_exception_user_id():
    exc = UserKnowledgeServiceException("error", user_id="u-001")
    assert exc.user_id == "u-001"


def test_user_knowledge_service_exception_inherits_application_exception():
    exc = UserKnowledgeServiceException("error")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# RepositoryException
# ---------------------------------------------------------------------------

def test_repository_exception_message():
    exc = RepositoryException("db error")
    assert exc.message == "db error"


def test_repository_exception_operation():
    exc = RepositoryException("db error", operation="save")
    assert exc.operation == "save"


def test_repository_exception_operation_none_by_default():
    exc = RepositoryException("error")
    assert exc.operation is None


def test_repository_exception_inherits_application_exception():
    exc = RepositoryException("error")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# ExternalServiceException
# ---------------------------------------------------------------------------

def test_external_service_exception_message():
    exc = ExternalServiceException("openai timeout")
    assert exc.message == "openai timeout"


def test_external_service_exception_service_name():
    exc = ExternalServiceException("timeout", service_name="OpenAI")
    assert exc.service_name == "OpenAI"


def test_external_service_exception_inherits_application_exception():
    exc = ExternalServiceException("error")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# BusinessRuleViolationException
# ---------------------------------------------------------------------------

def test_business_rule_violation_exception_message():
    exc = BusinessRuleViolationException("token limit exceeded")
    assert exc.message == "token limit exceeded"


def test_business_rule_violation_exception_rule_name():
    exc = BusinessRuleViolationException("exceeded", rule_name="token_budget")
    assert exc.rule_name == "token_budget"


def test_business_rule_violation_exception_inherits_application_exception():
    exc = BusinessRuleViolationException("violation")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# InsufficientPermissionsException
# ---------------------------------------------------------------------------

def test_insufficient_permissions_exception_message():
    exc = InsufficientPermissionsException("not allowed")
    assert exc.message == "not allowed"


def test_insufficient_permissions_exception_required_permission():
    exc = InsufficientPermissionsException("not allowed", required_permission="admin")
    assert exc.required_permission == "admin"


def test_insufficient_permissions_exception_inherits_application_exception():
    exc = InsufficientPermissionsException("not allowed")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# ResourceLimitExceededException
# ---------------------------------------------------------------------------

def test_resource_limit_exceeded_exception_message():
    exc = ResourceLimitExceededException("monthly limit reached")
    assert exc.message == "monthly limit reached"


def test_resource_limit_exceeded_exception_resource_type_and_limit():
    exc = ResourceLimitExceededException("limit", resource_type="tokens", limit=100000)
    assert exc.resource_type == "tokens"
    assert exc.limit == 100000


def test_resource_limit_exceeded_exception_defaults_none():
    exc = ResourceLimitExceededException("error")
    assert exc.resource_type is None
    assert exc.limit is None


def test_resource_limit_exceeded_exception_inherits_application_exception():
    exc = ResourceLimitExceededException("error")
    assert isinstance(exc, ApplicationException)


# ---------------------------------------------------------------------------
# Exception hierarchy — all subclasses catchable as ApplicationException
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exc_class,args", [
    (ValidationException, ("validation error",)),
    (UserNotFoundException, ("user-id-1",)),
    (AgentServiceException, ("agent error",)),
    (TaggingServiceException, ("tagging error",)),
    (UserKnowledgeServiceException, ("knowledge error",)),
    (RepositoryException, ("repo error",)),
    (ExternalServiceException, ("external error",)),
    (BusinessRuleViolationException, ("rule error",)),
    (InsufficientPermissionsException, ("perm error",)),
    (ResourceLimitExceededException, ("limit error",)),
])
def test_all_exceptions_catchable_as_application_exception(exc_class, args):
    with pytest.raises(ApplicationException):
        raise exc_class(*args)
