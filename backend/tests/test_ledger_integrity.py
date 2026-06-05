from datetime import datetime
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.consent.service import ConsentService
from app.fcra.service import FCRAService
from app.models.database import ConsentRecord, FundAccount, FundTransaction, FundType, Hospital


class _FixedDateTime:
    _current = datetime(2026, 1, 1, 0, 0, 0)

    @classmethod
    def set_current(cls, value: datetime) -> None:
        cls._current = value

    @classmethod
    def utcnow(cls) -> datetime:
        return cls._current


def _validate_fcra_chain(records: list[FundTransaction]) -> None:
    assert records
    by_previous = {}
    for record in records:
        by_previous.setdefault(record.previous_hash, []).append(record)

    assert len(by_previous.get("0" * 64, [])) == 1
    previous_hash = "0" * 64
    for _ in range(len(records)):
        next_records = by_previous.get(previous_hash, [])
        assert len(next_records) == 1
        record = next_records[0]
        assert record.previous_hash == previous_hash
        payload = (
            f"{record.account_id}"
            f"{record.amount}"
            f"{record.transaction_type.lower()}"
            f"{record.description}"
            f"{record.transaction_date.isoformat()}"
        )
        expected_hash = sha256(f"{payload}{previous_hash}".encode()).hexdigest()
        assert record.transaction_hash == expected_hash
        previous_hash = record.transaction_hash
    assert by_previous.get(previous_hash, []) == []


def _validate_consent_chain(records: list[ConsentRecord]) -> None:
    assert records
    by_previous = {}
    for record in records:
        by_previous.setdefault(record.previous_hash, []).append(record)

    assert len(by_previous.get("0" * 64, [])) == 1
    previous_hash = "0" * 64
    for _ in range(len(records)):
        next_records = by_previous.get(previous_hash, [])
        assert len(next_records) == 1
        record = next_records[0]
        assert record.previous_hash == previous_hash
        payload = (
            f"{record.patient_id}"
            f"{record.consent_type}"
            f"{record.purpose}"
            f"{record.digital_signature or ''}"
            f"{record.granted_at.isoformat()}"
        )
        expected_hash = sha256(f"{payload}{previous_hash}".encode()).hexdigest()
        assert record.artefact_hash == expected_hash
        previous_hash = record.artefact_hash
    assert by_previous.get(previous_hash, []) == []


def _seed_hospital_and_account(db_session):
    hospital = Hospital(
        id="hosp-ledger-1",
        name="Ledger Test Hospital",
        registration_number="REG-LEDGER-1",
        hospital_type="trust",
    )
    account = FundAccount(
        id="acc-ledger-1",
        hospital_id=hospital.id,
        account_name="FCRA Primary",
        account_number="123456789012",
        bank_name="Test Bank",
        branch="Main",
        fund_type=FundType.FCRA_FOREIGN,
        is_fcra_designated=True,
        fcra_utilization_purpose="patient care",
        current_balance=10000.0,
        annual_budget=50000.0,
    )
    db_session.add(hospital)
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return hospital, account


def test_fcra_transaction_hash_chain_integrity(db_session):
    _, account = _seed_hospital_and_account(db_session)
    txn_times = [
        datetime(2026, 1, 1, 10, 0, 0),
        datetime(2026, 1, 1, 10, 5, 0),
        datetime(2026, 1, 1, 10, 10, 0),
    ]
    txns = [
        SimpleNamespace(
            account_id=account.id,
            amount=1000.0,
            transaction_type="credit",
            description="Foreign grant tranche 1",
            purpose="patient care",
            donor_name="Donor A",
            donor_country="USA",
            donor_passport_or_id="ID-A",
        ),
        SimpleNamespace(
            account_id=account.id,
            amount=300.0,
            transaction_type="debit",
            description="Equipment payment",
            purpose="patient care",
            donor_name=None,
            donor_country=None,
            donor_passport_or_id=None,
        ),
        SimpleNamespace(
            account_id=account.id,
            amount=500.0,
            transaction_type="credit",
            description="Foreign grant tranche 2",
            purpose="patient care",
            donor_name="Donor B",
            donor_country="UK",
            donor_passport_or_id="ID-B",
        ),
    ]

    with patch("app.fcra.service.datetime", _FixedDateTime):
        for when, txn in zip(txn_times, txns):
            _FixedDateTime.set_current(when)
            FCRAService.record_transaction(db_session, txn, account)
            latest = (
                db_session.query(FundTransaction)
                .filter(FundTransaction.account_id == account.id)
                .order_by(FundTransaction.transaction_date.desc(), FundTransaction.id.desc())
                .first()
            )
            latest.created_at = when
            db_session.commit()

    chain = db_session.query(FundTransaction).filter(FundTransaction.account_id == account.id).all()
    assert len(chain) == 3
    _validate_fcra_chain(chain)


