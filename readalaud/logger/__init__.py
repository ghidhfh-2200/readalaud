from .log_manager import (
    init_db,
    log_audit,
    log_operation,
    log_info,
    log_success,
    log_warning,
    log_error,
    log_fatal,
    log_system,
    delete_logs,
    delete_logs_by_ids,
)
from .log_viewer import show_log_viewer

def bind_logger_api(instance):
    instance.show_log_viewer = lambda: show_log_viewer(instance)
    instance.log_audit = lambda action, details="": log_audit(getattr(instance, "current_acount", "SYSTEM"), action, details)
    instance.log_operation = lambda action, details="": log_operation(getattr(instance, "current_acount", "SYSTEM"), action, details)
    instance.log_info = lambda action, details="": log_info(getattr(instance, "current_acount", "SYSTEM"), action, details)
    instance.log_success = lambda action, details="": log_success(getattr(instance, "current_acount", "SYSTEM"), action, details)
    instance.log_warning = lambda action, details="": log_warning(getattr(instance, "current_acount", "SYSTEM"), action, details)
    instance.log_error = lambda action, details="": log_error(getattr(instance, "current_acount", "SYSTEM"), action, details)
    instance.log_fatal = lambda action, details="": log_fatal(getattr(instance, "current_acount", "SYSTEM"), action, details)
    instance.log_system = lambda action, details="": log_system(action, details)

__all__ = [
    "init_db",
    "bind_logger_api",
    "log_system",
    "log_info",
    "log_success",
    "log_warning",
    "log_error",
    "log_fatal",
    "delete_logs",
    "delete_logs_by_ids",
]
