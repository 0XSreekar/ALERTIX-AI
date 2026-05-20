"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactForm
from app.schemas.sos import SosCreate


class TestSosCreate:
    def test_valid_sos(self):
        sos = SosCreate(raw_text="Flooding in my village, 10 people stranded", consent_given=True)
        assert sos.raw_text.startswith("Flooding")

    def test_too_short_text(self):
        with pytest.raises(ValidationError):
            SosCreate(raw_text="Help", consent_given=True)

    def test_with_location(self):
        sos = SosCreate(
            raw_text="Earthquake damage in Kathmandu area",
            latitude=27.7,
            longitude=85.3,
            consent_given=False,
        )
        assert sos.latitude == 27.7


class TestContactForm:
    def test_valid_contact(self):
        form = ContactForm(
            name="Test User", email="test@example.com", message="Hello, this is a test message"
        )
        assert form.name == "Test User"

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            ContactForm(name="", email="test@example.com", message="Hello, this is a test message")

    def test_short_message(self):
        with pytest.raises(ValidationError):
            ContactForm(name="Test", email="test@example.com", message="Short")
