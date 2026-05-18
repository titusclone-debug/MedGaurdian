import pytest
from unittest.mock import MagicMock
from app.bmw.service import BMWService
from app.bmw.repository import BMWRepository
from app.models.database import BMWLog, BMWCategory

def test_bmw_service_log_entry_success():
    """Verify BMWService.log_entry maps and saves entries via the repository successfully."""
    db = MagicMock()
    entry = MagicMock()
    entry.weight_kg = 15.5
    entry.source_department = "ICU"
    entry.source_ward = "Ward A"
    entry.treatment_method = "autoclave"
    entry.treatment_operator = "John"
    entry.treatment_machine_id = "M01"
    entry.treatment_temperature = 121.0
    entry.treatment_duration_min = 30
    entry.disposal_agency = "Disposal Ltd"
    entry.disposal_manifest_number = "M100"
    entry.disposal_vehicle_number = "V100"
    
    # Simulate DB persistence return
    simulated_log = BMWLog(
        id="mock-log-id",
        hospital_id="hosp-1",
        category=BMWCategory.YELLOW,
        weight_kg=15.5,
        source_department="ICU",
    )
    
    original_create_entry = BMWRepository.create_entry
    BMWRepository.create_entry = MagicMock(return_value=simulated_log)
    
    try:
        res = BMWService.log_entry(db, entry, "hosp-1", BMWCategory.YELLOW)
        assert res["log_id"] == "mock-log-id"
        assert res["category"] == "yellow"
        assert res["weight_kg"] == 15.5
        assert res["status"] == "logged"
        BMWRepository.create_entry.assert_called_once()
    finally:
        BMWRepository.create_entry = original_create_entry


def test_bmw_service_verify_entry_success():
    """Verify BMWService.verify_entry updates verification compliance attributes correctly."""
    db = MagicMock()
    log = BMWLog(
        id="log-1",
        hospital_id="hosp-1",
        category=BMWCategory.RED,
        weight_kg=10.0,
    )
    
    verification = MagicMock()
    verification.is_properly_segregated = True
    verification.is_properly_labeled = True
    verification.is_properly_stored = True
    verification.compliance_notes = "Spot check passed"
    
    original_save = BMWRepository.save
    BMWRepository.save = MagicMock(return_value=log)
    
    try:
        res = BMWService.verify_entry(db, log, verification)
        assert res["is_compliant"] is True
        assert res["status"] == "compliant"
        assert log.is_properly_segregated is True
        assert log.is_properly_labeled is True
        assert log.is_properly_stored is True
        BMWRepository.save.assert_called_once()
    finally:
        BMWRepository.save = original_save
