#!/usr/bin/env python3
"""Private local tracker for TZ-277; NEVER sends messages or assumes a reply."""
import argparse,csv
from datetime import date,timedelta
from pathlib import Path

def due(received,holidays=()):
 day=date.fromisoformat(received);holidays=set(holidays)
 for _ in range(2):
  day+=timedelta(days=1)
  while day.weekday()>=5 or day in holidays:day+=timedelta(days=1)
 return day
def inspect(log,holidays,asof):
 out=[]
 with Path(log).open(encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f,delimiter=';'):
   received=row['received_date'].strip()
   answered=row['response_date'].strip()
   deadline=due(received,holidays) if received else None
   if answered and (not received or answered < received):raise ValueError('Response must follow confirmed receipt')
   status='NOT_SENT' if not received else ('ANSWERED_ON_TIME' if answered<=str(deadline) else 'ANSWERED_LATE') if answered else 'OVERDUE' if deadline<asof else 'WAITING'
   out.append((row['rfi_id'],status,str(deadline or ''),answered))
 return out
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('log',type=Path)
 ap.add_argument('--holidays',type=Path,required=True)
 ap.add_argument('--asof',type=date.fromisoformat,default=date.today())
 args=ap.parse_args()
 holidays=set(date.fromisoformat(x.strip()) for x in args.holidays.read_text().splitlines() if x.strip())
 for row in inspect(args.log,holidays,args.asof):print(';'.join(row))
if __name__=='__main__':main()
