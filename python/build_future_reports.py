from __future__ import annotations

import argparse
import html
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from config import ensure_directories, load_config, resolve_path
from db import connect


@dataclass
class TownProfile:
    town: str
    town_rank: int
    mobility_need_town_rank: int
    sample_population: int
    acs_town_population: int
    pct_pop_800m: float
    weighted_accessibility_score: float
    avg_nearest_stop_m: float
    avg_transit_score: float
    avg_sidewalk_score: float
    avg_school_score: float
    avg_hospital_score: float
    sidewalk_km: float
    sidewalk_m_per_1000_residents: float
    underserved_units: int
    weighted_mobility_need_index: float
    median_household_income: float
    pct_zero_vehicle_households: float
    pct_below_poverty: float
    pct_65_plus: float
    pct_with_disability: float
    high_need_units: int
    dominant_need_driver: str
    future_livability_score: float = 0
    investor_opportunity_score: float = 0
    investment_lane: str = ""
    missing_needs: list[str] | None = None


def value(row: dict[str, Any], key: str, default: Any = 0) -> Any:
    result = row.get(key, default)
    if isinstance(result, Decimal):
        return float(result)
    return result if result is not None else default


def rows(cfg: dict[str, Any], sql: str) -> list[dict[str, Any]]:
    with connect(cfg) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [description.name for description in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def normalize(value: float, values: list[float], invert: bool = False) -> float:
    low = min(values)
    high = max(values)
    if high == low:
        score = 50.0
    else:
        score = (value - low) / (high - low) * 100
    return 100 - score if invert else score


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def fetch_profiles(cfg: dict[str, Any]) -> list[TownProfile]:
    data = rows(cfg, """
        SELECT
            a.town,
            a.town_rank,
            m.mobility_need_town_rank,
            a.total_population AS sample_population,
            m.acs_town_population,
            a.pct_pop_800m,
            a.weighted_accessibility_score,
            a.avg_nearest_stop_m,
            a.avg_transit_score,
            a.avg_sidewalk_score,
            a.avg_school_score,
            a.avg_hospital_score,
            a.sidewalk_km,
            a.sidewalk_m_per_1000_residents,
            a.underserved_units,
            m.weighted_mobility_need_index,
            a.median_household_income,
            m.pct_zero_vehicle_households,
            m.pct_below_poverty,
            m.pct_65_plus,
            m.pct_with_disability,
            m.high_need_units,
            m.dominant_need_driver
        FROM town_accessibility_kpis a
        JOIN town_mobility_need_index m
            ON m.town = a.town
        ORDER BY a.town;
    """)
    profiles = [
        TownProfile(
            town=row["town"],
            town_rank=int(row["town_rank"]),
            mobility_need_town_rank=int(row["mobility_need_town_rank"]),
            sample_population=int(value(row, "sample_population")),
            acs_town_population=int(value(row, "acs_town_population")),
            pct_pop_800m=float(value(row, "pct_pop_800m")),
            weighted_accessibility_score=float(value(row, "weighted_accessibility_score")),
            avg_nearest_stop_m=float(value(row, "avg_nearest_stop_m")),
            avg_transit_score=float(value(row, "avg_transit_score")),
            avg_sidewalk_score=float(value(row, "avg_sidewalk_score")),
            avg_school_score=float(value(row, "avg_school_score")),
            avg_hospital_score=float(value(row, "avg_hospital_score")),
            sidewalk_km=float(value(row, "sidewalk_km")),
            sidewalk_m_per_1000_residents=float(value(row, "sidewalk_m_per_1000_residents")),
            underserved_units=int(value(row, "underserved_units")),
            weighted_mobility_need_index=float(value(row, "weighted_mobility_need_index")),
            median_household_income=float(value(row, "median_household_income")),
            pct_zero_vehicle_households=float(value(row, "pct_zero_vehicle_households")),
            pct_below_poverty=float(value(row, "pct_below_poverty")),
            pct_65_plus=float(value(row, "pct_65_plus")),
            pct_with_disability=float(value(row, "pct_with_disability")),
            high_need_units=int(value(row, "high_need_units")),
            dominant_need_driver=row["dominant_need_driver"] or "",
        )
        for row in data
    ]
    score_profiles(profiles)
    return profiles


def missing_needs(profile: TownProfile) -> list[str]:
    needs: list[str] = []
    if profile.pct_pop_800m < 50:
        needs.append("stronger transit access or last-mile mobility")
    if profile.avg_transit_score < 80:
        needs.append("more usable transit service/frequency")
    if profile.avg_sidewalk_score < 35:
        needs.append("sidewalk connectivity and safer walk-to-stop routes")
    if profile.avg_hospital_score < 35:
        needs.append("healthcare access, local clinics, or medical shuttle service")
    if profile.avg_school_score < 35:
        needs.append("school/youth access and family-service proximity")
    if profile.pct_zero_vehicle_households >= 10:
        needs.append("car-light housing and reliable non-car mobility")
    if profile.pct_below_poverty >= 8:
        needs.append("affordable/workforce housing and anti-displacement support")
    if profile.pct_65_plus >= 20:
        needs.append("age-friendly housing, healthcare access, and senior mobility")
    if profile.pct_with_disability >= 12:
        needs.append("accessible housing, ADA routes, and paratransit coordination")
    if profile.weighted_accessibility_score < 40:
        needs.append("foundational access investment before dense growth")
    if not needs:
        needs.append("continued housing supply, climate resilience, and affordability monitoring")
    return needs


def investment_lane(profile: TownProfile) -> str:
    if profile.weighted_accessibility_score >= 70 and profile.pct_zero_vehicle_households >= 10:
        return "urban mixed-use, car-light rentals, small business, and workforce services"
    if profile.weighted_accessibility_score >= 70:
        return "balanced residential, commuter-friendly housing, and local services"
    if profile.pct_65_plus >= 20 and profile.median_household_income >= 100000:
        return "age-friendly housing, healthcare services, and premium suburban living"
    if profile.weighted_mobility_need_index >= 25:
        return "value-add mobility, workforce housing, clinics, and town-center infrastructure"
    if profile.avg_nearest_stop_m < 100:
        return "transit-proximate housing and main-street redevelopment"
    return "selective housing, local services, and infrastructure-led long-term growth"


def score_profiles(profiles: list[TownProfile]) -> None:
    incomes = [p.median_household_income for p in profiles]
    populations = [p.acs_town_population for p in profiles]
    need_values = [p.weighted_mobility_need_index for p in profiles]
    gap_values = [100 - p.weighted_accessibility_score for p in profiles]
    for p in profiles:
        social_stability = clamp(100 - (p.pct_below_poverty * 3) - (p.pct_zero_vehicle_households * 1.5))
        income_score = normalize(p.median_household_income, incomes)
        inverse_need = clamp(100 - p.weighted_mobility_need_index * 2.5)
        distance_score = clamp(100 - (p.avg_nearest_stop_m / 8))
        p.future_livability_score = round(
            0.22 * p.weighted_accessibility_score
            + 0.15 * p.pct_pop_800m
            + 0.13 * p.avg_sidewalk_score
            + 0.10 * p.avg_hospital_score
            + 0.14 * income_score
            + 0.16 * social_stability
            + 0.10 * inverse_need,
            2,
        )
        need_score = normalize(p.weighted_mobility_need_index, need_values)
        access_gap_score = normalize(100 - p.weighted_accessibility_score, gap_values)
        population_score = normalize(p.acs_town_population, populations)
        demand_need = clamp(p.pct_zero_vehicle_households * 3 + p.pct_below_poverty * 3 + p.pct_65_plus)
        coverage_gap = 100 - p.pct_pop_800m
        p.investor_opportunity_score = round(
            0.22 * need_score
            + 0.20 * access_gap_score
            + 0.18 * population_score
            + 0.14 * demand_need
            + 0.12 * coverage_gap
            + 0.08 * normalize(p.median_household_income, incomes)
            + 0.06 * distance_score,
            2,
        )
        p.investment_lane = investment_lane(p)
        p.missing_needs = missing_needs(p)


def markdown_table(headers: list[str], rows_: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows_:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def html_table(headers: list[str], rows_: list[list[Any]]) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(str(item))}</td>" for item in row) + "</tr>"
        for row in rows_
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def source_block() -> str:
    return """
## Source Context

- U.S. Census Bureau ACS 2024 5-year table-based Summary File: town population, income, poverty, zero-vehicle households, age 65+, and disability.
- MaineHousing, State of Maine Housing Production Needs Study: Maine needs more housing supply and better alignment between housing location, economic opportunity, and quality of life.
- Maine Department of Economic and Community Development, 2024 Economic Development Strategy Reset: workforce growth depends on supporting infrastructure such as housing, childcare, transportation, broadband, and local hubs.
- Maine Climate Plan: future communities need lower-emission transportation choices and climate-aware growth.
- HUD Location Affordability framing: housing decisions are stronger when transportation cost and access are evaluated together.
""".strip()


def build_main_markdown(profiles: list[TownProfile]) -> str:
    livability = sorted(profiles, key=lambda p: p.future_livability_score, reverse=True)
    opportunity = sorted(profiles, key=lambda p: p.investor_opportunity_score, reverse=True)
    best_live = livability[0]
    best_invest = opportunity[0]
    rows_live = [
        [
            rank,
            p.town,
            fmt(p.future_livability_score),
            fmt(p.weighted_accessibility_score),
            f"{fmt(p.pct_pop_800m)}%",
            f"${fmt(p.median_household_income)}",
            f"{fmt(p.pct_below_poverty)}%",
            f"{fmt(p.pct_zero_vehicle_households)}%",
            p.investment_lane,
        ]
        for rank, p in enumerate(livability, start=1)
    ]
    rows_invest = [
        [
            rank,
            p.town,
            fmt(p.investor_opportunity_score),
            fmt(p.weighted_mobility_need_index),
            f"{fmt(100 - p.pct_pop_800m)}%",
            f"{fmt(p.pct_65_plus)}%",
            f"{fmt(p.pct_with_disability)}%",
            p.investment_lane,
        ]
        for rank, p in enumerate(opportunity, start=1)
    ]
    lines = [
        "# Future Livability and Investment Report",
        "",
        "## Bottom Line",
        "",
        f"- Best balanced place to live in the current prototype: **{best_live.town}**.",
        f"- Best broad investor/opportunity screen: **{best_invest.town}**.",
        "- Best urban/career and car-light living play: **Portland**, especially where access gaps and zero-car households overlap.",
        "- Best next-wave value-add screen: **Westbrook** and **Gorham**, but for different reasons: Westbrook has transit-proximate bones; Gorham has larger infrastructure gaps.",
        "",
        "This is a screening report, not financial advice. It ranks towns from the current Greater Portland prototype using transit access, walkability, ACS demographics, mobility need, income, and service gaps.",
        "",
        "## What Americans Usually Need From A Future-Proof Place",
        "",
        "- Housing that remains affordable relative to income.",
        "- Good access to jobs, education, healthcare, groceries, and daily services.",
        "- Transportation choices beyond a private car.",
        "- Safe walkable streets, especially for children, older adults, and disabled residents.",
        "- Climate-aware growth, resilient infrastructure, and lower transportation emissions.",
        "- Local services that match the population: childcare, clinics, senior services, trades, small business, and workforce supports.",
        "",
        "## Future Livability Ranking",
        "",
        markdown_table(
            ["Rank", "Town", "Future Livability", "Access", "800m Coverage", "Median Income", "Poverty", "Zero-Car HH", "Best-Fit Lane"],
            rows_live,
        ),
        "",
        f"**Why {best_live.town} leads:** it combines strong access, good coverage, relatively low mobility need, and enough service proximity to be resilient for households that want convenience without depending entirely on downtown Portland.",
        "",
        "## Investor / Opportunity Ranking",
        "",
        markdown_table(
            ["Rank", "Town", "Opportunity", "Need Index", "Coverage Gap", "Age 65+", "Disability", "Opportunity Lane"],
            rows_invest,
        ),
        "",
        f"**Why {best_invest.town} screens high for opportunity:** the model finds a strong gap between current access and future need. That often points to infrastructure, housing, mobility, healthcare, or local-service opportunities.",
        "",
        "## What Each Town Is Missing",
        "",
    ]
    for p in profiles:
        lines.extend([
            f"### {p.town}",
            "",
            f"- Current lane: {p.investment_lane}.",
            f"- Biggest missing needs: {', '.join(p.missing_needs or [])}.",
            f"- Signal: access score {fmt(p.weighted_accessibility_score)}, mobility need {fmt(p.weighted_mobility_need_index)}, ACS population {fmt(p.acs_town_population)}.",
            "",
        ])
    lines.extend(["", source_block(), ""])
    return "\n".join(lines)


def build_brief_markdown(profiles: list[TownProfile]) -> str:
    live = sorted(profiles, key=lambda p: p.future_livability_score, reverse=True)
    invest = sorted(profiles, key=lambda p: p.investor_opportunity_score, reverse=True)
    lines = [
        "# Visionary Realtor / Investor Brief",
        "",
        "## Fast Read",
        "",
        f"- Live-first pick: **{live[0].town}**.",
        f"- Opportunity-first pick: **{invest[0].town}**.",
        "- Portland remains the brand-name urban anchor, but its best future story is targeted infill and car-light living, not blanket growth.",
        "- Westbrook has main-street/value-add appeal because it scores well on access but still has visible service and sidewalk gaps.",
        "- Gorham and Scarborough screen as infrastructure-led plays: attractive long-term, but missing stronger mobility and essential-service proximity.",
        "- Falmouth is a premium/age-friendly play: strong incomes and older-adult demand, but less transit depth.",
        "",
        "## Town Positioning",
        "",
    ]
    for p in sorted(profiles, key=lambda item: item.town):
        lines.extend([
            f"### {p.town}",
            "",
            f"- Position: {p.investment_lane}.",
            f"- Future livability score: {fmt(p.future_livability_score)}.",
            f"- Investor opportunity score: {fmt(p.investor_opportunity_score)}.",
            f"- Missing: {', '.join(p.missing_needs or [])}.",
            "",
        ])
    return "\n".join(lines)


def build_scorecards_markdown(profiles: list[TownProfile]) -> str:
    lines = ["# Town Future Scorecards", ""]
    for p in sorted(profiles, key=lambda item: item.future_livability_score, reverse=True):
        lines.extend([
            f"## {p.town}",
            "",
            markdown_table(
                ["Metric", "Value"],
                [
                    ["Future livability score", fmt(p.future_livability_score)],
                    ["Investor opportunity score", fmt(p.investor_opportunity_score)],
                    ["Accessibility score", fmt(p.weighted_accessibility_score)],
                    ["Mobility Need Index", fmt(p.weighted_mobility_need_index)],
                    ["800 m transit coverage", f"{fmt(p.pct_pop_800m)}%"],
                    ["ACS population", fmt(p.acs_town_population)],
                    ["Median household income", f"${fmt(p.median_household_income)}"],
                    ["Zero-car households", f"{fmt(p.pct_zero_vehicle_households)}%"],
                    ["Poverty", f"{fmt(p.pct_below_poverty)}%"],
                    ["Age 65+", f"{fmt(p.pct_65_plus)}%"],
                    ["Disability", f"{fmt(p.pct_with_disability)}%"],
                    ["Best-fit lane", p.investment_lane],
                ],
            ),
            "",
            f"Missing needs: {', '.join(p.missing_needs or [])}.",
            "",
        ])
    return "\n".join(lines)


def build_needs_markdown(profiles: list[TownProfile]) -> str:
    rows_ = [
        [
            p.town,
            fmt(p.weighted_mobility_need_index),
            p.dominant_need_driver,
            "; ".join(p.missing_needs or []),
            p.investment_lane,
        ]
        for p in sorted(profiles, key=lambda item: item.weighted_mobility_need_index, reverse=True)
    ]
    return "\n".join([
        "# Missing Needs Matrix",
        "",
        markdown_table(["Town", "Need Index", "Dominant Driver", "Missing Needs", "Potential Opportunity Lane"], rows_),
        "",
        "Use this as a screening matrix for housing, mobility, healthcare, local-service, and infrastructure opportunities.",
        "",
    ])


def build_html_document(markdown: str, title: str) -> str:
    sections: list[str] = []
    lines = markdown.splitlines()
    in_list = False
    in_table = False
    table_lines: list[str] = []

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            sections.append("</ul>")
            in_list = False

    def flush_table() -> None:
        nonlocal in_table, table_lines
        if not in_table:
            return
        headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
        data_rows = [
            [cell.strip() for cell in row.strip("|").split("|")]
            for row in table_lines[2:]
            if row.strip()
        ]
        sections.append(html_table(headers, data_rows))
        table_lines = []
        in_table = False

    for line in lines:
        if line.startswith("|"):
            flush_list()
            in_table = True
            table_lines.append(line)
            continue
        flush_table()
        if not line:
            flush_list()
            continue
        if line.startswith("### "):
            flush_list()
            sections.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            flush_list()
            sections.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            flush_list()
            sections.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("- "):
            if not in_list:
                sections.append("<ul>")
                in_list = True
            text = html.escape(line[2:])
            text = text.replace("**", "")
            sections.append(f"<li>{text}</li>")
        else:
            flush_list()
            text = html.escape(line).replace("**", "")
            sections.append(f"<p>{text}</p>")
    flush_list()
    flush_table()

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    @page {{ size: Letter; margin: 0.55in; }}
    body {{ font-family: Arial, Helvetica, sans-serif; color: #1f2933; line-height: 1.45; margin: 0 auto; max-width: 1080px; padding: 24px; }}
    h1 {{ font-size: 28px; margin: 0 0 12px; color: #123f5f; }}
    h2 {{ font-size: 18px; color: #135c88; border-bottom: 1px solid #d7dde5; padding-bottom: 4px; margin-top: 24px; }}
    h3 {{ font-size: 14px; color: #1f2933; margin-top: 18px; }}
    p, li {{ font-size: 11.5px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 10px; margin: 10px 0 16px; }}
    th, td {{ border: 1px solid #d7dde5; padding: 6px; text-align: left; vertical-align: top; }}
    th {{ background: #e9f0f7; }}
    tr:nth-child(even) td {{ background: #fbfcfe; }}
  </style>
</head>
<body>
  {''.join(sections)}
</body>
</html>
"""


def find_browser() -> Path | None:
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    return next((path for path in candidates if path.exists()), None)


def export_pdf(html_path: Path) -> Path:
    browser = find_browser()
    if not browser:
        raise RuntimeError("No supported browser found for HTML-to-PDF export.")
    pdf_path = html_path.with_suffix(".pdf")
    if pdf_path.exists():
        pdf_path.unlink()
    subprocess.run(
        [
            str(browser),
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ],
        check=True,
    )
    return pdf_path


def write_reports(config_path: str = "configs/project.toml", pdf: bool = False) -> list[Path]:
    cfg = load_config(config_path)
    ensure_directories(cfg)
    reports_dir = resolve_path(cfg, "reports_dir")
    profiles = fetch_profiles(cfg)

    outputs: list[Path] = []
    artifacts = {
        "future_livability_investment_report": build_main_markdown(profiles),
        "visionary_realtor_investor_brief": build_brief_markdown(profiles),
        "town_future_scorecards": build_scorecards_markdown(profiles),
        "town_missing_needs_matrix": build_needs_markdown(profiles),
    }
    for stem, markdown in artifacts.items():
        md_path = reports_dir / f"{stem}.md"
        md_path.write_text(markdown, encoding="utf-8")
        outputs.append(md_path)
        if stem == "future_livability_investment_report":
            html_path = reports_dir / f"{stem}.html"
            html_path.write_text(build_html_document(markdown, "Future Livability and Investment Report"), encoding="utf-8")
            outputs.append(html_path)
            if pdf:
                outputs.append(export_pdf(html_path))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Build future livability, investment, and missing-needs reports.")
    parser.add_argument("--config", default="configs/project.toml")
    parser.add_argument("--pdf", action="store_true", help="Export the main HTML report to PDF.")
    args = parser.parse_args()
    for path in write_reports(args.config, pdf=args.pdf):
        print(path)


if __name__ == "__main__":
    main()
