from app.core.exceptions import ApplicationError


class OrderNotFoundError(ApplicationError):
    status_code = 404
    code = "ORDER_NOT_FOUND"
    message = "订单不存在或不属于当前用户"
