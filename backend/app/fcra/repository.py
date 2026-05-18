from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Optional, List
from app.models.database import FundAccount, FundTransaction, Hospital

class FCRARepository:
    @staticmethod
    def get_account_by_id(db: Session, account_id: str) -> Optional[FundAccount]:
        """Fetch a specific fund account by UUID."""
        return db.query(FundAccount).filter(FundAccount.id == account_id).first()

    @staticmethod
    def get_accounts_for_hospital(db: Session, hospital_id: str, fcra_only: bool = True) -> List[FundAccount]:
        """Fetch all fund accounts registered for a hospital, optionally filtering by FCRA designation."""
        query = db.query(FundAccount).filter(FundAccount.hospital_id == hospital_id)
        if fcra_only:
            query = query.filter(FundAccount.is_fcra_designated == True)
        return query.all()

    @staticmethod
    def get_recent_transactions(db: Session, account_id: str, limit: int = 10) -> List[FundTransaction]:
        """Fetch the most recent transactions for a fund account."""
        return db.query(FundTransaction).filter(
            FundTransaction.account_id == account_id
        ).order_by(FundTransaction.transaction_date.desc()).limit(limit).all()

    @staticmethod
    def get_last_transaction(db: Session, account_id: str) -> Optional[FundTransaction]:
        """Fetch the single absolute most recent transaction for ledger chain-linking."""
        return db.query(FundTransaction).filter(
            FundTransaction.account_id == account_id
        ).order_by(FundTransaction.created_at.desc()).first()

    @staticmethod
    def get_transactions_in_range(db: Session, account_id: str, start: datetime, end: datetime) -> List[FundTransaction]:
        """Fetch transactions for a fund account within a specific date range."""
        return db.query(FundTransaction).filter(
            and_(
                FundTransaction.account_id == account_id,
                FundTransaction.transaction_date >= start,
                FundTransaction.transaction_date <= end
            )
        ).all()

    @staticmethod
    def get_hospital_by_id(db: Session, hospital_id: str) -> Optional[Hospital]:
        """Fetch a hospital record."""
        return db.query(Hospital).filter(Hospital.id == hospital_id).first()

    @staticmethod
    def get_account_by_number(db: Session, number: str) -> Optional[FundAccount]:
        """Fetch a fund account by its account number."""
        return db.query(FundAccount).filter(FundAccount.account_number == number).first()

    @staticmethod
    def create_account(db: Session, account: FundAccount) -> FundAccount:
        """Persist a new fund account record."""
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    @staticmethod
    def create_transaction(db: Session, txn: FundTransaction) -> FundTransaction:
        """Persist a new transaction record."""
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn

    @staticmethod
    def save(db: Session, account: FundAccount) -> FundAccount:
        """Commit updates to an existing fund account."""
        db.commit()
        db.refresh(account)
        return account
