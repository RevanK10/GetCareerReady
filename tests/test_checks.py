from evals.checks import new_numbers


def test_no_new_numbers():
    assert new_numbers("Cut costs by 30% in 2021", "In 2021 I cut costs by 30%") == []


def test_invented_numbers_are_found():
    assert new_numbers("Led a team", "Led a team of 12 and grew revenue 45%") == ["12", "45"]


def test_thousands_separators_are_ignored():
    assert new_numbers("Saved $1,200", "Saved $1200") == []
