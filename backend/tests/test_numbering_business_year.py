from datetime import date

from app.services import numbering_service


def test_document_number_year_follows_business_timezone(db_session, monkeypatch):
    """At 23:30 in America/Tegucigalpa on 31 Dec the container clock (UTC) is
    already on 1 Jan of the next year. The year stamped into a document
    number must be the Honduras business year, not the UTC one."""
    from app.models.company import Company
    from app.models.currency import Currency
    from app.models.document_type import DocumentType

    db_session.add(Currency(code="HNL", name="Lempira", symbol="L"))
    company = Company(name="Numbering Co", code="NC")
    db_session.add(company)
    if db_session.get(DocumentType, "JMN") is None:
        db_session.add(DocumentType(code="JMN", name="Journal Manual", number_prefix="JMN"))
    db_session.flush()

    monkeypatch.setattr(numbering_service, "business_today", lambda: date(2026, 12, 31))
    number = numbering_service.next_document_number(
        db_session, company_id=company.id, document_type_code="JMN"
    )
    db_session.commit()

    assert number.split("-")[1] == "2026", number
