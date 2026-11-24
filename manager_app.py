import os
import pyodbc
import hashlib
from functools import wraps
from flask import Flask, session, request, render_template, redirect, url_for

# Define the DSN for the ODBC connection to my PostgreSQL database.

DSN = (
    "DRIVER=PostgreSQL Unicode;"
    "SERVER=localhost;"
    "PORT=5432;"
    "DATABASE=airport;"
    "UID=rorybrown;"
    "PWD=;"
)


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def parse_float(value):
    return float(value) if value.replace('.', '', 1).isdigit() else None


def parse_int(value):
    return int(value) if value.isdigit() else None


def get_employees():
    # 1. Connect to the database using pyodbc and DSN.
    # 2. Retrieve employees with their roles (Manager, Technician, ATC) or blank.
    # 3. Close the connection and return the result.

    employees = []
    try:
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()


        cursor.execute('''
            SELECT 
                e.ssn, e.name, e.address, e.phone, e.salary,
                CASE 
                    WHEN m.ssn IS NOT NULL THEN 'Manager'
                    WHEN t.ssn IS NOT NULL THEN 'Technician'
                    WHEN a.ssn IS NOT NULL THEN 'ATC'
                    ELSE ''
                END AS specialization
            FROM airport.employee e
            LEFT JOIN airport.manager m ON e.ssn = m.ssn
            LEFT JOIN airport.technician t ON e.ssn = t.ssn
            LEFT JOIN airport.atc a ON e.ssn = a.ssn
        ''')

        for row in cursor.fetchall():
            # employees.html reads columns by position: SSN, Name, Address, Phone, Salary, Role
            employees.append((row.ssn, row.name, row.address, row.phone,
                              row.salary, row.specialization))

    except Exception as e:
        print(f"Error in get_employees: {e}")
    finally:
        cnxn.close()
        # Ensure the connection is closed even if an error occurs
    return employees


def get_airplane_models():
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    # models.html reads columns by position (model number, capacity, weight) and
    # airplanes.html uses model[0] for its dropdown, so return full rows, not bare strings.
    cursor.execute('''
        SELECT model_number, capacity, weight
        FROM airport.airplane_model
        ORDER BY model_number
    ''')
    models = [tuple(row) for row in cursor.fetchall()]
    cnxn.close()
    return models


def get_airplanes():
    # 1. Connect to the database
    # 2. Retrieve all airplanes (reg_number, model_number)
    # 3. Close the connection
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    cursor.execute('''
        SELECT reg_number, model_number
        FROM airport.airplane
    ''')
    airplanes = [(r.reg_number, r.model_number) for r in cursor.fetchall()]
    cnxn.close()
    return airplanes


def get_faa_tests():
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    cursor.execute('''
        SELECT test_number, name, max_score
        FROM airport.faa_test
    ''')
    faa_tests = [(r.test_number, r.name, r.max_score) for r in cursor.fetchall()]
    cnxn.close()
    return faa_tests


def get_airworthiness_tests():
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    cursor.execute('''
        SELECT test_number, ssn, reg_number, date, duration, score
        FROM airport.test_event
    ''')
    tests = [(r.test_number, r.ssn, r.reg_number, r.date, r.duration, r.score)
             for r in cursor.fetchall()]
    cnxn.close()
    return tests


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        # 1. Connect to the DB
        # 2. Select manager based on SSN and retrieve the password
        # 3. Close the connection
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()
        cursor.execute('''
            SELECT e.password
            FROM airport.employee e
            JOIN airport.manager m ON e.ssn = m.ssn
            WHERE e.ssn = ?
        ''', (username,))
        user = cursor.fetchone()
        cnxn.close()

        if user and verify_password(password, user[0]):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', message="Authentication error!")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/employee/add', methods=['GET', 'POST'])
