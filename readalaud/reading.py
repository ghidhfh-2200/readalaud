# backward-compat shim -- real code is in reading/
from .reading import bind_reading_api
from .reading.session import reading_data_get_and_check, start_reading
__all__ = ['bind_reading_api', 'reading_data_get_and_check', 'start_reading']