def test_consent_hash_chain_integrity(db_session):
    hospital, _ = _seed_hospital_and_account(db_session)
    consent_times = [
        datetime(2026, 1, 2, 9, 0, 0),
        datetime(2026, 1, 2, 9, 5, 0),
        datetime(2026, 1, 2, 9, 10, 0),
    ]
    consents = [
        SimpleNamespace(
            hospital_id=hospital.id,
            patient_id="P-100",
            patient_name="Patient One",
            patient_mobile="9000000001",
            patient_address="Addr 1",
            digital_signature="sig-1",
            consent_type="treatment",
            purpose="General treatment",
            data_categories=["name", "diagnosis"],
            third_parties=["lab"],
            expires_in_days=30,
            consent_method="digital_signature",
            is_minor=False,
            guardian_consent_id=None,
            language_preference="en",
        ),
        SimpleNamespace(
            hospital_id=hospital.id,
            patient_id="P-101",
            patient_name="Patient Two",
            patient_mobile="9000000002",
            patient_address="Addr 2",
            digital_signature="sig-2",
            consent_type="billing",
            purpose="Insurance processing",
            data_categories=["name", "billing"],
            third_parties=["insurer"],
            expires_in_days=60,
            consent_method="digital_signature",
            is_minor=False,
            guardian_consent_id=None,
            language_preference="en",
        ),
        SimpleNamespace(
            hospital_id=hospital.id,
            patient_id="P-102",
            patient_name="Patient Three",
            patient_mobile="9000000003",
            patient_address="Addr 3",
            digital_signature="sig-3",
            consent_type="research",
            purpose="Clinical research",
            data_categories=["name", "lab_results"],
            third_parties=["research_partner"],
            expires_in_days=90,
            consent_method="digital_signature",
            is_minor=False,
            guardian_consent_id=None,
            language_preference="en",
        ),
    ]

    with patch("app.consent.service.datetime", _FixedDateTime):
        for when, consent in zip(consent_times, consents):
            _FixedDateTime.set_current(when)
            ConsentService.grant_consent(db_session, consent)
            latest = (
                db_session.query(ConsentRecord)
                .filter(ConsentRecord.hospital_id == hospital.id)
                .order_by(ConsentRecord.granted_at.desc(), ConsentRecord.id.desc())
                .first()
            )
            latest.created_at = when
            db_session.commit()

    chain = db_session.query(ConsentRecord).filter(ConsentRecord.hospital_id == hospital.id).all()
    assert len(chain) == 3
    _validate_consent_chain(chain)


