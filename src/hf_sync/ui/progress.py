"""Progress tracking for pipeline stages."""


class ProgressTracker:
    """Track progress across sync stages."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.current: int = 0
        self.total: int = 0
        self.stage: str = ""

    def update(self, n: int = 1) -> None:
        self.current += n
