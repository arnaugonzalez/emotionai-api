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


def test_base_application_exception_keeps_message_and_details():
    exc = ApplicationException("boom", details={"k": "v"})
    assert str(exc) == "boom"
    assert exc.message == "boom"
    assert exc.details == {"k": "v"}


def test_specialized_exceptions_keep_specific_fields():
    assert ValidationException("invalid", field="email", value="bad").field == "email"
    assert UserNotFoundException("u1").user_id == "u1"
    assert AgentServiceException("err", agent_type="therapy").agent_type == "therapy"
    assert TaggingServiceException("err", content_type="message").content_type == "message"
    assert UserKnowledgeServiceException("err", user_id="u2").user_id == "u2"
    assert RepositoryException("err", operation="save").operation == "save"
    assert ExternalServiceException("err", service_name="openai").service_name == "openai"
    assert BusinessRuleViolationException("err", rule_name="rule_x").rule_name == "rule_x"
    assert InsufficientPermissionsException("err", required_permission="admin").required_permission == "admin"
    r = ResourceLimitExceededException("err", resource_type="tokens", limit=100)
    assert r.resource_type == "tokens"
    assert r.limit == 100
