
import os
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from functools import wraps

import click
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


SEED_SEATS = [
    # A Zone
    ("Pratik", "4F-325(1)", 1, 1),
    ("Piyush", "4F-325(2)", 1, 2),
    ("Flexi", "4F-324", 1, 3),
    ("Flexi", "4F-323", 1, 4),
    ("Sourav", "4F-325", 1, 5),
    ("Ritesh", "4F-326", 1, 6),

    # B Zone
    ("Amit", "4F-286", 2, 1),
    ("Milind", "4F-285", 2, 2),
    ("Raman", "4F-284", 2, 3),
    ("Shailesh", "4F-283", 2, 4),
    ("Sumanth", "4F-282", 2, 5),
    ("Ashutosh", "4F-281", 2, 6),
    ("Mahavir", "4F-280", 2, 7),
    ("Vikas", "4F-279", 2, 8),
    ("Aman", "4F-278", 2, 9),

    # C & D Zone - Row 3
    ("Devan", "4F-272", 3, 1),
    ("Shashank", "4F-273", 3, 2),
    ("Ruchira", "4F-274", 3, 3),
    ("Anwar", "4F-275", 3, 4),
    ("Pradeep", "4F-276", 3, 5),
    ("Prashant", "4F-277", 3, 6),

    # C & D Zone - Row 4
    ("Pallav", "4F-271", 4, 1),
    ("Yogendra", "4F-270", 4, 2),
    ("Pradamya", "4F-269", 4, 3),
    ("Nirbhay", "4F-268", 4, 4),
    ("Vishal", "4F-267", 4, 5),
    ("A. Prakash", "4F-266", 4, 6),

    # E Zone
    ("Nishant", "1", 5, 1),
    ("Aditya", "2", 5, 2),
    ("Manoj", "3", 5, 3),
    ("Seat 4", "4", 5, 4),
    ("Seat 5", "5", 5, 5),
]


VALID_STATUSES = {"Available", "WFH", "Leave", "Other"}


class Employee(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    seat_no = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    row = db.Column(db.Integer, nullable=False)

    col = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(50),
        nullable=False,
        default="Available"
    )

    comment = db.Column(
        db.String(500),
        nullable=False,
        default="Available"
    )

    replacement = db.Column(
        db.String(100),
        nullable=False,
        default=""
    )


