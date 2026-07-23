from dolphin_v2_rocm.dolphin_parsing import (
    MarkdownConverter,
    extract_labels_from_string,
    extract_table_from_html,
    parse_layout_string,
    resize_img,
    truncate_repeated_tail,
)

UPSTREAM_SAMPLE = (
    "[210,136,910,172][sec_0][PAIR_SEP]"
    "[202,217,921,325][para][author][PAIR_SEP]"
    "[290,404,384,432][sec_1][paper_abstract][PAIR_SEP]"
    "[125,781,552,1143][para][RELATION_SEP]"
    "[573,406,1000,561][para][PAIR_SEP]"
    "[21,499,63,1163][watermark][meta_num]"
)


def test_extract_labels_skips_coordinates():
    assert extract_labels_from_string("[202,217,921,325][para][author]") == ["para", "author"]


def test_parse_layout_string_upstream_sample():
    parsed = parse_layout_string(UPSTREAM_SAMPLE)
    assert len(parsed) == 6
    coords, label, tags = parsed[0]
    assert coords == [210.0, 136.0, 910.0, 172.0]
    assert label == "sec_0"
    assert tags == []
    _, label1, tags1 = parsed[1]
    assert label1 == "para"
    assert tags1 == ["author"]
    _, label5, tags5 = parsed[5]
    assert label5 == "watermark"
    assert tags5 == ["meta_num"]


def test_parse_layout_string_garbage_returns_empty():
    assert parse_layout_string("The quick brown fox") == []
    assert parse_layout_string("") == []


def test_resize_img_caps_long_edge():
    from PIL import Image

    img = Image.new("RGB", (3200, 1600))
    resized = resize_img(img, max_size=1600)
    assert max(resized.size) == 1600
    small = Image.new("RGB", (100, 100))
    assert resize_img(small).size == (100, 100)


def test_markdown_converter_headings_tables_formulas():
    results = [
        {"label": "sec_0", "text": "Title", "reading_order": 0},
        {"label": "para", "text": "Hello\nworld", "reading_order": 1},
        {"label": "equ", "text": "E = mc^2", "reading_order": 2},
        {"label": "tab", "text": "<table border='1'><tr><td>x</td></tr></table>", "reading_order": 3},
        {"label": "code", "text": "print('hi')", "reading_order": 4},
        {"label": "", "text": "", "reading_order": 5},
    ]
    md = MarkdownConverter().convert(results)
    assert "# Title" in md
    assert "Hello world" in md
    assert "$$E = mc^2$$" in md
    assert "<table><tr><td>x</td></tr></table>" in md
    assert "```bash\nprint('hi')\n```" in md


def test_extract_table_strips_attributes():
    html = "<table class='x' border=1><tr><td>1</td></tr></table>"
    assert extract_table_from_html(html) == "<table><tr><td>1</td></tr></table>"


def test_truncate_repeated_tail():
    s = "abc" + "xy" * 50
    out = truncate_repeated_tail(s, threshold=20, keep=1)
    assert out == "abcxy"
    assert truncate_repeated_tail("normal text") == "normal text"
