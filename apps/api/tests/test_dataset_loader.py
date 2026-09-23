from app.infrastructure.dataset_loader import load_dataset


def test_seed_dataset_contract() -> None:
    bundle = load_dataset()

    assert bundle.dataset_version == "1.0"
    assert bundle.as_of_date.isoformat() == "2026-10-01"
    assert len(bundle.skills) == 60
    assert len(bundle.role_profiles) == 32
    assert len(bundle.employees) == 200
    assert len(bundle.events) == 40
    assert len(bundle.history) == 2743
    assert bundle.events["EV_036"].repeatable is True
    assert all(
        event.repeatable is False
        for event_id, event in bundle.events.items()
        if event_id != "EV_036"
    )
