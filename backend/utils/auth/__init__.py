"""Authentication utilities for SODAV Monitor."""

from .auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)

from .security import (
    verify_password as security_verify_password,
    get_password_hash as security_get_password_hash,
    create_access_token as security_create_access_token,
    get_current_user as security_get_current_user,
    oauth2_scheme
)

# Export the security functions as the primary ones
# This allows for a smooth transition from the old security module
verify_password = security_verify_password
get_password_hash = security_get_password_hash
create_access_token = security_create_access_token
get_current_user = security_get_current_user

__all__ = [
    'verify_password',
    'get_password_hash',
    'create_access_token',
    'get_current_user'
] 