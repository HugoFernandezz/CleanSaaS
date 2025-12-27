"""Centralized exception handling for the application."""

from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception for application errors."""

    pass


class NotFoundError(BaseAppException):
    """Exception raised when a resource is not found."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} with id {identifier} not found")


class ValidationError(BaseAppException):
    """Exception raised when validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def map_exception_to_http(exception: Exception) -> HTTPException:
    """
    Mapea excepciones de negocio a códigos HTTP apropiados.

    Esta función es perezosa: solo procesa cuando se necesita.
    """
    if isinstance(exception, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exception),
        )
    if isinstance(exception, ValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exception.message,
        )

    # Error genérico (no debería llegar aquí en producción)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",
    )


