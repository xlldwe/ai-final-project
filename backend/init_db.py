import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import init_db

if __name__ == '__main__':
    init_db()
    print("Database initialized!")