class StreamtapeError(Exception):
    """Raised when a streamtape api error is countered."""
    
    def __init__(self: "StreamtapeError", status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        
        super().__init__(f"{self.status_code} - {self.message}")