def test_fcra_chain_detects_tampering(db_session):
    _, account = _seed_hospital_and_account(db_session)
    txn_times = [
        datetime(2026, 1, 3, 11, 0, 0),
        datetime(2026, 1, 3, 11, 5, 0),
        datetime(2026, 1, 3, 11, 10, 0),
    ]
    txns = [
        SimpleNamespace(
            account_id=account.id,
            amount=1000.0,
            transaction_type="credit",
            description="Initial credit",
            purpose="patient care",
            donor_name="Donor X",
            donor_country="USA",
            donor_passport_or_id="ID-X",
        ),
        SimpleNamespace(
            account_id=account.id,
            amount=200.0,
            transaction_type="debit",
            description="Medicine purchase",
            purpose="patient care",
            donor_name=None,
            donor_country=None,
            donor_passport_or_id=None,
        ),
        SimpleNamespace(
            account_id=account.id,
            amount=400.0,
            transaction_type="credit",
            description="Second credit",
            purpose="patient care",
            donor_name="Donor Y",
            donor_country="UK",
            donor_passport_or_id="ID-Y",
        ),
    ]

    with patch("app.fcra.service.datetime", _FixedDateTime):
        for when, txn in zip(txn_times, txns):
            _FixedDateTime.set_current(when)
            FCRAService.record_transaction(db_session, txn, account)
            latest = (
                db_session.query(FundTransaction)
                .filter(FundTransaction.account_id == account.id)
                .order_by(FundTransaction.transaction_date.desc(), FundTransaction.id.desc())
                .first()
            )
            latest.created_at = when
            db_session.commit()

    chain = db_session.query(FundTransaction).filter(FundTransaction.account_id == account.id).all()
    chain[1].amount = 9999.0
    db_session.commit()

    tampered_chain = db_session.query(FundTransaction).filter(FundTransaction.account_id == account.id).all()
    with pytest.raises(AssertionError):
        _validate_fcra_chain(tampered_chain)


def test_consent_chain_detects_tampering(db_session):
    hospital, _ = _seed_hospital_and_account(db_session)
    consent_times = [
        datetime(2026, 1, 4, 12, 0, 0),
        datetime(2026, 1, 4, 12, 5, 0),
        datetime(2026, 1, 4, 12, 10, 0),
    ]
    consents = [
        SimpleNamespace(
            hospital_id=hospital.id,
            patient_id="P-201",
            patient_name="Alpha",
            patient_mobile="9000000101",
            patient_address="Addr A",
            digital_signature="sig-a",
            consent_type="treatment",
            purpose="Treatment access",
            data_categories=["name", "diagnosis"],
            third_parties=[],
            expires_in_days=30,
            consent_method="digital_signature",
            is_minor=False,
            guardian_consent_id=None,
            language_preference="en",
        ),
        SimpleNamespace(
            hospital_id=hospital.id,
            patient_id="P-202",
            patient_name="Beta",
            patient_mobile="9000000102",
            patient_address="Addr B",
            digital_signature="sig-b",
            consent_type="billing",
            purpose="Billing access",
            data_categories=["name", "billing"],
            third_parties=[],
            expires_in_days=30,
            consent_method="digital_signature",
            is_minor=False,
            guardian_consent_id=None,
            language_preference="en",
        ),
        SimpleNamespace(
            hospital_id=hospital.id,
            patient_id="P-203",
            patient_name="Gamma",
            patient_mobile="9000000103",
            patient_address="Addr C",
            digital_signature="sig-c",
            consent_type="research",
            purpose="Research access",
            data_categories=["name", "lab_results"],
            third_parties=[],
            expires_in_days=30,
            consent_method="digital_signature",
            is_minor=False,
            guardian_consent_id=None,
            language_preference="en",
        ),
    ]

    with patch("app.consent.service.datetime", _FixedDateTime):
        for when, consent in zip(consent_times, consents):
            _FixedDateTime.set_current(when)
            ConsentService.grant_consent(db_session, consent)
            latest = (
                db_session.query(ConsentRecord)
                .filter(ConsentRecord.hospital_id == hospital.id)
                .order_by(ConsentRecord.granted_at.desc(), ConsentRecord.id.desc())
                .first()
            )
            latest.created_at = when
            db_session.commit()

    chain = db_session.query(ConsentRecord).filter(ConsentRecord.hospital_id == hospital.id).all()
    chain[1].purpose = "Tampered purpose"
    db_session.commit()

    tampered_chain = db_session.query(ConsentRecord).filter(ConsentRecord.hospital_id == hospital.id).all()
    with pytest.raises(AssertionError):
        _validate_consent_chain(tampered_chain)
