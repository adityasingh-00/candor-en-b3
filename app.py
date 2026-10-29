
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import click
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

STATUS_CHOICES = ["Available", "WFH", "Leave"]

SEED_SEATS = [
    ("Pratik", "4F-325(1)", 1, 1), ("Piyush", "4F-325(2)", 1, 2),
    ("Flexi", "4F-324", 1, 3), ("Flexi", "4F-323", 1, 4),
    ("Sourav", "4F-325", 1, 5), ("Ritesh", "4F-326", 1, 6),
    ("Amit", "4F-286", 2, 1), ("Milind", "4F-285", 2, 2),
    ("Raman", "4F-284", 2, 3), ("Shailesh", "4F-283", 2, 4),
    ("Sumanth", "4F-282", 2, 5), ("Ashutosh", "4F-281", 2, 6),
    ("Mahavir", "4F-280", 2, 7), ("Vikas", "4F-279", 2, 8),
    ("Aman", "4F-278", 2, 9),
    ("Devan", "4F-272", 3, 1), ("Shashank", "4F-273", 3, 2),
    ("Ruchira", "4F-274", 3, 3), ("Anwar", "4F-275", 3, 4),
    ("Pradeep", "4F-276", 3, 5), ("Prashant", "4F-277", 3, 6),
    ("Pallav", "4F-271", 4, 1), ("Yogendra", "4F-270", 4, 2),
    ("Pradamya", "4F-269", 4, 3), ("Nirbhay", "4F-268", 4, 4),
    ("Vishal", "4F-267", 4, 5), ("A. Prakash", "4F-266", 4, 6),
]


def create_app():
    app = Flask(__name__)

    app.config["APP_TIMEZONE"] = os.environ.get(
        "APP_TIMEZONE", "Asia/Kolkata"
    )
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "local-only-change-this-secret"
    )

    database_url = os.environ.get("DATABASE_URL", "sqlite:///employee.db")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql+psycopg://", 1
        )
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    )

    db.init_app(app)

    @app.cli.command("init-db")
    def init_db():
        """Create tables and seed the initial seating plan."""
        db.create_all()

        if Employee.query.count() == 0:
            for name, seat_no, row, col in SEED_SEATS:
                db.session.add(
                    Employee(
                        name=name,
                        seat_no=seat_no,
                        row=row,
                        col=col,
                        status="Available",
                        comment="Available",
                        replacement="",
                    )
                )

        if AppSettings.query.first() is None:
            db.session.add(AppSettings(last_reset_date=""))

        db.session.commit()
        click.echo("Database initialized.")

    def reset_seats_if_due(now=None):
        now = now or datetime.now(ZoneInfo(app.config["APP_TIMEZONE"]))
        settings = AppSettings.query.first()

        if settings is None:
            settings = AppSettings(last_reset_date="")
            db.session.add(settings)
            db.session.flush()

        today = now.strftime("%Y-%m-%d")
        after_cutoff = (now.hour, now.minute) >= (18, 45)

        if after_cutoff and settings.last_reset_date != today:
            Employee.query.update(
                {
                    Employee.status: "Available",
                    Employee.comment: "Available",
                    Employee.replacement: "",
                },
                synchronize_session=False,
            )
            settings.last_reset_date = today
            db.session.commit()

    @app.get("/")
    def index():
        reset_seats_if_due()
        employees = Employee.query.order_by(
            Employee.row, Employee.col
        ).all()

        counts = {
            "total": len(employees),
            "available": sum(e.status == "Available" for e in employees),
            "wfh": sum(e.status == "WFH" for e in employees),
            "leave": sum(e.status == "Leave" for e in employees),
        }

        now = datetime.now(ZoneInfo(app.config["APP_TIMEZONE"]))

        # Before 6:45 PM: show today's date.
        # At or after 6:45 PM: show tomorrow's date.
        display_date = (
            now + timedelta(days=1)
            if (now.hour, now.minute) >= (18, 45)
            else now
        ).strftime("%d %b %Y")

        return render_template(
            "index.html",
            employees=employees,
            counts=counts,
            display_date=display_date,
        )

    @app.route("/update/<int:employee_id>", methods=["GET", "POST"])
    def update(employee_id):
        emp = db.get_or_404(Employee, employee_id)

        if request.method == "POST":
            status = request.form.get("status", "")

            if status not in STATUS_CHOICES:
                flash("Please select a valid seat status.", "error")
                return redirect(
                    url_for("update", employee_id=emp.id)
                )

            emp.status = status
            emp.comment = request.form.get(
                "comment", ""
            ).strip()[:500]
            emp.replacement = request.form.get(
                "replacement", ""
            ).strip()[:100]

            db.session.commit()
            flash(f"Seat {emp.seat_no} updated.", "success")
            return redirect(url_for("index"))

        return render_template(
            "update.html",
            emp=emp,
            status_choices=STATUS_CHOICES,
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    return app


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    seat_no = db.Column(db.String(20), unique=True, nullable=False)
    row = db.Column(db.Integer, nullable=False)
    col = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(50), nullable=False, default="Available"
    )
    comment = db.Column(
        db.String(500), nullable=False, default="Available"
    )
    replacement = db.Column(
        db.String(100), nullable=False, default=""
    )


class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_reset_date = db.Column(
        db.String(20), nullable=False, default=""
    )


app = create_app()

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    )
