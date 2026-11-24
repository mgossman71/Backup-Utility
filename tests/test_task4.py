"""Task 4 acceptance tests: design system assets + styled, placeholder-rich pages."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "static/css/design-system.css").read_text()


def test_assets_are_served(client):
    for path in [
        "/static/css/reset.css",
        "/static/css/design-system.css",
        "/static/js/layout.js",
        "/static/favicon.svg",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, path


def test_palette_and_typography_tokens_defined():
    # Approved palette colors.
    for token in ["#0B1020", "#141B2D", "#4F8CFF", "#34C759", "#FF5B5B", "#FFB300", "#7DD3FC"]:
        assert token in CSS
    # Typography stacks.
    assert "Inter" in CSS
    assert "JetBrains Mono" in CSS
    # Layout: max width + breakpoints + topbar height.
    assert "1280px" in CSS
    assert "max-width: 767px" in CSS
    assert "min-width: 1280px" in CSS


def test_custom_controls_not_browser_default():
    # Custom checkbox/select/switch suppress native appearance.
    assert "appearance: none" in CSS
    assert ".check input" in CSS
    assert ".select" in CSS
    # Status pills include an icon (never color alone).
    assert ".pill svg" in CSS
    # Visible focus ring: 2px primary outline with offset.
    assert "outline: 2px solid var(--primary)" in CSS
    assert "outline-offset: 2px" in CSS


def test_root_page_uses_design_system_and_placeholders(client):
    html = client.get("/").text
    assert 'href="/static/css/design-system.css"' in html
    assert 'class="hero"' in html
    assert "JetBrains+Mono" in html  # typography link
    assert '<meta name="viewport"' in html
    # Placeholder/empty state uses cohesive line-art SVG (not blank).
    assert "empty-state" in html
    assert "<svg" in html
    # Status pill renders approved label with icon (text + icon, not color alone).
    assert "No Runs" in html
    # Contact + pricing copy in footer.
    assert "Contact: Your system administration team." in html
    assert "Pricing: Self-hosted with no license fee." in html


def test_placeholder_strategies_present():
    # Hero procedural gradient + hex grid, sparkline, skeleton rows.
    assert "linear-gradient(135deg, #0B1020 0%, #14243F 100%)" in CSS
    assert "skeleton" in CSS
    spark = (ROOT / "templates/components/icon.html").read_text()
    assert "sparkline" in spark
