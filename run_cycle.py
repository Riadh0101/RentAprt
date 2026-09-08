import sys
import os
import logging
from datetime import datetime

# Configure Windows UTF-8 stdout/stderr
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from src.database import init_db, upsert_property, has_been_notified
from src.filter_scorer import cheap_filter, score_property
from src.searcher import fetch_cycle_candidates
from src.notifier import dispatch_alert, send_email_report
from src.config import SCORE_INSTANT_ALERT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("HermesRunner")

def run_single_cycle(cycle_index: int = 0, force_notify: bool = False) -> dict:
    """Execute one complete monitoring cycle."""
    print("\n" + "═"*70)
    print(f"🚀 HERMES AUTONOMOUS RENTAL MONITOR — دورة المراقبة رقم #{cycle_index}")
    print(f"⏰ التوقيت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═"*70)

    # 1. Initialize Database
    init_db()

    # 2. Fetch candidates
    raw_candidates = fetch_cycle_candidates(cycle_index)
    logger.info(f"Discovered {len(raw_candidates)} candidate listings.")

    stats = {
        "discovered": len(raw_candidates),
        "passed_filter": 0,
        "rejected_filter": 0,
        "new_inserted": 0,
        "price_drops": 0,
        "unchanged": 0,
        "alerts_sent": 0,
        "top_matches": []
    }

    # 3. Process each listing
    for raw in raw_candidates:
        passed, reason = cheap_filter(raw)
        if not passed:
            stats["rejected_filter"] += 1
            continue

        stats["passed_filter"] += 1

        # Score the candidate
        total_score, breakdown, classification = score_property(raw)
        raw["score"] = total_score
        raw["score_breakdown"] = breakdown
        raw["classification"] = classification

        # Deduplicate & record in SQLite
        status, updated_prop = upsert_property(raw)
        stats["top_matches"].append(updated_prop)

        if status == "NEW":
            stats["new_inserted"] += 1
        elif status == "PRICE_DROP":
            stats["price_drops"] += 1
        else:
            stats["unchanged"] += 1

        # Alert condition
        should_alert = (status == "NEW" and total_score >= SCORE_INSTANT_ALERT) or \
                       (status == "PRICE_DROP") or \
                       (force_notify and total_score >= SCORE_INSTANT_ALERT)

        if should_alert:
            alert_t = "PRICE_DROP" if status == "PRICE_DROP" else "NEW_MATCH"
            logger.info(f"🔥 DISPATCHING ALERT: '{raw['title'][:40]}...' Score: {total_score} [{classification}]")
            sent = dispatch_alert(updated_prop, alert_type=alert_t)
            if sent:
                stats["alerts_sent"] += 1

    # Print Cycle Summary
    print("\n" + "─"*70)
    print("📊 ملخص دورة المراقبة (CYCLE SUMMARY):")
    print(f"  • إجمالي الإعلانات المفحوصة:   {stats['discovered']}")
    print(f"  • المطابقة للفلتر الأولي:       {stats['passed_filter']}")
    print(f"  • المستبعدة (سعر/نوع/شروط):     {stats['rejected_filter']}")
    print(f"  • شقق جديدة مسجلة بقاعدة البيانات: {stats['new_inserted']}")
    print(f"  • رصد انخفاض بالأسعار:         {stats['price_drops']}")
    print(f"  • إشعارات التيليجرام المرسلة:  {stats['alerts_sent']}")
    print("─"*70)

    if stats["top_matches"]:
        # Sort by score descending
        stats["top_matches"].sort(key=lambda x: x.get("score", 0), reverse=True)
        print("\n🏆 أفضل الشقق المؤهلة في هذه الدورة (مرتبة حسب التقييم):")
        for idx, p in enumerate(stats["top_matches"], 1):
            price_fmt = f"{float(p.get('price_tl', 0)):,.0f} TL"
            print(f"  {idx}. [{p.get('score')}/100 - {p.get('classification')}] {p.get('title')}")
            print(f"     📍 المنطقة: {p.get('location')} | السعر: {price_fmt} | غرف: {p.get('rooms')}")
            print(f"     🎓 جامعة أيدن: {p.get('univ_dist_min')} دقيقة مشياً | 🚇 المتروباص: {p.get('metrobus_dist_min')} دقيقة")
    if stats["top_matches"]:
        send_email_report(stats["top_matches"], "Riadh0101@yahoo.fr")

    return stats

if __name__ == "__main__":
    force = "--notify" in sys.argv or "-n" in sys.argv
    run_single_cycle(0, force_notify=force)
