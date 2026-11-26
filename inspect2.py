import sqlite3
db="/home/mulerun/opt-mulerun/npm-global/lib/node_modules/mule-computer/workspace/ehadir-demo/app/data.db"
c=sqlite3.connect(db); c.row_factory=sqlite3.Row; cur=c.cursor()
for t in ["leave_requests","announcements","class_events","org_settings","activity_log","login_attempts"]:
    row=cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()
    print("---",t,"---"); print(row["sql"] if row else "MISSING"); print()
print("=== admin row ===")
for r in cur.execute("SELECT id,role,username,name,active FROM users WHERE role='admin'"): print(dict(r))
print("=== password hash sample (teacher) ===")
r=cur.execute("SELECT username,password FROM users WHERE role='teacher' LIMIT 1").fetchone()
print(r["username"], r["password"][:20]+"...")
print("=== org_settings ===")
for r in cur.execute("SELECT key,value FROM org_settings"): print(dict(r))
print("=== attendance sample ===")
for r in cur.execute("SELECT * FROM attendance LIMIT 2"): print(dict(r))
print("=== cu_sessions sample ===")
for r in cur.execute("SELECT * FROM cu_sessions LIMIT 2"): print(dict(r))
