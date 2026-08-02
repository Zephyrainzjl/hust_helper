from __future__ import annotations

from hust_helper.core.repository import HustEaterRepository


def test_overlay_crud(tmp_path):
    repo = HustEaterRepository(tmp_path)
    created = repo.add({"id": "", "name": "测试小店", "description": "测试", "extensions": {}})
    assert repo.get(created.id).name == "测试小店"
    updated = repo.update(created.id, description="已更新")
    assert updated.description == "已更新"
    repo.delete(created.id)
    assert all(item.id != created.id for item in repo.list_entries())
    repo.restore(created.id)
    assert repo.get(created.id).description == "已更新"


def test_image_overlay_operations(tmp_path):
    repo = HustEaterRepository(tmp_path)
    entry = next(item for item in repo.list_entries() if item.media_ids)
    base_media_id = entry.media_ids[0]
    original = repo.image_bytes(base_media_id)
    record = repo.update_image_caption(base_media_id, "新的图片说明")
    assert record["caption"] == "新的图片说明"
    assert repo.image_bytes(base_media_id) == original

    # A minimal PNG signature is sufficient for repository byte replacement tests.
    replacement = tmp_path / "replacement.png"
    replacement.write_bytes(bytes.fromhex("89504e470d0a1a0a0000000049454e44ae426082"))
    repo.replace_image(base_media_id, replacement, "替换后的图片")
    assert repo.image_bytes(base_media_id) == replacement.read_bytes()
    assert repo.media_record(base_media_id)["caption"] == "替换后的图片"
