from __future__ import annotations

from hust_helper.tools.hust_eater.service import HustEaterService


def test_catalog_counts():
    service = HustEaterService()
    catalog = service.repository.catalog()
    assert catalog["source_pdf_pages"] == 49
    assert catalog["counts"] == {"chapters": 5, "sections": 32, "entries": 144, "images": 98}
    assert len(service.entries()) == 144


def test_all_pages_and_images_are_accessible():
    service = HustEaterService()
    for page in (1, 10, 24, 33, 45, 49):
        record = service.repository.page(page)
        assert record["page_number"] == page
    assert service.repository.image_bytes("media-p010-01").startswith(bytes.fromhex("89504e47"))
