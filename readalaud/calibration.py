# backward-compat shim -- real code is in calibration/
from .calibration.webview_process import bind_calibration_api
from .calibration.webview_process import start_calibration

# Explicitly expose start_calibration as an attribute of this module
__all__ = ['bind_calibration_api', 'start_calibration']

# Ensure functions are available as module attributes
globals()['start_calibration'] = start_calibration
globals()['bind_calibration_api'] = bind_calibration_api

