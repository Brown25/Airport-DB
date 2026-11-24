# AirportDB – Airport Management System

A database-driven airport management system. One PostgreSQL database is shared by two client applications:

| Module | Stack | Users | Purpose |
|---|---|---|---|
| **Database** | PostgreSQL 14, PL/pgSQL | — | Schema, constraints, and stored procedures for employees, airplanes, and FAA tests |
| **Manager web app** | Python 3.10, Flask, pyodbc (ODBC) | Managers | Manage employees, salaries, technician expertise, airplane models, airplanes, and FAA tests; view recorded tests |
| **Airplane test app** | Java 11+, Swing, JDBC | Technicians | Log in and record airworthiness test events |

More detail:
- [Project overview](docs/PROJECT_OVERVIEW.md): goals, components, and what each part delivers.
- [Architecture](docs/ARCHITECTURE.md): the components, how they connect, and the data model.
- [System design](docs/SYSTEM_DESIGN.md): request flows, design decisions, and known limitations.

---

## Repository layout

```
.
├── README.md                     ← you are here
├── .gitignore
├── create_database.sql           ── DB module: schema + stored procedures
├── manager_app.py                ── Python module: Flask manager web app
├── templates/                       Jinja2 pages used by manager_app.py
│   ├── login.html, index.html
│   ├── employees.html, salary.html, expertise.html
│   ├── models.html, airplanes.html
│   └── faa_tests.html, tests.html
├── password.py                      helper: print a SHA-256 password hash
├── AirplaneTestApp.java          ── Java module: Swing technician app
├── postgresql-42.7.5.jar            PostgreSQL JDBC driver
├── docs/
│   ├── PROJECT_OVERVIEW.md          goals and scope
│   ├── ARCHITECTURE.md              components, module trees, data model
│   ├── SYSTEM_DESIGN.md             flows, decisions, limitations
│   ├── relational_model.png         relational model diagram
│   ├── Design.txt                   design notes
│   └── output.txt                   earlier directory listing
└── .venv/                        Python virtualenv (git-ignored)
```

---

## Prerequisites (macOS / Homebrew)

```bash
brew install postgresql@14 unixodbc psqlodbc
brew services start postgresql@14
```

- Python 3.10 or newer, with `flask` and `pyodbc` installed.
- Java 11 or newer. The app is launched as a single source file, so there's no separate compile step.
- The PostgreSQL ODBC driver must be registered in `/opt/homebrew/etc/odbcinst.ini`:

  ```ini
  [PostgreSQL Unicode]
  Description=PostgreSQL ODBC driver (Unicode)
  Driver=/opt/homebrew/lib/psqlodbcw.so
  ```

  Check it with `odbcinst -q -d`.

---

## Quick start

All commands run from the repository root.

### 1. Create the database

Both apps query `airport.<table>`, so the tables must live in a schema named `airport`.

```bash
createdb airport
psql -d airport -c "CREATE SCHEMA airport"
PGOPTIONS="-c search_path=airport" psql -d airport -f create_database.sql
```

### 2. Seed a manager and a technician

`create_database.sql` deliberately inserts no data. Passwords are stored as SHA-256 hex digests.

```sql
-- psql -d airport
SET search_path = airport;

INSERT INTO employee (ssn, name, password, address, phone, salary) VALUES
  ('111111111', 'Alice Manager', encode(sha256('manager123'::bytea), 'hex'), '1 Main St', '555-0001', 90000),
  ('222222222', 'Tom Tech',      encode(sha256('tech123'::bytea),    'hex'), '2 Oak Ave', '555-0002', 60000);
INSERT INTO manager    (ssn) VALUES ('111111111');
INSERT INTO technician (ssn) VALUES ('222222222');

-- optional sample data so the dropdowns aren't empty
INSERT INTO airplane_model VALUES ('B737', 180, 41000);
INSERT INTO airplane       VALUES ('N12345', 'B737');
INSERT INTO faa_test       VALUES (1, 'Engine Inspection', 100);
```

### 3. Run the manager web app (Python)

```bash
python3.10 -m venv .venv          # first time only
source .venv/bin/activate
pip install flask pyodbc          # first time only
python manager_app.py
```

Open **http://127.0.0.1:2000** and log in as `111111111` / `manager123`.

### 4. Run the airplane test app (Java)

```bash
java -cp .:postgresql-42.7.5.jar AirplaneTestApp.java
```

Log in as `222222222` / `tech123`. Then pick an airplane and an FAA test, enter the duration and score, and submit.

---

## Configuration

Connection settings are constants at the top of each app:

| App | Location | Default |
|---|---|---|
| Python | `DSN` in [manager_app.py](manager_app.py) | `DRIVER=PostgreSQL Unicode;SERVER=localhost;PORT=5432;DATABASE=airport;UID=rorybrown;PWD=` |
| Java | `DB_URL`, `DB_USER`, `DB_PASSWORD` in [AirplaneTestApp.java](AirplaneTestApp.java) | `jdbc:postgresql://localhost:5432/airport?currentSchema=airport`, `rorybrown`, empty password |

To use a remote PostgreSQL server instead, open an SSH tunnel first with `ssh -N -L 5432:localhost:5432 <user>@<db-host>`. Then point both apps at `localhost:5432` with that server's database name and credentials.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `zsh: command not found: python` after activating | The venv was created at another path. Recreate it, or run `.venv/bin/python manager_app.py`. |
| `Data source name not found` | The ODBC driver isn't registered. The `DRIVER=` name must match the `[section]` in `odbcinst.ini`. |
| `relation "airport.employee" does not exist` | The `airport` schema is missing. Rerun step 1. |
| `role "..." does not exist` | The DB user in the app config doesn't exist locally. Change it to your Postgres user. |
| Login says "Authentication error!" or "Invalid credentials" | The SSN/password pair is wrong, or the user isn't in the `manager` table (web app) or the `technician` table (Java app). |
