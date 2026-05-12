# backward-compat shim -- real code is in settings/
from .settings import bind_settings
from .settings.settings_io import _load_settings
__all__ = ['bind_settings', '_load_settings']