@login_required
def employee_add():
    employees = get_employees()

    if request.method == 'POST':
        ssn = request.form['ssn'].strip()
        name = request.form['name'].strip() or None
        password = request.form['password'].strip() or None
        address = request.form['address'].strip() or None
        phone = request.form['phone'].strip() or None
        salary = request.form['salary'].strip()
        specialization = request.form.get('specialization')

        salary = parse_float(salary)
        password_hashed = hash_password(password) if password else None

        # 1. Connect to DB
        # 2. Check if this SSN already exists
        # 3. If not, insert into employee and handle specialization
        # 4. Close connection

        # … parse form …
        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        # 1. Check for existing SSN
        cur.execute("SELECT 1 FROM airport.employee WHERE ssn=?", (ssn,))
        if not cur.fetchone():
            # 2. Insert new employee
            cur.execute('''
                INSERT INTO airport.employee
                  (ssn,name,password,address,phone,salary)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ssn, name, password_hashed, address, phone, salary))
            # 3. Assign specialization
            if specialization == 'Manager':
                cur.execute("INSERT INTO airport.manager(ssn) VALUES(?)", (ssn,))
            elif specialization == 'Technician':
                cur.execute("INSERT INTO airport.technician(ssn) VALUES(?)", (ssn,))
            elif specialization == 'ATC':
                cur.execute("INSERT INTO airport.atc(ssn) VALUES(?)", (ssn,))
            cnxn.commit()
        cnxn.close()
        return redirect(url_for('employee_add'))

    return render_template('employees.html', employees=employees, action='Add')


@app.route('/employee/update', methods=['GET', 'POST'])
@login_required
def employee_update():
    employees = get_employees()

    if request.method == 'POST':
        ssn = request.form['ssn'].strip()
        name = request.form['name'].strip() or None
        password = request.form['password'].strip() or None
        address = request.form['address'].strip() or None
        phone = request.form['phone'].strip() or None
        salary = parse_float(request.form['salary'].strip())
        specialization = request.form.get('specialization')
        password_hashed = hash_password(password) if password else None

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        cur.execute("SELECT 1 FROM airport.employee WHERE ssn=?", (ssn,))
        if cur.fetchone():
            # Update only non-empty fields
            fields, params = [], []
            if name:
                fields.append("name=?");    params.append(name)
            if password_hashed:
                fields.append("password=?"); params.append(password_hashed)
            if address:
                fields.append("address=?"); params.append(address)
            if phone:
                fields.append("phone=?");    params.append(phone)
            if salary is not None:
                fields.append("salary=?");  params.append(salary)
            if fields:
                sql = f"UPDATE airport.employee SET {','.join(fields)} WHERE ssn=?"
                cur.execute(sql, (*params, ssn))
            # Reset specialization
            cur.execute("DELETE FROM airport.manager WHERE ssn=?", (ssn,))
            cur.execute("DELETE FROM airport.technician WHERE ssn=?", (ssn,))
            cur.execute("DELETE FROM airport.atc WHERE ssn=?", (ssn,))
            if specialization == 'Manager':
                cur.execute("INSERT INTO airport.manager(ssn) VALUES(?)", (ssn,))
            elif specialization == 'Technician':
                cur.execute("INSERT INTO airport.technician(ssn) VALUES(?)", (ssn,))
            elif specialization == 'ATC':
                cur.execute("INSERT INTO airport.atc(ssn) VALUES(?)", (ssn,))
            cnxn.commit()
        cnxn.close()

        return redirect(url_for('employee_update'))

    return render_template('employees.html', employees=employees, action='Update')


@app.route('/employee/delete', methods=['GET', 'POST'])
@login_required
def employee_delete():
    employees = get_employees()

    if request.method == 'POST':
        ssn = request.form['ssn'].strip()

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        # Delete specializations first
        cur.execute("DELETE FROM airport.manager WHERE ssn=?", (ssn,))
        cur.execute("DELETE FROM airport.technician WHERE ssn=?", (ssn,))
        cur.execute("DELETE FROM airport.atc WHERE ssn=?", (ssn,))
        # Then delete employee
        cur.execute("DELETE FROM airport.employee WHERE ssn=?", (ssn,))
        cnxn.commit()
        cnxn.close()

        return redirect(url_for('employee_delete'))

    return render_template('employees.html', employees=employees, action='Delete')


@app.route('/expertise', methods=['GET', 'POST'])
@login_required
def expertise():
    cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
    if request.method == 'POST':
        ssn = request.form['ssn'].strip()
        model_number = request.form['model_number'].strip()
        action = request.form['action']
        if action == "add":
            cur.execute("INSERT INTO airport.expert(ssn,model_number) VALUES(?,?)",
                        (ssn, model_number))
        else:
            cur.execute("DELETE FROM airport.expert WHERE ssn=? AND model_number=?",
                        (ssn, model_number))
        cnxn.commit()
    # Fetch technicians + existing expertise
    cur.execute('''
      SELECT t.ssn, e.name,
        (SELECT string_agg(x.model_number, ',')
         FROM airport.expert x WHERE x.ssn=t.ssn)
      FROM airport.technician t
      JOIN airport.employee e ON e.ssn=t.ssn
    ''')
    technicians = cur.fetchall()
    # Fetch models for dropdown
    cur.execute("SELECT model_number, capacity, weight FROM airport.airplane_model")
    models = cur.fetchall()
    cnxn.close()
    # Format for template
    formatted_technicians = [
        (t[0], t[1], t[2] or '') for t in technicians
    ]

    return render_template('expertise.html',
                           technicians=formatted_technicians,
                           models=models)


@app.route('/update_salaries', methods=['GET', 'POST'])
@login_required
def update_salaries():
    if request.method == 'POST':
        percentage = parse_float(request.form['percentage'].strip())
        if percentage is not None:
            percentage = round(percentage, 2) / 100
            cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
            # CAST: the ODBC driver sends the float as text, and PostgreSQL otherwise
            # infers "integer" from "1 + ?" and rejects values like 0.1.
            cur.execute("UPDATE airport.employee SET salary = salary * (1 + CAST(? AS NUMERIC))",
                        (percentage,))
            cnxn.commit()
            cnxn.close()
        return redirect(url_for('index'))

    return render_template('salary.html')


@app.route('/models/add', methods=['GET', 'POST'])
@login_required
def model_add():
    if request.method == 'POST':
        model_number = request.form['model_number'].strip()
        capacity = parse_int(request.form['capacity'].strip())
        weight = parse_float(request.form['weight'].strip())

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        cur.execute(
            "INSERT INTO airport.airplane_model(model_number,capacity,weight) VALUES(?,?,?)",
            (model_number, capacity, weight)
        )
        cnxn.commit()
        cnxn.close()

    return render_template('models.html',
                           models=get_airplane_models(),
                           action="Add")


@app.route('/models/update', methods=['GET', 'POST'])
@login_required
def model_update():
    if request.method == 'POST':
        model_number = request.form['model_number'].strip()
        capacity = request.form['capacity'].strip() or None
        weight = request.form['weight'].strip() or None
        capacity = parse_int(capacity) if capacity else None
        weight = parse_float(weight) if weight else None

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        if capacity is not None:
            cur.execute("UPDATE airport.airplane_model SET capacity=? WHERE model_number=?",
                        (capacity, model_number))
        if weight is not None:
            cur.execute("UPDATE airport.airplane_model SET weight=? WHERE model_number=?",
                        (weight, model_number))
        cnxn.commit()
        cnxn.close()

    return render_template('models.html',
                           models=get_airplane_models(),
                           action="Update")

@app.route('/models/delete', methods=['GET', 'POST'])
@login_required
def model_delete():
    if request.method == 'POST':
        model_number = request.form['model_number'].strip()

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        cur.execute("DELETE FROM airport.airplane_model WHERE model_number=?",
                    (model_number,))
        cnxn.commit()
        cnxn.close()

    return render_template('models.html',
                           models=get_airplane_models(),
                           action="Delete")


@app.route('/airplanes/add', methods=['GET', 'POST'])
@login_required
def airplane_add():
    if request.method == 'POST':
        reg_number = request.form['reg_number'].strip()
        model_number = request.form['model_number'].strip()
        cnxn = pyodbc.connect(DSN)
        cur = cnxn.cursor()
        # Check if reg_number already exists
        cur.execute("SELECT 1 FROM airport.airplane WHERE reg_number=?", (reg_number,))
        if not cur.fetchone():
            cur.execute("INSERT INTO airport.airplane(reg_number,model_number) VALUES(?,?)",
                        (reg_number, model_number))
            cnxn.commit()
        else:
            print(f"Registration number {reg_number} already exists. Skipping insert.")
        cnxn.close()

    return render_template('airplanes.html',
                           airplanes=get_airplanes(),
                           models=get_airplane_models(),
                           action="Add")


@app.route('/airplanes/update', methods=['GET', 'POST'])
@login_required
def airplane_update():
    if request.method == 'POST':
        reg_number = request.form['reg_number'].strip()
        model_number = request.form['model_number'].strip()

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        cur.execute("UPDATE airport.airplane SET model_number=? WHERE reg_number=?",
                    (model_number, reg_number))
        cnxn.commit()
        cnxn.close()

    return render_template('airplanes.html',
                           airplanes=get_airplanes(),
                           models=get_airplane_models(),
                           action="Update")


@app.route('/airplanes/delete', methods=['GET', 'POST'])
@login_required
def airplane_delete():
    if request.method == 'POST':
        reg_number = request.form['reg_number'].strip()

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        cur.execute("DELETE FROM airport.airplane WHERE reg_number=?",
                    (reg_number,))
        cnxn.commit()
        cnxn.close()

    return render_template('airplanes.html',
                           airplanes=get_airplanes(),
                           action="Delete")


@app.route('/faa_tests/add', methods=['GET', 'POST'])
@login_required
def faa_test_add():
    if request.method == 'POST':
        test_number = request.form['test_number'].strip()
        name = request.form['name'].strip()
        max_score = parse_float(request.form['max_score'].strip())

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        cur.execute("INSERT INTO airport.faa_test(test_number,name,max_score) VALUES(?,?,?)",
                    (test_number, name, max_score))
        cnxn.commit()
        cnxn.close()

    return render_template('faa_tests.html',
                           faa_tests=get_faa_tests(),
                           action="Add")


@app.route('/faa_tests/update', methods=['GET', 'POST'])
@login_required
def faa_test_update():
    if request.method == 'POST':
        test_number = request.form['test_number'].strip()
        name = request.form['name'].strip() or None
        max_score = request.form['max_score'].strip() or None
        max_score = parse_float(max_score) if max_score else None

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        if name:
            cur.execute("UPDATE airport.faa_test SET name=? WHERE test_number=?",
                        (name, test_number))
        if max_score is not None:
            cur.execute("UPDATE airport.faa_test SET max_score=? WHERE test_number=?",
                        (max_score, test_number))
        cnxn.commit()
        cnxn.close()

    return render_template('faa_tests.html',
                           faa_tests=get_faa_tests(),
                           action="Update")


@app.route('/faa_tests/delete', methods=['GET', 'POST'])
@login_required
def faa_test_delete():
    if request.method == 'POST':
        test_number = request.form['test_number'].strip()

        cnxn = pyodbc.connect(DSN); cur = cnxn.cursor()
        cur.execute("DELETE FROM airport.faa_test WHERE test_number=?",
                    (test_number,))
        cnxn.commit()
        cnxn.close()

    return render_template('faa_tests.html',
                           faa_tests=get_faa_tests(),
                           action="Delete")

@app.route('/tests')
@login_required
def tests():
    return render_template('tests.html', tests=get_airworthiness_tests())


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=2000)

'''
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

'''