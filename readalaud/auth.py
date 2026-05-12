# backward-compat shim -- real code is in auth/
from .auth import bind_auth
__all__ = ['bind_auth']
