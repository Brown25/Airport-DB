--Deliverable: Submit an SQL script (create_database.sql) 
--containing all the SQL commands to define the database and
-- at least one stored procedure to implement a business rule. 
 
 --The script should not populate the database with data.

-- Drop tables if they exist to avoid conflicts when re-running the script
DROP TABLE IF EXISTS test_event, faa_test, expert, airplane, airplane_model, atc, technician, manager, employee CASCADE;

-- Drop the functions too, so the script can be re-run even if their signatures changed.
DROP FUNCTION IF EXISTS raise_salary(CHAR, NUMERIC);
DROP FUNCTION IF EXISTS add_new_airplane(TEXT, TEXT);
DROP FUNCTION IF EXISTS record_test_event(INTEGER, CHAR, TEXT, DATE, INTERVAL, INTEGER);

-- Employee Table
CREATE TABLE employee (
    ssn CHAR(9) PRIMARY KEY,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    address TEXT,
    phone TEXT,
    salary NUMERIC(100, 2) CHECK (salary >= 0)
);

-- Manager Table
CREATE TABLE manager (
    ssn CHAR(9) PRIMARY KEY,
    FOREIGN KEY (ssn) REFERENCES employee(ssn) ON DELETE CASCADE
);

-- Technician Table
CREATE TABLE technician (
    ssn CHAR(9) PRIMARY KEY,
    FOREIGN KEY (ssn) REFERENCES employee(ssn) ON DELETE CASCADE
);

-- ATC Table (Air Traffic Controller)
CREATE TABLE atc (
    ssn CHAR(9) PRIMARY KEY,
    FOREIGN KEY (ssn) REFERENCES employee(ssn) ON DELETE CASCADE
);

-- Airplane Model Table
CREATE TABLE airplane_model (
    model_number TEXT PRIMARY KEY,
    capacity INTEGER NOT NULL CHECK (capacity >= 0),
    weight INTEGER NOT NULL CHECK (weight >= 0)
);

-- Airplane Table
CREATE TABLE airplane (
    reg_number TEXT PRIMARY KEY,
    model_number TEXT NOT NULL,
    FOREIGN KEY (model_number) REFERENCES airplane_model(model_number) ON DELETE CASCADE
);

-- Expert Table (multi-column PK)
CREATE TABLE expert (
    ssn CHAR(9) NOT NULL,
    model_number TEXT NOT NULL,
    PRIMARY KEY (ssn, model_number),
    FOREIGN KEY (ssn) REFERENCES employee(ssn) ON DELETE CASCADE,
    FOREIGN KEY (model_number) REFERENCES airplane_model(model_number) ON DELETE CASCADE
);

-- FAA Test Table
CREATE TABLE faa_test (
    test_number INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    max_score INTEGER NOT NULL CHECK (max_score > 0)
);

-- Test Event Table (multi-column PK)
CREATE TABLE test_event (
    test_number INTEGER NOT NULL,
    ssn CHAR(9) NOT NULL,
    reg_number TEXT NOT NULL,
    date DATE NOT NULL,
    duration INTERVAL,
    score INTEGER NOT NULL CHECK (score >= 0),
    PRIMARY KEY (test_number, ssn, reg_number, date),
    FOREIGN KEY (test_number) REFERENCES faa_test(test_number) ON DELETE CASCADE,
    FOREIGN KEY (ssn) REFERENCES employee(ssn) ON DELETE CASCADE,
    FOREIGN KEY (reg_number) REFERENCES airplane(reg_number) ON DELETE CASCADE
);

-- Indexes for better search performance
CREATE INDEX idx_employee_name ON employee(name);
CREATE INDEX idx_employee_salary ON employee(salary);
CREATE INDEX idx_airplane_model_number ON airplane(model_number);
CREATE INDEX idx_test_event_score ON test_event(score);
CREATE INDEX idx_test_event_date ON test_event(date);







-- ===================================
-- Stored Procedure 1: Raise Employee Salary
-- ===================================
-- Business rule: a raise must be a positive amount and the employee must exist.
-- (Parameters are prefixed with p_ so they can never clash with column names.)
CREATE OR REPLACE FUNCTION raise_salary(p_ssn CHAR(9), p_amount NUMERIC)
RETURNS VOID AS $$
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Salary raise amount must be positive.';
    END IF;

    UPDATE employee
    SET salary = salary + p_amount
    WHERE ssn = p_ssn;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Employee % does not exist.', p_ssn;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ===================================
-- Stored Procedure 2: Add a New Airplane
-- ===================================
-- Business rule: an airplane must belong to an existing model and have a unique registration.
-- (Fix: the old parameters were named reg_number / model_number, the same as the
--  table columns, so "WHERE model_number = model_number" was ambiguous and every call failed.)
CREATE OR REPLACE FUNCTION add_new_airplane(p_reg_number TEXT, p_model_number TEXT)
RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM airplane_model m WHERE m.model_number = p_model_number) THEN
        RAISE EXCEPTION 'Model number % does not exist.', p_model_number;
    END IF;

    IF EXISTS (SELECT 1 FROM airplane a WHERE a.reg_number = p_reg_number) THEN
        RAISE EXCEPTION 'Airplane % is already registered.', p_reg_number;
    END IF;

    INSERT INTO airplane (reg_number, model_number)
    VALUES (p_reg_number, p_model_number);
END;
$$ LANGUAGE plpgsql;

-- ===================================
-- Stored Procedure 3: Record a New Test Event
-- ===================================
-- Business rules: only a technician can record a test, the test and airplane must
-- exist, and the score must be between 0 and the test's max_score.
CREATE OR REPLACE FUNCTION record_test_event(p_test_number INTEGER, p_technician_ssn CHAR(9), p_reg_number TEXT, p_date DATE, p_duration INTERVAL, p_score INTEGER)
RETURNS VOID AS $$
DECLARE
    v_max_score INTEGER;
BEGIN
    SELECT t.max_score INTO v_max_score FROM faa_test t WHERE t.test_number = p_test_number;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'FAA test % does not exist.', p_test_number;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM technician t WHERE t.ssn = p_technician_ssn) THEN
        RAISE EXCEPTION 'Employee % is not a technician.', p_technician_ssn;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM airplane a WHERE a.reg_number = p_reg_number) THEN
        RAISE EXCEPTION 'Airplane % does not exist.', p_reg_number;
    END IF;

    IF p_score IS NULL OR p_score < 0 OR p_score > v_max_score THEN
        RAISE EXCEPTION 'Test score must be between 0 and % for this test.', v_max_score;
    END IF;

    INSERT INTO test_event (test_number, ssn, reg_number, date, duration, score)
    VALUES (p_test_number, p_technician_ssn, p_reg_number, p_date, p_duration, p_score);
END;
$$ LANGUAGE plpgsql;