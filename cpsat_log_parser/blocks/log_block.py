import typing
import abc


class LogBlock:
    def __init__(self, lines: typing.List[str]) -> None:
        self.lines = [l for l in lines if l.strip()]

    def __str__(self) -> str:
        return "\n".join(self.lines)

    def get_title(self) -> str:
        return self.lines[0] if self.lines else "UNKNOWN"

    def get_help(self) -> typing.Optional[str]:
        return None
    
    @staticmethod
    @abc.abstractmethod
    def matches(lines: typing.List[str]) -> bool:
        return True
