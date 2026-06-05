"""FCRA Guardian — Foreign fund compliance and utilization tracking."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.models.database import FundAccount, Hospital, Staff, FundType, UserRole
from app.fcra.repository import FCRARepository
from app.fcra.service import FCRAService

router = APIRouter()


class FundAccountCreate(BaseModel):
    account_name: str
    account_number: str
    bank_name: str
    branch: str
    fund_type: str
    is_fcra_designated: bool = False
    fcra_utilization_purpose: Optional[str] = None
    annual_budget: float = 0.0


class TransactionCreate(BaseModel):
    account_id: str
    amount: float
    transaction_type: str  # credit, debit
    description: str
    purpose: str
    donor_name: Optional[str] = None
    donor_country: Optional[str] = None
    donor_passport_or_id: Optional[str] = None


@router.get("/accounts/{hospital_id}")
async def get_fcra_accounts(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.ACCOUNTANT])),
):
    """Get all FCRA-designated fund accounts for a hospital."""
    assert_hospital_access(current_user, hospital_id)
    
    return FCRAService.get_accounts(db, hospital_id)


@router.post("/accounts/{hospital_id}")
async def create_fcra_account(
    hospital_id: str,
    account: FundAccountCreate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.ACCOUNTANT])),
):
    """Register a new FCRA-designated fund account."""
    assert_hospital_access(current_user, hospital_id)

    # Validate hospital exists
    hospital = FCRARepository.get_hospital_by_id(db, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")

    try:
        fund_type = FundType(account.fund_type.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fund type: '{account.fund_type}'. Must be one of: fcra_foreign, fcra_domestic, government_grant, patient_fees, donation_domestic, csr_funds"
        )
    
    # Check for duplicate account number
    existing = FCRARepository.get_account_by_number(db, account.account_number)
    if existing:
        raise HTTPException(status_code=400, detail="Account number already registered")
    
    return FCRAService.create_account(db, hospital_id, account, fund_type)


@router.post("/transactions")
async def record_transaction(
    txn: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.ACCOUNTANT])),
):
    """Record a fund transaction with FCRA compliance checks."""
    if txn.transaction_type.lower() not in ["credit", "debit"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transaction type: '{txn.transaction_type}'. Must be 'credit' or 'debit'."
        )

    if txn.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Transaction amount must be greater than zero: {txn.amount}"
        )

    account = FCRARepository.get_account_by_id(db, txn.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Fund account not found")
    assert_hospital_access(current_user, account.hospital_id)
    
    return FCRAService.record_transaction(db, txn, account)


@router.get("/compliance-report/{hospital_id}")
async def get_fcra_compliance_report(
    hospital_id: str,
    year: int = Query(datetime.utcnow().year),
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """Generate FCRA compliance report for a given year."""
    # SECURITY FIX: Restored assert_hospital_access from docstring comment into active code!
    assert_hospital_access(current_user, hospital_id)
    
    return FCRAService.get_compliance_report(db, hospital_id, year)


@router.post("/renewal-draft/{hospital_id}")
async def draft_fcra_renewal(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.ACCOUNTANT])),
):
    """Auto-draft FCRA renewal application in MHA standard formatting."""
    assert_hospital_access(current_user, hospital_id)

    hospital = FCRARepository.get_hospital_by_id(db, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    return FCRAService.draft_fcra_renewal(db, hospital)
