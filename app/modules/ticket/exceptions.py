from app.core.exceptions import ApplicationError


class TicketNotFoundError(ApplicationError):
    status_code = 404
    code = "TICKET_NOT_FOUND"
    message = "工单不存在或不属于当前用户"


class TicketStateError(ApplicationError):
    status_code = 409
    code = "TICKET_STATE_INVALID"
    message = "工单当前状态不允许该操作"
