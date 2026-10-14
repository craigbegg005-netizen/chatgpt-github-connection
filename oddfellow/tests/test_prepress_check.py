"""
The prepress tool must reproduce the hand analysis it replaces, number for number.

``commerce/prepress/SAMURAI-PREPRESS-2026-10-14.md`` reached a strategy-level conclusion
by hand: a 1122x1402 source cannot make a 300-DPI print at any size Fourthwall offers, so
the wall-art launch is a 5x7 product rather than a "matte art print" range. That document
also says the analysis must be re-run for every collection and again when the real file
arrives -- so the arithmetic now lives in ``prepress_check.py``, and this file holds it to
the document's own table.

If these two ever disagree, one of them is wrong. That is the whole point of asserting
them against each other rather than trusting either alone.
"""

from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PREPRESS = os.path.join(REPO, "commerce", "prepress")

sys.path.insert(0, PREPRESS)

from prepress_check import (  # noqa: E402
    FOURTHWALL_POSTER_SIZES,
    assess,
    parse_sizes,
    upscale_factor,
    verdict,
)

# The document's table, verbatim: size -> (DPI, crop %). Transcribed, not recomputed.
DOC_TABLE = {
    "5x7": (200, 10.7),
    "8x10": (140, 0.0),
    "11x14": (100, 1.8),
    "10x10": (112, 20.0),
    "12x16": (88, 6.3),
    "12x18": (78, 16.7),
    "16x20": (70, 0.0),
    "18x24": (58, 6.3),
    "20x30": (47, 16.7),
    "24x36": (39, 16.7),
}

SOURCE = (1122, 1402)


def test_the_tool_reproduces_the_documents_table():
    assert len(FOURTHWALL_POSTER_SIZES) == len(DOC_TABLE), (
        "the size list and the document's table have different lengths -- one moved"
    )
    for pw, ph in FOURTHWALL_POSTER_SIZES:
        a = assess(*SOURCE, pw, ph)
        key = a["size"]
        assert key in DOC_TABLE, f"size {key} is not in the document's table"
        want_dpi, want_crop = DOC_TABLE[key]
        assert round(a["dpi"]) == want_dpi, (
            f"{key}: tool says {a['dpi']:.1f} DPI, document says {want_dpi}"
        )
        assert abs(a["crop_pct"] - want_crop) < 0.05, (
            f"{key}: tool says {a['crop_pct']:.1f}% crop, document says {want_crop}%"
        )


def test_no_offered_size_reaches_300_dpi():
    """The document's headline, asserted rather than described."""
    best = max(assess(*SOURCE, pw, ph)["dpi"] for pw, ph in FOURTHWALL_POSTER_SIZES)
    assert best < 300, f"a size reached {best:.0f} DPI, so the headline is wrong"
    assert round(best) == 200, "the best available size is no longer 5x7 at 200 DPI"


def test_the_source_is_smaller_than_the_smallest_poster_at_300_dpi():
    w_in, h_in = SOURCE[0] / 300, SOURCE[1] / 300
    assert w_in < 5 and h_in < 7, (
        f"at 300 DPI the source covers {w_in:.2f}x{h_in:.2f} in, which is not smaller "
        "than the 5x7 minimum -- the document's headline would be wrong"
    )


def test_aspect_is_a_second_constraint_independent_of_resolution():
    """8x10 and 16x20 share the source's 4:5 aspect exactly, so they need no crop.

    Worth its own test because it is what makes them look attractive while their DPI
    makes them unusable -- two constraints pulling opposite ways.
    """
    for size in ("8x10", "16x20"):
        pw, ph = (float(x) for x in size.split("x"))
        a = assess(*SOURCE, pw, ph)
        assert a["crop_axis"] == "none", f"{size} unexpectedly needs a crop"
        assert a["crop_pct"] == 0.0


def test_upscale_factors_are_governed_by_the_limiting_dimension():
    """The document's 24x36 row used the WIDTH ratio where the HEIGHT governs.

    8x10 and 16x20 are exact 4:5 matches, so both dimensions scale equally and the
    question does not arise. 24x36 is 2:3, so it does: 7200/1122 = 6.4x, but
    10800/1402 = 7.7x, and 7.7x is what is actually required. The same row already
    reports 39 DPI, which is the height-limited figure -- so the row contradicted
    itself, and the correction makes the document's own point stronger, not weaker.
    """
    for size, want in (("8x10", 2.1), ("16x20", 4.3), ("24x36", 7.7)):
        pw, ph = (float(x) for x in size.split("x"))
        got = upscale_factor(*SOURCE, pw, ph, 300)
        assert abs(got - want) < 0.05, f"{size}: tool says {got:.2f}x, expected {want}x"


def test_a_large_enough_source_passes_cleanly():
    """The control: the tool must be able to say yes, or it is not measuring anything.

    Without this, every assertion above could hold in a tool that simply always fails.
    """
    big = (3600, 4500)  # 12x15 in at 300 DPI, exact 4:5
    a = assess(*big, 8, 10)
    assert a["dpi"] == 450.0
    assert a["crop_pct"] == 0.0
    assert verdict(a["dpi"], 300) == "OK"


def test_verdict_thresholds():
    assert verdict(300, 300) == "OK"
    assert verdict(299, 300) == "soft"
    assert verdict(150, 300) == "soft"
    assert verdict(149, 300) == "poor"
    assert verdict(100, 300) == "poor"
    assert verdict(99, 300) == "unusable"


def test_parse_sizes_rejects_nonsense():
    assert parse_sizes("5x7, 8x10") == ((5.0, 7.0), (8.0, 10.0))
    with pytest.raises(ValueError):
        parse_sizes("5by7")
    with pytest.raises(ValueError):
        parse_sizes("  ,  ")


def test_assess_rejects_non_positive_dimensions():
    with pytest.raises(ValueError):
        assess(0, 100, 5, 7)
    with pytest.raises(ValueError):
        assess(100, 100, 0, 7)
