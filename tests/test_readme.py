import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_readme_findings_are_the_chart_headlines():
    """The README can't state a finding the charts don't: each one is a chart's generated
    headline, word for word."""
    readme = (ROOT / "README.md").read_text()
    headlines = json.loads((ROOT / "analysis" / "figures" / "en" / "headlines.json").read_text())
    missing = [name for name, chart in headlines.items() if f"**{chart['title']}**" not in readme]
    assert not missing
