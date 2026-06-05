import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.regulatory_ingestion import (
    _classify_update_type,
    _identify_affected_areas,
    run_ingestion,
)
from app.models.database import RegulatoryUpdate

def test_classify_update_type():
    assert _classify_update_type("Amendment to Rules", "This is an amendment") == "amendment"
    assert _classify_update_type("New Rules", "Draft new rule for clinical establishments") == "new_rule"
    assert _classify_update_type("Circular 10", "Important circular from Ministry") == "circular"
    assert _classify_update_type("Order to all clinics", "This is an order") == "order"
    assert _classify_update_type("Gazette notice", "Some notice published") == "gazette_notification"
    # "Standard Notification" would be classified as "new_rule" because of "Notification"
    # To test the default fallback "notification", we use a title without keyword matches
    assert _classify_update_type("Standard Alert", "Random update") == "notification"

def test_identify_affected_areas():
    assert "bmw" in _identify_affected_areas("Bio-medical waste management", "Rules regarding waste")
    assert "dpdp" in _identify_affected_areas("DPDP compliance", "Patient personal data privacy")
    assert "fcra" in _identify_affected_areas("FCRA transactions", "Foreign contribution auditing")
    assert "nabh" in _identify_affected_areas("NABH 6th Edition", "Accreditation guidelines")
    assert "general" in _identify_affected_areas("Some random title", "Nothing interesting")

def test_run_ingestion(db_session):
    async def run_test():
        # Mock XML response for Gazette of India
        xml_content = """<?xml version="1.0" encoding="UTF-8" ?>
        <rss version="2.0">
          <channel>
            <item>
              <title>Amendment to Bio-Medical Waste rules 2026</title>
              <description>New standards for waste management and GPS tracking of waste transport vehicles.</description>
              <link>https://egazette.gov.in/test-bmw-1</link>
              <pubDate>Sun, 24 May 2026 12:00:00 GMT</pubDate>
            </item>
            <item>
              <title>Unrelated regulation on highways</title>
              <description>Draft rules for national highway toll pricing.</description>
              <link>https://egazette.gov.in/test-highway-1</link>
              <pubDate>Sun, 24 May 2026 12:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """

        class MockResponse:
            def __init__(self, status_code, content):
                self.status_code = status_code
                self.content = content

        mock_client = MagicMock()
        # Mocking async context manager 'async with AsyncClient()'
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        # We need mock_client.get to be an AsyncMock returning the Response
        mock_client.get = AsyncMock(return_value=MockResponse(200, xml_content.encode("utf-8")))

        with patch("app.core.database.SessionLocal", return_value=db_session), \
             patch("httpx.AsyncClient", return_value=mock_client), \
             patch("app.services.vector_store.ingest_regulation", return_value=1), \
             patch.object(db_session, "close", return_value=None):
            
            results = await run_ingestion()
            
            # We expect some new updates
            assert results["new_updates"] > 0
            
            # Check that the updates are stored in the database
            bmw_update = db_session.query(RegulatoryUpdate).filter(
                RegulatoryUpdate.title == "Amendment to Bio-Medical Waste rules 2026"
            ).first()
            assert bmw_update is not None
            assert bmw_update.source == "gazette"
            assert bmw_update.update_type == "amendment"
            assert "bmw" in bmw_update.affected_areas
            
            # Run ingestion again to verify duplicates are skipped
            count_before = db_session.query(RegulatoryUpdate).count()
            
            results2 = await run_ingestion()
            
            count_after = db_session.query(RegulatoryUpdate).count()
            assert count_before == count_after

    asyncio.run(run_test())
