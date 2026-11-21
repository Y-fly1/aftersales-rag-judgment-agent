from app.core.exceptions import ApplicationError


class PolicyNotFoundError(ApplicationError):
    status_code = 404
    code = "POLICY_NOT_FOUND"
    message = "政策不存在"
