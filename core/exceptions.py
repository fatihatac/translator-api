from fastapi import HTTPException, status


class BaseTranslatorException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class TargetSiteStructureChanged(BaseTranslatorException):
    def __init__(self, message: str = "Target site structure has changed. Scraping failed."):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


class ProxyBlockedException(BaseTranslatorException):
    def __init__(self, message: str = "Scraping service is temporarily blocked by the target server."):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)


class WordNotFoundException(BaseTranslatorException):
    def __init__(self, word: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=f"Word '{word}' not found or invalid.")


class ScrapingTimeoutException(BaseTranslatorException):
    def __init__(self, message: str = "Timeout occurred while scraping the target site."):
        super().__init__(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=message)
