import sys
from types import TracebackType
from typing import Any, Optional


def error_message_detail(error: Exception | str, error_detail: Optional[Any] = None) -> str:
    """
    Extracts detailed error information including file name, line number, and error message.

    Args:
        error: The exception instance or error message string.
        error_detail: Optional reference to `sys`, an `exc_info` tuple, or `sys.exc_info()` by default.

    Returns:
        A formatted error message string.
    """
    exc_tb: Optional[TracebackType] = None

    try:
        if error_detail is not None:
            # إذا تم تمرير وحدة sys
            if hasattr(error_detail, "exc_info") and callable(error_detail.exc_info):
                _, _, exc_tb = error_detail.exc_info()
            # إذا تم تمرير tuple الخاصة بـ sys.exc_info()
            elif isinstance(error_detail, tuple) and len(error_detail) == 3:
                _, _, exc_tb = error_detail

        # إذا لم يتم العثور على traceback من error_detail، نحاول الحصول عليه من الحالة الحالية
        if exc_tb is None:
            _, _, exc_tb = sys.exc_info()

    except Exception:
        exc_tb = None

    if exc_tb is not None:
        file_name = exc_tb.tb_frame.f_code.co_filename
        line_number = exc_tb.tb_lineno
        return (
            f"Error occurred in script: [{file_name}] "
            f"at line number: [{line_number}] "
            f"error message: [{str(error)}]"
        )

    return f"Error occurred: [{str(error)}]"


class CustomException(Exception):
    """
    Custom exception class designed to capture file name, line number,
    and detailed traceback information.
    """

    def __init__(self, error_message: Exception | str, error_detail: Optional[Any] = None):
        super().__init__(str(error_message))
        self.error_message = error_message_detail(error_message, error_detail=error_detail)

    def __str__(self) -> str:
        return self.error_message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.error_message!r})"
