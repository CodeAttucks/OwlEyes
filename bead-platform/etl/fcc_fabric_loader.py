import csv
import sys
from pathlib import Path

# Add parent directory to path so we can import api module
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.db import get_conn

def load_fabric(file_path):
    conn = get_conn()
    cur = conn.cursor()

    with open(file_path) as f:
        reader = csv.DictReader(f)

        for row in reader:
            cur.execute("""
                INSERT INTO service_locations (geom, address, served)
                VALUES (
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    %s,
                    %s
                )
            """, (
                float(row['longitude']),
                float(row['latitude']),
                row.get('address', ''),
                row.get('served', 'false') == 'true'
            ))

    conn.commit()


def load_bdc(file_path):
    conn = get_conn()
    cur = conn.cursor()

    with open(file_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cur.execute("""
                INSERT INTO coverage_areas (geom, provider_id, technology, max_down_speed, max_up_speed)
                VALUES (
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    %s, %s, %s, %s
                )
                ON CONFLICT DO NOTHING
            """, (
                float(row['longitude']),
                float(row['latitude']),
                row.get('provider_id', ''),
                row.get('technology', ''),
                float(row.get('max_down_speed', 0)),
                float(row.get('max_up_speed', 0)),
            ))

    conn.commit()
