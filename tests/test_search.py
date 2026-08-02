from __future__ import annotations

from hust_helper.tools.hust_eater.service import HustEaterService


def test_exact_and_dish_search():
    service = HustEaterService()
    exact = service.search("红旺猪脚饭", limit=3)
    assert exact and exact[0].entry.name == "红旺猪脚饭"
    dish = service.search("糖醋排骨", limit=10)
    assert any(item.entry.name == "红旺猪脚饭" for item in dish)


def test_filtering():
    service = HustEaterService()
    results = service.search("热干面", chapter="武汉过早篇", limit=50)
    assert results
    assert all(item.entry.chapter_title == "武汉过早篇" for item in results)
