"""Domain exceptions for business rule enforcement."""
from fastapi import HTTPException, status

class DomainRuleException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class VoucherAlreadyUsedException(DomainRuleException):
    def __init__(self, code: str):
        super().__init__(
            detail=f"Comprovante '{code}' já foi utilizado e validado anteriormente.",
            status_code=status.HTTP_409_CONFLICT,
        )

class VoucherNotEligibleException(DomainRuleException):
    def __init__(self, reason: str):
        super().__init__(
            detail=f"Comprovante recusado: {reason}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

class CampaignNotActiveException(DomainRuleException):
    def __init__(self, status_name: str):
        super().__init__(
            detail=f"A campanha não está ativa para operações (situação atual: {status_name}).",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

class BoxNotConfirmedException(DomainRuleException):
    def __init__(self, box_number: str):
        super().__init__(
            detail=f"O box '{box_number}' ainda não possui cadastro oficial confirmado pela administração.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
