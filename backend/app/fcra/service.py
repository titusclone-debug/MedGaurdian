from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
from typing import Optional, List, Dict, Any
from app.fcra.repository import FCRARepository
from app.models.database import FundAccount, FundTransaction, FundType, ComplianceStatus, Hospital

class FCRAService:
    @staticmethod
    def get_accounts(db: Session, hospital_id: str) -> Dict[str, Any]:
        """Fetch all FCRA-designated accounts, masked account numbers, and recent transactions."""
        accounts = FCRARepository.get_accounts_for_hospital(db, hospital_id, fcra_only=True)
        
        result = []
        for acc in accounts:
            recent_txns = FCRARepository.get_recent_transactions(db, acc.id, limit=10)
            
            result.append({
                "id": acc.id,
                "account_name": acc.account_name,
                "account_number": acc.account_number[-4:].rjust(len(acc.account_number), '*'),
                "bank_name": acc.bank_name,
                "branch": acc.branch,
                "fund_type": acc.fund_type.value,
                "fcra_utilization_purpose": acc.fcra_utilization_purpose,
                "current_balance": acc.current_balance,
                "annual_budget": acc.annual_budget,
                "ytd_expenditure": acc.ytd_expenditure,
                "utilization_rate": (acc.ytd_expenditure / acc.annual_budget * 100) if acc.annual_budget > 0 else 0,
                "compliance_status": acc.compliance_status.value,
                "last_reconciliation": acc.last_reconciliation.isoformat() if acc.last_reconciliation else None,
                "recent_transactions": [{
                    "id": txn.id,
                    "date": txn.transaction_date.isoformat(),
                    "amount": txn.amount,
                    "type": txn.transaction_type,
                    "description": txn.description,
                    "purpose": txn.purpose,
                    "is_compliant": txn.is_compliant,
                    "donor_country": txn.donor_country,
                } for txn in recent_txns]
            })
            
        return {"accounts": result}

    @staticmethod
    def create_account(
        db: Session,
        hospital_id: str,
        account: Any,
        fund_type: FundType
    ) -> Dict[str, Any]:
        """Create and seed a new fund account."""
        new_account = FundAccount(
            hospital_id=hospital_id,
            account_name=account.account_name,
            account_number=account.account_number,
            bank_name=account.bank_name,
            branch=account.branch,
            fund_type=fund_type,
            is_fcra_designated=account.is_fcra_designated,
            fcra_utilization_purpose=account.fcra_utilization_purpose,
            annual_budget=account.annual_budget,
            compliance_status=ComplianceStatus.UNDER_REVIEW,
        )
        saved = FCRARepository.create_account(db, new_account)
        
        return {
            "message": "FCRA account registered successfully",
            "account_id": saved.id,
            "compliance_status": "under_review"
        }

    @staticmethod
    def record_transaction(db: Session, txn: Any, account: FundAccount) -> Dict[str, Any]:
        """Post a transaction, apply FCRA compliance checks, and hash-chain it to the ledger block."""
        compliance_issues = []
        
        # Check 1: Foreign donations must have donor details
        if account.fund_type == FundType.FCRA_FOREIGN and txn.transaction_type.lower() == "credit":
            if not txn.donor_name:
                compliance_issues.append("Foreign donation requires donor name")
            if not txn.donor_country:
                compliance_issues.append("Foreign donation requires donor country")
            if not txn.donor_passport_or_id:
                compliance_issues.append("Foreign donation requires donor ID (passport/registration)")
        
        # Check 2: FCRA funds cannot mix with domestic funds
        if account.is_fcra_designated and account.fund_type == FundType.FCRA_FOREIGN:
            if account.fcra_utilization_purpose and txn.purpose:
                purpose_lower = txn.purpose.lower()
                allowed_lower = account.fcra_utilization_purpose.lower()
                if not any(word in purpose_lower for word in allowed_lower.split()):
                    compliance_issues.append(f"Transaction purpose '{txn.purpose}' may not align with FCRA utilization purpose '{account.fcra_utilization_purpose}'")
        
        # Check 3: Balance validation for debits
        if txn.transaction_type.lower() == "debit":
            if txn.amount > account.current_balance:
                compliance_issues.append(f"Insufficient funds: Balance ₹{account.current_balance}, Debit ₹{txn.amount}")
        
        # Chain hash generation
        last_txn = FCRARepository.get_last_transaction(db, txn.account_id)
        previous_hash = last_txn.transaction_hash if last_txn else "0" * 64
        txn_data = f"{txn.account_id}{txn.amount}{txn.transaction_type.lower()}{txn.description}{datetime.utcnow().isoformat()}"
        transaction_hash = hashlib.sha256(f"{txn_data}{previous_hash}".encode()).hexdigest()
        
        # Create record
        new_txn = FundTransaction(
            account_id=txn.account_id,
            transaction_date=datetime.utcnow(),
            amount=txn.amount,
            transaction_type=txn.transaction_type.lower(),
            description=txn.description,
            purpose=txn.purpose,
            donor_name=txn.donor_name,
            donor_country=txn.donor_country,
            donor_passport_or_id=txn.donor_passport_or_id,
            is_compliant=len(compliance_issues) == 0,
            compliance_notes="; ".join(compliance_issues) if compliance_issues else None,
            transaction_hash=transaction_hash,
            previous_hash=previous_hash,
        )
        
        # Update balance
        if txn.transaction_type.lower() == "credit":
            account.current_balance += txn.amount
        else:
            account.current_balance -= txn.amount
            account.ytd_expenditure += txn.amount
            
        FCRARepository.create_transaction(db, new_txn)
        FCRARepository.save(db, account)
        
        return {
            "transaction_id": new_txn.id,
            "hash": transaction_hash,
            "is_compliant": len(compliance_issues) == 0,
            "compliance_issues": compliance_issues,
            "new_balance": account.current_balance,
            "message": "Transaction recorded with FCRA compliance check"
        }

    @staticmethod
    def get_compliance_report(db: Session, hospital_id: str, year: int) -> Dict[str, Any]:
        """Aggregate ledger balances, credit/debit transaction statistics, and compliance ratings."""
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        
        accounts = FCRARepository.get_accounts_for_hospital(db, hospital_id, fcra_only=True)
        
        report = {
            "hospital_id": hospital_id,
            "year": year,
            "generated_at": datetime.utcnow().isoformat(),
            "accounts": []
        }
        
        total_foreign_credits = 0
        total_expenditure = 0
        compliant_transactions = 0
        total_transactions = 0
        
        for acc in accounts:
            txns = FCRARepository.get_transactions_in_range(db, acc.id, start_date, end_date)
            
            credits = sum(t.amount for t in txns if t.transaction_type == "credit")
            debits = sum(t.amount for t in txns if t.transaction_type == "debit")
            compliant = sum(1 for t in txns if t.is_compliant)
            
            total_foreign_credits += credits
            total_expenditure += debits
            compliant_transactions += compliant
            total_transactions += len(txns)
            
            report["accounts"].append({
                "account_name": acc.account_name,
                "fund_type": acc.fund_type.value,
                "opening_balance": acc.current_balance - credits + debits,
                "total_credits": credits,
                "total_debits": debits,
                "closing_balance": acc.current_balance,
                "transaction_count": len(txns),
                "compliant_transactions": compliant,
                "compliance_rate": (compliant / len(txns) * 100) if txns else 100,
                "utilization_purpose": acc.fcra_utilization_purpose,
            })
            
        report["summary"] = {
            "total_foreign_credits": total_foreign_credits,
            "total_expenditure": total_expenditure,
            "overall_compliance_rate": (compliant_transactions / total_transactions * 100) if total_transactions > 0 else 100,
            "total_transactions": total_transactions,
            "compliant_transactions": compliant_transactions,
        }
        
        return report

    @staticmethod
    def draft_fcra_renewal(db: Session, hospital: Hospital) -> Dict[str, Any]:
        """Draft a renewal application to the Ministry of Home Affairs (Bureaucracy Engine)."""
        accounts = FCRARepository.get_accounts_for_hospital(db, hospital.id, fcra_only=True)
        
        draft = f"""
TO
The Director (FCRA Wing)
Ministry of Home Affairs
Government of India
New Delhi

Subject: Application for Renewal of FCRA Registration — {hospital.fcra_number}

Respected Sir/Madam,

I write on behalf of {hospital.name}, a {hospital.hospital_type} hospital located in {hospital.district}, {hospital.state}, to respectfully submit our application for the renewal of our FCRA registration (Registration No: {hospital.fcra_number}) which is due for renewal on {hospital.fcra_expiry.strftime('%d-%m-%Y') if hospital.fcra_expiry else 'N/A'}.

BACKGROUND AND PURPOSE:
{hospital.name} has been serving the healthcare needs of the {hospital.district} district since its establishment, with a particular focus on providing affordable healthcare to underserved communities. As a {hospital.hospital_type} institution with {hospital.bed_count} beds, we serve approximately [X] patients annually, of which [X]% are from below-poverty-line families.

FCRA UTILIZATION REPORT:
We have maintained meticulous compliance with all FCRA provisions during the current registration period. Our designated FCRA account(s) have been operated in strict accordance with the conditions of registration:

"""
        
        for acc in accounts:
            draft += f"""
• Account: {acc.account_name} at {acc.bank_name}, {acc.branch}
  - Utilization Purpose: {acc.fcra_utilization_purpose}
  - Current Balance: ₹{acc.current_balance:,.2f}
  - Annual Expenditure: ₹{acc.ytd_expenditure:,.2f}
"""
            
        draft += """
COMPLIANCE CERTIFICATE:
We certify that:
1. All foreign contributions received have been utilized for the stated purpose
2. No foreign contributions have been deposited in any account other than the designated FCRA account
3. All required returns and reports have been filed within the stipulated timelines
4. The institution has not been found guilty of any violation of FCRA provisions

We humbly request the Hon'ble Director to consider our application favourably and renew our FCRA registration for a further period of five years.

Thanking you,

Yours faithfully,
[Name]
Designation
{hospital.name}
"""
        
        return {
            "draft": draft.strip(),
            "hospital": hospital.name,
            "fcra_number": hospital.fcra_number,
            "expiry_date": hospital.fcra_expiry.isoformat() if hospital.fcra_expiry else None,
            "accounts_included": len(accounts),
            "message": "Renewal draft generated. Review and customize before submission."
        }
