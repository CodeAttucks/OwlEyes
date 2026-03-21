from fastapi import APIRouter, HTTPException
from ..db import get_conn
from typing import Optional

router = APIRouter(prefix="/fiber")

@router.get("/")
def list_fiber_routes():
    """Get all fiber routes"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, project_id, ST_AsGeoJSON(geom) as geometry, miles 
            FROM fiber_routes
        """)
        routes = [
            {
                "id": row[0],
                "project_id": row[1],
                "geometry": row[2],
                "miles": row[3]
            }
            for row in cur.fetchall()
        ]
        conn.close()
        return {"routes": routes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_id}")
def get_fiber_by_project(project_id: str):
    """Get fiber routes for a specific project"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, project_id, ST_AsGeoJSON(geom) as geometry, miles 
            FROM fiber_routes 
            WHERE project_id = %s
        """, (project_id,))
        routes = [
            {
                "id": row[0],
                "project_id": row[1],
                "geometry": row[2],
                "miles": row[3]
            }
            for row in cur.fetchall()
        ]
        conn.close()
        return {"routes": routes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
def create_fiber_route(route_data: dict):
    """Create a new fiber route"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO fiber_routes (project_id, geom, miles)
            VALUES (%s, ST_GeomFromGeoJSON(%s), %s)
            RETURNING id
        """, (
            route_data.get('project_id'),
            route_data.get('geometry'),
            route_data.get('miles')
        ))
        fiber_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        return {"id": fiber_id, "status": "created"}
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/summary")
def get_fiber_stats():
    """Get summary statistics for fiber routes"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as total_routes,
                COALESCE(SUM(miles), 0) as total_miles,
                COALESCE(AVG(miles), 0) as avg_miles
            FROM fiber_routes
        """)
        stats = cur.fetchone()
        conn.close()
        return {
            "total_routes": stats[0],
            "total_miles": stats[1],
            "average_miles": stats[2]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))