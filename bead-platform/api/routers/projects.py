from fastapi import APIRouter
from ..db import get_conn

router = APIRouter(prefix="/projects")

@router.get("/")
def list_projects():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, status FROM projects")
    return cur.fetchall()