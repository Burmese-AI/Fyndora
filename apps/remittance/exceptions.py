from apps.core.exceptions import BaseServiceError


class RemittanceConfirmPaymentException(Exception):
    pass


class RemittanceServiceError(BaseServiceError):
    default_detail = "Remittance service error occurred"
