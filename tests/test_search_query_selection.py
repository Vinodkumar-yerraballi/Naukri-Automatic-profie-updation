from main import _select_search_queries


def test_search_selection_covers_each_role_before_repeating_locations():
    roles = ["Data Analyst", "Data Scientist", "Reporting Analyst"]
    locations = ["Remote", "Bangalore", "Hyderabad", "Chennai"]

    selected = _select_search_queries(
        roles=roles,
        locations=locations,
        max_searches=3,
        day_offset=0,
    )

    assert [role for role, _ in selected] == roles


def test_search_selection_rotates_locations_and_respects_limit():
    roles = ["Data Analyst", "Data Scientist"]
    locations = ["Remote", "Bangalore", "Hyderabad"]

    first_day = _select_search_queries(
        roles=roles,
        locations=locations,
        max_searches=3,
        day_offset=0,
    )
    second_day = _select_search_queries(
        roles=roles,
        locations=locations,
        max_searches=3,
        day_offset=1,
    )

    assert len(first_day) == 3
    assert len(second_day) == 3
    assert first_day != second_day
