import sqlite3
from flask import Flask
from flask import request, session, redirect, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import db
import config
import secrets

app = Flask(__name__)
app.secret_key = config.secret_key

LABELS = {"A": "Personal", "B": "Household", "C": "Business", "D": "Other"}
default_classes = list(LABELS)
MAX_EXPENSES = 10
code_len = 6

def parse_expenses(descriptions, amounts):
    if len(descriptions) > MAX_EXPENSES or len(descriptions) != len(amounts):
        return None, "Invalid expenses."

    expenses = []
    for description, amount_text in zip(descriptions, amounts):
        description = description.strip()
        amount_text = amount_text.strip()

        if not description and not amount_text:
            continue  # empty row, skip it

        try:
            amount = int(amount_text)
        except ValueError:
            return None, "Each expense needs a description and a whole-number amount."
        if not description or amount < 0:
            return None, "Each expense needs a description and a non-negative amount."

        expenses.append((description, amount))

    if not expenses:
        return None, "Add at least one expense."
    return expenses, None

def new_code():
    while True:
        code = secrets.token_hex(6)
        rows = db.query("SELECT * FROM bplan WHERE access_code = ?", [code])

        if rows == []:
            return code


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        rows = db.query("SELECT password_hash FROM users WHERE username = ?", [username])
        if rows and check_password_hash(rows[0]["password_hash"], password):
            session["username"] = username
            return redirect("/")
        error = "Wrong username or password"

    username = session.get("username")
    plans = []
    title = ""
    selected = default_classes

    if username:
        title = request.args.get("title", "").strip()

        if "searched" in request.args:
            selected = [c for c in request.args.getlist("classification") if c in default_classes]

        sql = """
            SELECT p.id, p.title, p.classification, p.budget
            FROM bplan p JOIN users u ON u.id = p.owner_id
            WHERE u.username = ?
        """
        params = [username]

        if title:
            sql += " AND p.title LIKE ?"
            params.append("%" + title + "%")

        sql += " AND p.classification IN (" + ",".join("?" * len(selected)) + ")"
        params += selected

        sql += " ORDER BY p.title"
        rows = db.query(sql, params)

        plans = []
        for row in rows:
            expenses = db.query(
                "SELECT expense_title, expense_amount FROM expenses WHERE bplan_id = ?",
                [row["id"]],
            )
            plans.append({
                "title": row["title"],
                "classification": row["classification"],
                "budget": row["budget"],
                "expenses": expenses,
                "total": sum(e["expense_amount"] for e in expenses),
            })

    return render_template("index.html", username=username, error=error, plans=plans, title=title, selected=selected, labels=LABELS)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password1 = request.form["password1"]
        password2 = request.form["password2"]

        if password1 != password2:
            error = "Passwords don't match."

        elif len(password1) < 8:
            error = "Password must be at least 8 characters."

        elif len(password1) > 128:
            error = "Password is too long"

        else:        
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    [username, generate_password_hash(password1)],
                )
                session["username"] = username

                return redirect("/")

            except sqlite3.IntegrityError:
                error = "Username not available."

    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/create", methods=["GET", "POST"])
def create():
    if "username" not in session:
        return redirect("/")

    error = None
    if request.method == "POST":
        title = request.form["title"].strip()
        classification = request.form["classification"]

        try:
            budget = int(request.form["budget"])
        except ValueError:
            budget = None

        expenses, expense_error = parse_expenses(
            request.form.getlist("expense_description"),
            request.form.getlist("expense_amount"),
        )


        if not title:
            error = "Title is required."

        elif budget is None or budget < 0:
            error = "Budget must be a whole number and can't be negative."

        elif classification not in default_classes:
            error = "Choose a classification"

        elif expense_error:
            error = expense_error

        else:
            access_code = new_code()
            owner = db.query("SELECT id FROM users WHERE username = ?", [session["username"]])
            db.execute("INSERT INTO bplan (title, owner_id, budget, classification, access_code) VALUES (?, ?, ?, ?, ?)", [title, owner[0]["id"], budget, classification, access_code],)

            plan_id = db.last_insert_id()
            for description, amount in expenses:
                db.execute(
                    "INSERT INTO expenses (bplan_id, expense_title, expense_amount) VALUES (?, ?, ?)",
                    [plan_id, description, amount],
                )
            return redirect("/")

    return render_template("create.html", error=error, labels=LABELS, max_expenses=MAX_EXPENSES)

