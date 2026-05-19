from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Standard envelope for all API responses."""

    result: T | None = None
    status_code: int
    message: str | None = None
    success: bool | None = None


def success_response(
    result: T | None = None, message: str = "Success", status_code: int = 200
) -> BaseResponse[T]:
    return BaseResponse(
        result=result,
        status_code=status_code,
        message=message or "Success",
        success=True,
    )


def error_response(
    message: str = "Something went wrong", status_code: int = 500
) -> BaseResponse[None]:
    return BaseResponse(
        result=None,
        status_code=status_code,
        message=message or "Something went wrong",
        success=False,
    )
