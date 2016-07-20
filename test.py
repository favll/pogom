import json
from pogom.models import create_tables, parse_map

with open('/home/wbuffett/test.json', 'r') as f:
    r = json.loads(f.read())

create_tables()
parse_map(r)
