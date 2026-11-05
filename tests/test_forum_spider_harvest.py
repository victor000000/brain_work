"""Repair mode and harvest_bodies: a failed fetch is never checkpointed."""

from download.forum.spider import pending_ids


def test_pending_ids_repair_mode_requeues_empty_entries():
    done = {"1": "", "2": [], "3": "body", "4": [{"id": 9}]}
    assert pending_ids([1, 2, 3, 4], done) == []
    assert pending_ids([1, 2, 3, 4], done, repair_empty=True) == [1, 2]


def test_pending_ids_repair_mode_keeps_unfetched_ids():
    assert pending_ids([1, 2], {"1": ""}, repair_empty=True) == [1, 2]


class _FakeClient:
    """Post 1 always fails; the rest return a body."""

    def post_body(self, pid):
        return None if pid == 1 else f"<p>{pid}</p>"


def test_harvest_bodies_does_not_checkpoint_failures(tmp_path, monkeypatch):
    import download.forum.spider as spider

    monkeypatch.setattr(spider, "_client", lambda: _FakeClient())
    done = spider.harvest_bodies([1, 2], out_dir=tmp_path, workers=1, verbose=False)

    assert done == {"2": "<p>2</p>"}
    assert "1" not in done
    # the durable checkpoint must not record the failure either, or the next
    # run would count it as done
    assert "1" not in spider.load_checkpoint(tmp_path / "forum_bodies.json")


def test_harvest_bodies_repairs_checkpointed_empty_entries(tmp_path, monkeypatch):
    import download.forum.spider as spider

    monkeypatch.setattr(spider, "_client", lambda: _FakeClient())
    spider.save_checkpoint(tmp_path / "forum_bodies.json", {"2": ""})

    done = spider.harvest_bodies([2], out_dir=tmp_path, workers=1, verbose=False)
    assert done["2"] == "<p>2</p>"


def test_harvest_bodies_can_skip_repair(tmp_path, monkeypatch):
    import download.forum.spider as spider

    monkeypatch.setattr(spider, "_client", lambda: _FakeClient())
    spider.save_checkpoint(tmp_path / "forum_bodies.json", {"2": ""})

    done = spider.harvest_bodies([2], out_dir=tmp_path, workers=1, verbose=False, repair_empty=False)
    assert done["2"] == ""
