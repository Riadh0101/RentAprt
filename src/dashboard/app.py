import os
from tabulate import tabulate
from ..db.database import Database

class DashboardApp:
    def __init__(self, db: Database):
        self.db = db

    def render(self):
        stats = self.db.get_statistics()
        top_props = self.db.get_top_properties(limit=10, min_score=60)

        print("\n" + "=" * 80)
        print("  HERMES AUTONOMOUS RENTAL MONITORING SYSTEM - LIVE DASHBOARD")
        print("=" * 80)
        
        print("\n[SYSTEM SUMMARY]")
        print(f"  • Total Tracked:        {stats['total_tracked']}")
        print(f"  • Active Listings:      {stats['active_properties']}")
        print(f"  • Price Reductions:     {stats['price_reductions_total']}")
        print(f"  • Highest Score:        {stats['top_score']}/100")
        print(f"  • Average Monthly Rent: {stats['average_price']:,} TL")
        print(f"  • Lowest Monthly Rent:  {stats['lowest_price']:,} TL")

        print("\n[TOP ACCOMMODATION CANDIDATES]")
        if not top_props:
            print("  No listings tracked yet. Run a search cycle first.")
        else:
            table_data = []
            for p in top_props:
                table_data.append([
                    p.id,
                    p.score,
                    p.location[:15],
                    p.rooms,
                    f"{int(p.effective_monthly_price):,} TL",
                    "YES" if p.furnished else "NO",
                    f"{p.university_distance_min}m" if p.university_distance_min else "-",
                    f"{p.metrobus_distance_min}m" if p.metrobus_distance_min else "-",
                    p.source[:12],
                    p.title[:30]
                ])

            headers = ["ID", "Score", "Location", "Type", "Rent/mo", "Furn", "IAU", "Mbus", "Source", "Title"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))

        print("\n" + "=" * 80)