class AppSettings(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    last_reset_date = db.Column(
        db.String(20),
        nullable=False,
        default=""
    )


class SeatStatusSchedule(db.Model):

    __tablename__ = "seat_status_schedule"

    id = db.Column(db.Integer, primary_key=True)

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employee.id"),
        nullable=False,
        index=True
    )

    start_date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    end_date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    status = db.Column(
        db.String(50),
        nullable=False
    )

    period = db.Column(
        db.String(20),
        nullable=False,
        default="Whole day",
        server_default="Whole day"
    )

    comment = db.Column(
        db.String(500),
        nullable=False,
        default=""
    )

    replacement = db.Column(
        db.String(100),
        nullable=False,
        default=""
    )

    employee = db.relationship(
        "Employee",
        backref=db.backref(
            "status_schedules",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )


def create_app():

    app = Flask(__name__)

    app.config["APP_PASSWORD"] = os.environ.get("APP_PASSWORD")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is not configured.")

    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

    app.config["APP_TIMEZONE"] = os.environ.get(
        "APP_TIMEZONE",
        "Asia/Kolkata"
    )

    database_url = os.environ.get(
        "DATABASE_URL",
        "sqlite:///employee.db"
    )

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )

    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.config["SESSION_COOKIE_SECURE"] = (
        os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    )

    db.init_app(app)

    def get_local_now():

        return datetime.now(
            ZoneInfo(app.config["APP_TIMEZONE"])
        )

    def get_operational_date(now=None):

        if now is None:
            now = get_local_now()

        today = now.date()

        if (now.hour, now.minute) >= (18, 45):
            today += timedelta(days=1)

        return today

    def reset_seats_if_due(now=None):

        if now is None:
            now = get_local_now()

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
                    Employee.replacement: ""
                },
                synchronize_session=False
            )

            settings.last_reset_date = today

            db.session.commit()

    @app.cli.command("init-db")
    def init_db():

        db.create_all()

        existing_seats = {
            seat_no
            for (seat_no,) in db.session.query(
                Employee.seat_no
            ).all()
        }

        added_count = 0

        for name, seat_no, row, col in SEED_SEATS:

            if seat_no not in existing_seats:

                db.session.add(
                    Employee(
                        name=name,
                        seat_no=seat_no,
                        row=row,
                        col=col,
                        status="Available",
                        comment="Available",
                        replacement=""
                    )
                )

                added_count += 1

        if AppSettings.query.first() is None:

            db.session.add(
                AppSettings(last_reset_date="")
            )

        db.session.commit()

        click.echo(
            f"Database initialized. Added {added_count} new seats."
        )

    
    @app.get("/")
    def index():

        reset_seats_if_due()

        now = get_local_now()
        target_date = get_operational_date(now)

        # Select which half should be displayed on the dashboard.
        # Before 2:00 PM: First half.
        # From 2:00 PM until 6:45 PM: Second half.
        # At/after 6:45 PM: First half of the next operational date.
        if (now.hour, now.minute) >= (14, 0) and (now.hour, now.minute) < (18, 45):
            active_period = "Second half"
            period_label = "Second half · 2:00 PM – 6:45 PM"
        else:
            active_period = "First half"
            period_label = "First half · Until 2:00 PM"

        employees = Employee.query.order_by(
            Employee.row,
            Employee.col
        ).all()

        schedules = SeatStatusSchedule.query.filter(
            SeatStatusSchedule.start_date <= target_date,
            SeatStatusSchedule.end_date >= target_date
        ).all()

        # Group schedules by employee.
        schedule_by_employee = {}

        for schedule in schedules:

            schedule_by_employee.setdefault(
                schedule.employee_id,
                []
            ).append(schedule)

        for emp in employees:

            employee_schedules = schedule_by_employee.get(emp.id, [])

            whole_day = next(
                (s for s in employee_schedules if s.period == "Whole day"),
                None
            )

            first_half = next(
                (s for s in employee_schedules if s.period == "First half"),
                None
            )

            second_half = next(
                (s for s in employee_schedules if s.period == "Second half"),
                None
            )

            # A specific half schedule takes priority over a whole-day schedule.
            # If no specific schedule exists, use the whole-day schedule.
            # If neither exists, use the employee's default status.

            first_status_schedule = first_half or whole_day
            second_status_schedule = second_half or whole_day

            emp.view_status_first_half = (
                first_status_schedule.status
                if first_status_schedule
                else emp.status
            )

            emp.view_status_second_half = (
                second_status_schedule.status
                if second_status_schedule
                else emp.status
            )

            emp.view_comment_first_half = (
                first_status_schedule.comment
                if first_status_schedule
                else emp.comment
            )

            emp.view_comment_second_half = (
                second_status_schedule.comment
                if second_status_schedule
                else emp.comment
            )

            emp.view_replacement_first_half = (
                first_status_schedule.replacement
                if first_status_schedule
                else emp.replacement
            )

            emp.view_replacement_second_half = (
                second_status_schedule.replacement
                if second_status_schedule
                else emp.replacement
            )

            # Select the status according to the current time.
            if active_period == "First half":

                emp.view_status = emp.view_status_first_half
                emp.view_comment = emp.view_comment_first_half
                emp.view_replacement = emp.view_replacement_first_half

            else:

                emp.view_status = emp.view_status_second_half
                emp.view_comment = emp.view_comment_second_half
                emp.view_replacement = emp.view_replacement_second_half

        # Count employees using the currently active half only.
        counts = {
            "total": len(employees),

            "available": sum(
                emp.view_status == "Available"
                for emp in employees
            ),

            "wfh": sum(
                emp.view_status == "WFH"
                for emp in employees
            ),

            "leave": sum(
                emp.view_status == "Leave"
                for emp in employees
            ),

            "other": sum(
                emp.view_status == "Other"
                for emp in employees
            )
        }

        display_date = target_date.strftime("%d %b %Y")

        return render_template(
            "index.html",
            employees=employees,
            counts=counts,
            display_date=display_date,
            period_label=period_label
        )

    @app.route(
        "/update/<int:employee_id>",
        methods=["GET", "POST"]
    )
    def update(employee_id):

        emp = db.get_or_404(Employee, employee_id)

        operational_date = get_operational_date()

        if request.method == "POST":

            status = request.form.get("status", "")

            period = request.form.get("period", "Whole day")

            VALID_PERIODS = {
                "Whole day",
                "First half",
                "Second half"
            }

            if period not in VALID_PERIODS:

                flash(
                    "Please select a valid time period.",
                    "error"
                )

                return redirect(
                    url_for("update", employee_id=emp.id)
                )

            if status not in VALID_STATUSES:

                flash(
                    "Please select a valid status.",
                    "error"
                )

                return redirect(
                    url_for("update", employee_id=emp.id)
                )

            try:

                start_date = date.fromisoformat(
                    request.form.get("start_date", "")
                )

                end_date = date.fromisoformat(
                    request.form.get("end_date", "")
                )

            except (ValueError, TypeError):

                flash(
                    "Please select valid start and end dates.",
                    "error"
                )

                return redirect(
                    url_for("update", employee_id=emp.id)
                )

            if start_date < operational_date:

                flash(
                    "You cannot schedule a status for a past date.",
                    "error"
                )

                return redirect(
                    url_for("update", employee_id=emp.id)
                )

            if end_date < start_date:

                flash(
                    "End date cannot be earlier than start date.",
                    "error"
                )

                return redirect(
                    url_for("update", employee_id=emp.id)
                )

            comment = request.form.get(
                "comment", ""
            ).strip()[:500]

            replacement = request.form.get(
                "replacement", ""
            ).strip()[:100]

            # Find schedules that conflict with the new selection.
            #
            # Whole day conflicts with all periods.
            # First half conflicts with Whole day and First half.
            # Second half conflicts with Whole day and Second half.

            if period == "Whole day":

                conflicting_periods = [
                    "Whole day",
                    "First half",
                    "Second half"
                ]

            else:

                conflicting_periods = [
                    "Whole day",
                    period
                ]


            overlapping_schedules = SeatStatusSchedule.query.filter(
                SeatStatusSchedule.employee_id == emp.id,
                SeatStatusSchedule.start_date <= end_date,
                SeatStatusSchedule.end_date >= start_date,
                SeatStatusSchedule.period.in_(conflicting_periods)
            ).all()


            # Preserve existing schedule portions that are not overwritten.
            for old in overlapping_schedules:

                overlap_start = max(old.start_date, start_date)
                overlap_end = min(old.end_date, end_date)

                # Preserve dates before the newly selected range.
                if old.start_date < overlap_start:

                    db.session.add(SeatStatusSchedule(
                        employee_id=emp.id,
                        start_date=old.start_date,
                        end_date=overlap_start - timedelta(days=1),
                        status=old.status,
                        period=old.period,
                        comment=old.comment,
                        replacement=old.replacement
                    ))

                # Preserve dates after the newly selected range.
                if old.end_date > overlap_end:

                    db.session.add(SeatStatusSchedule(
                        employee_id=emp.id,
                        start_date=overlap_end + timedelta(days=1),
                        end_date=old.end_date,
                        status=old.status,
                        period=old.period,
                        comment=old.comment,
                        replacement=old.replacement
                    ))

                # If an existing whole-day schedule is being changed
                # for only one half, preserve its other half.
                if old.period == "Whole day" and period != "Whole day":

                    other_half = (
                        "Second half"
                        if period == "First half"
                        else "First half"
                    )

                    db.session.add(SeatStatusSchedule(
                        employee_id=emp.id,
                        start_date=overlap_start,
                        end_date=overlap_end,
                        status=old.status,
                        period=other_half,
                        comment=old.comment,
                        replacement=old.replacement
                    ))

                db.session.delete(old)


            # Save the new schedule.
            new_schedule = SeatStatusSchedule(
                employee_id=emp.id,
                start_date=start_date,
                end_date=end_date,
                status=status,
                period=period,
                comment=comment,
                replacement=replacement
            )

            db.session.add(new_schedule)

            message = "Status schedule saved successfully."

            db.session.commit()

            flash(
                f"Seat {emp.seat_no}: {message}",
                "success"
            )

            return redirect(url_for("index"))

        upcoming_schedules = SeatStatusSchedule.query.filter(
            SeatStatusSchedule.employee_id == emp.id,
            SeatStatusSchedule.end_date >= operational_date
        ).order_by(
            SeatStatusSchedule.start_date
        ).all()

        active_schedules = SeatStatusSchedule.query.filter(
            SeatStatusSchedule.employee_id == emp.id,
            SeatStatusSchedule.start_date <= operational_date,
            SeatStatusSchedule.end_date >= operational_date
        ).all()

        # Prefer a whole-day schedule when one exists.
        # Otherwise use the first half, then the second half.
        active_schedule = next(
            (s for s in active_schedules if s.period == "Whole day"),
            None
        )

        if active_schedule is None:
            active_schedule = next(
                (s for s in active_schedules if s.period == "First half"),
                None
            )

        if active_schedule is None:
            active_schedule = next(
                (s for s in active_schedules if s.period == "Second half"),
                None
            )

        if active_schedule:

            default_status = active_schedule.status
            default_comment = active_schedule.comment
            default_replacement = active_schedule.replacement
            default_period = active_schedule.period

        else:

            default_status = emp.status
            default_comment = emp.comment
            default_replacement = emp.replacement
            default_period = "Whole day"

        return render_template(
            "update.html",
            emp=emp,
            upcoming_schedules=upcoming_schedules,
            operational_date=operational_date.isoformat(),
            default_status=default_status,
            default_comment=default_comment,
            default_replacement=default_replacement,
            default_period=default_period
        )

    @app.get("/health")
    def health():

        return {"status": "ok"}, 200

    return app


app = create_app()


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=debug_mode
    )

