import time
import logging
from datetime import datetime
from typing import Dict, Any
from ..config import config
from ..db.database import Database
from ..db.models import SearchRunRecord
from ..search.engine import SearchEngine
from ..deduplication.matcher import DeduplicationMatcher
from ..notification.dispatcher import NotificationDispatcher
from ..notification.telegram import TelegramNotifier

logger = logging.getLogger(__name__)

class SchedulerRunner:
    def __init__(self, db: Database):
        self.db = db
        self.search_engine = SearchEngine()
        self.dispatcher = NotificationDispatcher(self.db)
        self.last_successful_run = None
        self.consecutive_errors = 0

    def run_cycle(self) -> Dict[str, Any]:
        """
        Executes a single monitoring cycle:
        SEARCH -> EXTRACT -> NORMALIZE -> DEDUPLICATE -> SCORE -> DATABASE -> NOTIFY -> LOG
        """
        start_time = datetime.utcnow()
        logger.info(f"=== Starting Monitoring Cycle at {start_time.isoformat()} ===")
        
        sources_checked = 0
        raw_found = 0
        new_listings_count = 0
        price_changes_count = 0
        errors_count = 0

        try:
            # 1. Search, normalize & score
            candidates, sources_checked, raw_found = self.search_engine.execute_search_cycle()
            
            # 2. Process candidates against database & deduplicate
            existing_properties = self.db.get_all_active()

            for cand in candidates:
                try:
                    # Check for duplicates
                    dup = DeduplicationMatcher.find_duplicate(cand, existing_properties, threshold=0.85)
                    if dup:
                        existing_match, sim = dup
                        cand.canonical_id = existing_match.canonical_id
                    
                    # Upsert into database
                    prop_id, action = self.db.upsert_property(cand)
                    cand.id = prop_id

                    if action == "NEW":
                        new_listings_count += 1
                        self.dispatcher.process_and_notify(cand, "NEW_LISTING")
                    elif action == "PRICE_REDUCED":
                        price_changes_count += 1
                        self.dispatcher.process_and_notify(cand, "PRICE_REDUCTION")
                    elif action == "UPDATED":
                        pass

                except Exception as inner_e:
                    logger.error(f"Error processing candidate property {cand.title}: {inner_e}")
                    errors_count += 1

            self.last_successful_run = datetime.utcnow()
            self.consecutive_errors = 0

        except Exception as e:
            logger.error(f"Fatal cycle error: {e}", exc_info=True)
            errors_count += 1
            self.consecutive_errors += 1

        end_time = datetime.utcnow()
        summary = (
            f"Cycle finished in {(end_time - start_time).total_seconds():.1f}s. "
            f"Sources: {sources_checked}, Found: {raw_found}, New: {new_listings_count}, "
            f"Price Reductions: {price_changes_count}, Errors: {errors_count}"
        )
        logger.info(summary)

        # Record run in DB
        self.db.record_run(
            SearchRunRecord(
                started_at=start_time.isoformat(),
                finished_at=end_time.isoformat(),
                sources_checked=sources_checked,
                listings_found=raw_found,
                new_listings=new_listings_count,
                price_changes=price_changes_count,
                errors=errors_count,
                log_summary=summary
            )
        )

        # Health alert if multiple consecutive failures
        if self.consecutive_errors >= 3:
            TelegramNotifier.send_message(
                f"🚨 <b>HERMES MONITORING WARNING</b>\nConsecutive monitoring failures: {self.consecutive_errors}\nLast success: {self.last_successful_run}"
            )

        return {
            "sources_checked": sources_checked,
            "listings_found": raw_found,
            "new_listings": new_listings_count,
            "price_changes": price_changes_count,
            "errors": errors_count,
            "summary": summary
        }

    def generate_daily_digest(self) -> str:
        """
        Generates 24-hour summary report.
        """
        stats = self.db.get_statistics()
        top_props = self.db.get_top_properties(limit=5, min_score=70)
        
        report = "📊 <b>HERMES DAILY RENTAL MARKET SUMMARY</b>\n\n"
        report += f"• <b>Total Properties Tracked:</b> {stats['total_tracked']}\n"
        report += f"• <b>Active Properties:</b> {stats['active_properties']}\n"
        report += f"• <b>Total Price Reductions:</b> {stats['price_reductions_total']}\n"
        report += f"• <b>Average Rent:</b> {stats['average_price']:,} TL\n"
        report += f"• <b>Lowest Rent:</b> {stats['lowest_price']:,} TL\n\n"
        report += "🏆 <b>TOP RECOMMENDATIONS TODAY:</b>\n"

        for idx, p in enumerate(top_props, 1):
            report += f"\n{idx}. <b>{p.title[:45]}...</b>\n"
            report += f"   ⭐ Score: {p.score}/100 | 💰 {int(p.effective_monthly_price):,} TL | 📍 {p.location}\n"
            report += f"   🚇 Metrobus: {p.metrobus_distance_min}m | 🎓 IAU: {p.university_distance_min}m\n"
            report += f"   🔗 <a href='{p.url}'>View Listing</a>\n"

        return report

    def start_monitoring_loop(self, interval_minutes: int = None):
        """
        Runs persistent 20-minute monitoring loop.
        """
        interval = (interval_minutes or config.CYCLE_INTERVAL_MINUTES) * 60
        logger.info(f"Starting continuous monitoring loop (interval: {interval_minutes or config.CYCLE_INTERVAL_MINUTES} minutes)")
        
        # Initial cycle
        self.run_cycle()

        while True:
            try:
                time.sleep(interval)
                self.run_cycle()
            except KeyboardInterrupt:
                logger.info("Monitoring loop stopped by user.")
                break
            except Exception as e:
                logger.error(f"Unexpected loop exception: {e}")
                time.sleep(30)
