CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
);

CREATE TABLE bplan (
    id INTEGER PRIMARY KEY,
    title TEXT,
    owner_id INTEGER REFERENCES users,
    budget INTEGER,
    classification TEXT,
    access_code TEXT UNIQUE
);

CREATE TABLE expenses (
    id INTEGER PRIMARY KEY,
    bplan_id INTEGER REFERENCES bplan,
    expense_title TEXT,
    expense_amount INTEGER
);

CREATE TABLE accesses (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users,
    access_code REFERENCES bplan
);
