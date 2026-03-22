import psycopg2

from .secrets import get_required_secret

def get_conn():
    return psycopg2.connect(get_required_secret("DATABASE_URL"))