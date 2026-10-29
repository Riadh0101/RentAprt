"""Terminal views: cycle summary and the top-listings dashboard."""
from typing import List, Sequence

from .database import Database
from .models import FURNISHED, PARTIAL, CycleReport, Listing


def _table(headers: Sequence[str], rows: List[Sequence[str]]) -> str:
    widths = [max([len(str(h))] + [len(str(r[i])) for r in rows]) for i, h in enumerate(headers)]
    line = "+".join("-" * (w + 2) for w in widths)
    fmt = lambda cells: "|".join(f" {str(c):<{w}} " for c, w in zip(cells, widths))
    return "\n".join([line, fmt(headers), line, *(fmt(r) for r in rows), line])


def _furn(code) -> str:
    return {FURNISHED: "yes", PARTIAL: "part"}.get(code, "no")


def render_listings(listings: Sequence[Listing]) -> str:
    rows = [[
        p.id, p.score, p.classification, p.neighborhood[:18], p.rooms or "?",
        f"{p.effective_cost:,.0f}", _furn(p.furnished),
        f"{p.univ_walk_min}m" if p.univ_walk_min is not None else "-",
        f"{p.metrobus_walk_min}m" if p.metrobus_walk_min is not None else "-",
        p.title[:34],
    ] for p in listings]
    headers = ["ID", "Score", "Class", "Area", "Rooms", "TL/mo", "Furn", "IAU", "Mbus", "Title"]
    return _table(headers, rows)


def render_dashboard(db: Database, min_score: int = 0, limit: int = 15) -> str:
    s = db.statistics()
    out = [
        "=" * 80,
        "  HERMES RENTAL MONITOR — DASHBOARD",
        "=" * 80,
        f"  Active listings: {s['active']}  (tracked {s['total_tracked']}, removed {s['removed']})",
        f"  Last 24h: {s['new_recent']} new, {s['price_drops_recent']} price drops, {s['runs_recent']} cycles",
        f"  Monthly cost incl. aidat: avg {s['average_cost']:,} TL, lowest {s['lowest_cost']:,} TL, "
        f"top score {s['top_score']}/100",
        "",
    ]
    top = db.active_listings(min_score=min_score, limit=limit)
    if top:
        out.append(render_listings(top))
        out.extend(f"  [{p.id}] {p.url}" for p in top[:5])
    else:
        out.append("  No listings yet — run `python main.py run-once`.")
    return "\n".join(out)


def render_cycle(report: CycleReport) -> str:
    return "\n".join([
        "─" * 70,
        "📊 ملخص دورة المراقبة (CYCLE SUMMARY):",
        f"  • مصادر البحث الناجحة:          {report.feeds_checked - report.feeds_failed}/{report.feeds_checked}",
        f"  • إجمالي الإعلانات المرشحة:     {report.candidates}",
        f"  • تم التحقق منها مباشرة:        {report.verified}",
        f"  • المستبعدة (سعر/نوع/شروط):     {report.rejected}",
        f"  • شقق جديدة:                     {report.new}",
        f"  • انخفاض بالأسعار:              {report.price_drops}",
        f"  • إعلانات أزيلت:                 {report.removed}",
        f"  • إشعارات تيليجرام المرسلة:      {report.alerts_sent}",
        f"  • أخطاء:                          {report.errors}",
        "─" * 70,
    ])
