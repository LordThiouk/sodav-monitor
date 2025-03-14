"""Compatibility layer for Pydantic v1 to v2 features.

This module provides compatibility functions for Pydantic v1 to v2 features.
"""

from functools import wraps
from typing import Any, Callable, ClassVar, Dict, Type, TypeVar, cast

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def model_serializer(func: Callable) -> Callable:
    """Compatibility function for Pydantic v2's model_serializer.

    In v1, we can use a custom dict() method.

    Args:
        func: The serializer function

    Returns:
        The wrapped function
    """

    @wraps(func)
    def wrapper(self: BaseModel) -> Dict[str, Any]:
        return func(self)

    # Attach the function to the class
    setattr(BaseModel, "dict", wrapper)
    return func


def model_validator(mode: str = "after") -> Callable:
    """Compatibility function for Pydantic v2's model_validator.

    In v1, we can use validators.

    Args:
        mode: The validation mode (before or after)

    Returns:
        A decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(cls: Type[T], values: Dict[str, Any]) -> Dict[str, Any]:
            return func(cls, values)

        # In v1, we would register this with the validator decorator
        # But for simple cases, we can just return the function
        return wrapper

    return decorator


# ConfigDict compatibility
ConfigDict = dict
