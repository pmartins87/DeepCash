import pytest

from deepcash_core.actions import ActionKind, AbstractAction, legalize_raise_to


def test_non_raise_cannot_have_size() -> None:
    with pytest.raises(ValueError):
        AbstractAction(ActionKind.CALL, pot_fraction=0.5)


def test_raise_requires_exactly_one_sizing_coordinate() -> None:
    with pytest.raises(ValueError):
        AbstractAction(ActionKind.RAISE_TO)
    with pytest.raises(ValueError):
        AbstractAction(ActionKind.RAISE_TO, pot_fraction=0.5, raise_to_bb=2.5)
    assert AbstractAction(ActionKind.RAISE_TO, pot_fraction=0.75).pot_fraction == 0.75


def test_legalize_raise_to_clips_only_to_engine_bounds() -> None:
    assert legalize_raise_to(400, min_raise_to=500, max_raise_to=2000) == 500
    assert legalize_raise_to(900, min_raise_to=500, max_raise_to=2000) == 900
    assert legalize_raise_to(2500, min_raise_to=500, max_raise_to=2000) == 2000
