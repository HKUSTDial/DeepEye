from app.node.video.render.tsx_sanitize import sanitize_tsx_for_browser


def test_sanitize_tsx_repairs_invalid_keyof_indexing() -> None:
    source = """
const highlighted = new Set(activeEmphasis.flatMap(a => data
  .filter(d => Object.keys(a.target_data!.data_filter).every(
    k => d[k as keyof typeof d] === a.target_data!.data_filter[k as keyof typeof a.target_data!.data_filter]
  ))
  .map(d => d.city)));
"""

    sanitized = sanitize_tsx_for_browser(source)

    assert "[k as keyof typeof d]" not in sanitized
    assert "[k as keyof typeof a.target_data!.data_filter]" not in sanitized
    assert "d[k] === a.target_data!.data_filter[k]" in sanitized
