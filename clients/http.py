"""
Adapter interface for making generic HTTP requests.
"""

class HttpClient:
    """A generic interface for making HTTP requests."""

    def post(self, url: str, json_data: dict) -> dict:
        """Sends a POST request to the specified URL."""
        pass
