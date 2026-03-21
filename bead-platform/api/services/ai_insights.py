from ..db import get_conn
from typing import Dict, List, Any

def get_insights() -> Dict[str, Any]:
    """Calculate AI-driven insights from BEAD platform data"""
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Calculate cost per location
        cur.execute("""
            SELECT 
                SUM(COALESCE(e.amount, 0)) / NULLIF(COUNT(DISTINCT sl.id), 0) as cost_per_location,
                COUNT(DISTINCT p.id) as total_projects,
                COUNT(DISTINCT sl.id) as total_locations,
                SUM(COALESCE(fr.miles, 0)) as total_miles,
                ROUND(100.0 * COUNT(DISTINCT CASE WHEN sl.served THEN sl.id END) / NULLIF(COUNT(DISTINCT sl.id), 1), 2) as coverage_percent
            FROM projects p
            LEFT JOIN fiber_routes fr ON p.id = fr.project_id
            LEFT JOIN service_locations sl ON p.id = sl.id
            LEFT JOIN expenditures e ON p.id = e.project_id
        """)
        
        row = cur.fetchone()
        cost_per_location = row[0] or 0
        total_projects = row[1] or 0
        total_locations = row[2] or 0
        total_miles = row[3] or 0
        coverage_percent = row[4] or 0

        # Generate insights
        insights = []
        
        if cost_per_location > 5000:
            insights.append("⚠️ High cost per location detected. Consider optimization strategies.")
        elif cost_per_location > 0:
            insights.append("✅ Cost per location is within acceptable range")
        
        if coverage_percent > 80:
            insights.append(f"🎯 High coverage at {coverage_percent}% of planned locations")
        elif coverage_percent > 50:
            insights.append(f"📈 Coverage at {coverage_percent}% - halfway to target")
        
        if total_miles > 1000:
            insights.append(f"🛣️ Extensive fiber deployment: {total_miles:,.0f} miles")
        
        if total_projects > 5:
            insights.append(f"🚀 Multiple projects active: {total_projects} ongoing initiatives")

        conn.close()
        
        return {
            "cost_per_location": round(cost_per_location, 2),
            "total_projects": total_projects,
            "total_locations": total_locations,
            "total_miles": round(total_miles, 2),
            "coverage_percent": coverage_percent,
            "insights": insights if insights else ["📊 No major insights at this time"]
        }
    except Exception as e:
        return {
            "error": str(e),
            "insights": ["⚠️ Unable to calculate insights"]
        }