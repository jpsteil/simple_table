from pydal.validators import IS_DATE


class IS_DATE_HTML5(IS_DATE):
    def __init__(self, error_message="Enter a valid Date"):
        super().__init__(error_message=error_message)
