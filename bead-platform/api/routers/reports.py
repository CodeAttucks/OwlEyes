from fastapi import APIRouter
from fastapi.responses import FileResponse
from ..db import get_conn
from ..services.ai_insights import get_insights
import pandas as pd
import io
import os
from datetime import datetime

router = APIRouter(prefix="/reports")

@router.get("/")
def get_reports():
    """Get list of available reports"""
    return {
        "reports": [
            {"name": "export", "description": "Export BEAD data to Excel"},
            {"name": "insights", "description": "AI-driven platform insights"},
            {"name": "summary", "description": "Executive summary"}
        ]
    }

@router.get("/export")
def export_report():
    """Export platform data to Excel file"""
    try:
        conn = get_conn()
        
        # Query data
        df_projects = pd.read_sql("""
            SELECT p.name, p.state, p.status, 
                   COUNT(DISTINCT sl.id) as total_locations,
                   COUNT(DISTINCT CASE WHEN sl.served THEN sl.id END) as served_locations,
                   SUM(COALESCE(fr.miles, 0)) as fiber_miles
            FROM projects p
            LEFT JOIN service_locations sl ON p.id = sl.id
            LEFT JOIN fiber_routes fr ON p.id = fr.project_id
            GROUP BY p.name, p.state, p.status
        """, conn)
        
        df_financials = pd.read_sql("""
            SELECT p.name, e.category, SUM(e.amount) as total_amount, COUNT(*) as transactions
            FROM expenditures e
            JOIN projects p ON p.id = e.project_id
            GROUP BY p.name, e.category
        """, conn)
        
        # Create Excel file with multiple sheets
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_projects.to_excel(writer, sheet_name='Projects', index=False)
            df_financials.to_excel(writer, sheet_name='Financials', index=False)
        
        output.seek(0)
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f'bead_report_{timestamp}.xlsx'
        
        with open(file_name, 'wb') as f:
            f.write(output.getvalue())
        
        conn.close()
        
        return FileResponse(
            path=file_name,
            filename=file_name,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return {"error": str(e)}

@router.get("/insights")
def insights():
    """Get AI-driven insights about BEAD platform performance"""
    return get_insights()

@router.get("/summary")
def get_summary():
    """Get executive summary"""
    try:
        insights_data = get_insights()
        
        return {
            "title": "BEAD Platform Executive Summary",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total_projects": insights_data.get('total_projects', 0),
                "total_locations": insights_data.get('total_locations', 0),
                "total_miles": insights_data.get('total_miles', 0),
                "coverage_percent": insights_data.get('coverage_percent', 0),
                "cost_per_location": insights_data.get('cost_per_location', 0)
            },
            "insights": insights_data.get('insights', [])
        }
    except Exception as e:
        return {"error": str(e)}