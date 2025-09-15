from apps.core.exceptions import BaseServiceError


class EntryServiceError(BaseServiceError):
    default_detail = "Entry service error occurred"
