from .severity import Severity


class CheckException(Exception):
    """CheckException is the basic check exception."""
    def __init__(self, msg: str, severity: Severity = Severity.MEDIUM):
        assert msg, 'CheckException message must not be empty'
        self.severity = severity
        super().__init__(msg)

    def to_dict(self):
        return {
            "error": self.__str__(),
            "severity": self.severity.value
        }


class NoCountException(Exception):  # Only to be used within CheckBase
    """NoCountException must ONLY be raised withing non-multi CheckBase class!!
    This exception cannot be used with CheckBaseMulti;
    """
    def __init__(self, result: dict):
        assert isinstance(result, dict)
        self.result = result
        super().__init__('No count exception')
