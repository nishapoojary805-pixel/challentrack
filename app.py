
from flask import Flask, render_template, request, redirect, flash, send_file
import sqlite3
import re
from io import BytesIO
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "challantrack_secret_key"

DATABASE = "challenTrack.db"


# DATABASE CONNECTION
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# DATABASE INITIALIZATION AND BASIC MIGRATION
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS offences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offence_name TEXT NOT NULL,
            fine_amount REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS challans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            offence_id INTEGER NOT NULL,
            fine_amount REAL NOT NULL,
            location TEXT,
            payment_status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offence_id) REFERENCES offences(id)
        )
    """)

    # Add created_at if an older database does not have it.
    cursor.execute("PRAGMA table_info(challans)")
    columns = [column["name"] for column in cursor.fetchall()]

    if "created_at" not in columns:
        cursor.execute("""
            ALTER TABLE challans
            ADD COLUMN created_at TEXT
        """)

        cursor.execute("""
            UPDATE challans
            SET created_at = CURRENT_TIMESTAMP
            WHERE created_at IS NULL
        """)

    conn.commit()
    conn.close()


init_db()


# DASHBOARD
@app.route("/")
@app.route("/dashboard")
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM challans")
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM challans
        WHERE payment_status='Paid'
    """)
    paid = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM challans
        WHERE payment_status='Pending'
    """)
    pending = cursor.fetchone()[0]

    cursor.execute("""
        SELECT SUM(fine_amount) FROM challans
        WHERE payment_status='Paid'
    """)
    collection = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(fine_amount) FROM challans")
    total_fine = cursor.fetchone()[0] or 0

    conn.close()

    return render_template(
        "dashboard.html",
        total=total,
        paid=paid,
        pending=pending,
        collection=collection,
        total_fine=total_fine
    )


# OFFENCE MANAGEMENT
@app.route("/offences", methods=["GET", "POST"])
def offences():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        offence_name = request.form.get(
            "offence_name", ""
        ).strip()

        try:
            fine_amount = float(
                request.form.get("fine_amount", 0)
            )
        except (ValueError, TypeError):
            fine_amount = 0

        if not offence_name or fine_amount <= 0:
            flash("Enter valid offence details!", "error")
        else:
            cursor.execute("""
                INSERT INTO offences (offence_name, fine_amount)
                VALUES (?, ?)
            """, (offence_name, fine_amount))

            conn.commit()
            flash("Offence added successfully!", "success")

        conn.close()
        return redirect("/offences")

    cursor.execute("SELECT * FROM offences ORDER BY id ASC")
    offence_list = cursor.fetchall()

    conn.close()

    return render_template(
        "offences.html",
        offences=offence_list
    )


# ISSUE CHALLAN AND REPEAT OFFENDER DETECTION
@app.route("/issue_challan", methods=["GET", "POST"])
def issue_challan():

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        vehicle_number = request.form.get(
            "vehicle_number", ""
        ).upper().replace(" ", "").strip()

        owner_name = request.form.get(
            "owner_name", ""
        ).strip()

        offence_id = request.form.get(
            "offence_id", ""
        ).strip()

        location = request.form.get(
            "location", ""
        ).strip()

        # Indian vehicle number validation
        pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"

        if not re.fullmatch(pattern, vehicle_number):
            conn.close()
            flash("Invalid vehicle number format!", "error")
            return redirect("/issue_challan")

        if not owner_name or not location:
            conn.close()
            flash("Please fill all required fields!", "error")
            return redirect("/issue_challan")

        try:
            offence_id = int(offence_id)

            cursor.execute("""
                SELECT fine_amount
                FROM offences
                WHERE id=?
            """, (offence_id,))

            offence = cursor.fetchone()

        except (ValueError, TypeError):
            offence = None

        if offence is None:
            conn.close()
            flash("Please select a valid offence!", "error")
            return redirect("/issue_challan")

        original_fine = float(offence["fine_amount"])

        # Count previous same offences by the same vehicle
        cursor.execute("""
            SELECT COUNT(*)
            FROM challans
            WHERE vehicle_number=?
            AND offence_id=?
        """, (vehicle_number, offence_id))

        previous_count = cursor.fetchone()[0]

        # Increase fine by 50% for each previous same offence
        fine_amount = original_fine * (
            1 + 0.5 * previous_count
        )

        cursor.execute("""
            INSERT INTO challans (
                vehicle_number,
                owner_name,
                offence_id,
                fine_amount,
                location,
                payment_status
            )
            VALUES (?, ?, ?, ?, ?, 'Pending')
        """, (
            vehicle_number,
            owner_name,
            offence_id,
            fine_amount,
            location
        ))

        conn.commit()
        conn.close()

        if previous_count > 0:
            flash(
                f"REPEAT OFFENDER! Previous offences: "
                f"{previous_count}. Original Fine: "
                f"Rs. {original_fine:.2f}. Increased Fine: "
                f"Rs. {fine_amount:.2f}",
                "warning"
            )
        else:
            flash(
                f"Challan issued successfully! Fine: "
                f"Rs. {fine_amount:.2f}",
                "success"
            )

        return redirect("/view_challans")

    cursor.execute("SELECT * FROM offences ORDER BY id ASC")
    offence_list = cursor.fetchall()

    conn.close()

    return render_template(
        "issue_challan.html",
        offences=offence_list
    )


# VIEW ALL CHALLANS
@app.route("/view_challans")
def view_challans():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.vehicle_number,
            c.owner_name,
            o.offence_name,
            c.fine_amount,
            c.location,
            c.payment_status
        FROM challans c
        LEFT JOIN offences o
        ON c.offence_id = o.id
        ORDER BY c.id DESC
    """)

    challans = cursor.fetchall()

    conn.close()

    return render_template(
        "view_challans.html",
        challans=challans
    )


# PAYMENT PAGE
@app.route("/payment")
def payment():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            vehicle_number,
            owner_name,
            fine_amount,
            payment_status
        FROM challans
        ORDER BY id DESC
    """)

    challans = cursor.fetchall()

    conn.close()

    return render_template(
        "payment.html",
        challans=challans
    )


# RECORD PAYMENT
@app.route("/pay/<int:challan_id>", methods=["POST"])
def pay(challan_id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE challans
        SET payment_status='Paid'
        WHERE id=?
        AND payment_status='Pending'
    """, (challan_id,))

    updated = cursor.rowcount

    conn.commit()
    conn.close()

    if updated:
        flash("Payment recorded successfully!", "success")
    else:
        flash("Challan not found or already paid!", "error")

    return redirect("/payment")


# VEHICLE SEARCH
@app.route("/vehicle_search", methods=["GET", "POST"])
def vehicle_search():

    challans = []
    total_fine = 0
    paid_amount = 0
    pending_amount = 0
    searched = False
    vehicle_number = ""

    if request.method == "POST":

        vehicle_number = request.form.get(
            "vehicle_number", ""
        ).upper().replace(" ", "").strip()

        searched = True

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.id,
                c.vehicle_number,
                o.offence_name,
                c.fine_amount,
                c.location,
                c.payment_status
            FROM challans c
            LEFT JOIN offences o
            ON c.offence_id=o.id
            WHERE c.vehicle_number=?
            ORDER BY c.id DESC
        """, (vehicle_number,))

        challans = cursor.fetchall()

        for row in challans:

            total_fine += row["fine_amount"]

            if row["payment_status"] == "Paid":
                paid_amount += row["fine_amount"]
            else:
                pending_amount += row["fine_amount"]

        conn.close()

    return render_template(
        "vehicle_search.html",
        challans=challans,
        total_fine=total_fine,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        searched=searched,
        vehicle_number=vehicle_number
    )


# PENDING CHALLAN ALERT
@app.route("/pending_challans", methods=["GET", "POST"])
def pending_challans():

    challans = []
    total_due = 0
    searched = False
    vehicle_number = ""

    if request.method == "POST":

        vehicle_number = request.form.get(
            "vehicle_number", ""
        ).upper().replace(" ", "").strip()

        searched = True

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM challans
            WHERE vehicle_number=?
            AND payment_status='Pending'
            ORDER BY id DESC
        """, (vehicle_number,))

        challans = cursor.fetchall()

        total_due = sum(
            row["fine_amount"] for row in challans
        )

        conn.close()

    multiple_pending = len(challans) > 1

    return render_template(
        "pending_challans.html",
        challans=challans,
        total_due=total_due,
        searched=searched,
        vehicle_number=vehicle_number,
        multiple_pending=multiple_pending
    )


# PDF CHALLAN RECEIPT
@app.route("/challan_receipt/<int:challan_id>")
def challan_receipt(challan_id):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.vehicle_number,
            c.owner_name,
            o.offence_name,
            c.fine_amount,
            c.location,
            c.payment_status,
            c.created_at
        FROM challans c
        LEFT JOIN offences o
        ON c.offence_id=o.id
        WHERE c.id=?
    """, (challan_id,))

    challan = cursor.fetchone()

    conn.close()

    if challan is None:
        return "Challan not found", 404

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.setTitle("Challan Receipt")

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(170, 800, "CHALLANTRACK")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(180, 760, "Traffic Challan Receipt")

    pdf.line(50, 740, 550, 740)

    pdf.setFont("Helvetica", 12)

    details = [
        f"Challan ID: {challan['id']}",
        f"Vehicle Number: {challan['vehicle_number']}",
        f"Owner Name: {challan['owner_name']}",
        f"Offence: {challan['offence_name'] or 'Unknown'}",
        f"Fine Amount: Rs. {challan['fine_amount']:.2f}",
        f"Location: {challan['location'] or 'Not available'}",
        f"Payment Status: {challan['payment_status']}",
        f"Date: {challan['created_at'] or 'Not available'}"
    ]

    y = 700

    for detail in details:
        pdf.drawString(70, y, detail)
        y -= 35

    pdf.line(50, y - 10, 550, y - 10)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(70, y - 40, "Thank you.")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Challan_{challan_id}.pdf",
        mimetype="application/pdf"
    )


# AREA-WISE REPORT
@app.route("/area_report")
def area_report():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            location,
            COUNT(*) AS total_challans,
            SUM(
                CASE
                    WHEN payment_status='Paid'
                    THEN fine_amount
                    ELSE 0
                END
            ) AS paid_amount,
            SUM(
                CASE
                    WHEN payment_status='Pending'
                    THEN 1
                    ELSE 0
                END
            ) AS pending_count
        FROM challans
        GROUP BY location
        ORDER BY total_challans DESC
    """)

    rows = cursor.fetchall()
    reports = []

    for row in rows:

        cursor.execute("""
            SELECT
                o.offence_name,
                COUNT(*) AS total
            FROM challans c
            JOIN offences o
            ON c.offence_id=o.id
            WHERE c.location=?
            GROUP BY o.offence_name
            ORDER BY total DESC
            LIMIT 1
        """, (row["location"],))

        common = cursor.fetchone()

        reports.append({
            "location": row["location"],
            "total_challans": row["total_challans"],
            "paid_amount": row["paid_amount"] or 0,
            "pending_count": row["pending_count"] or 0,
            "common_offence": (
                common["offence_name"] if common else "None"
            )
        })

    conn.close()

    return render_template(
        "area_report.html",
        reports=reports
    )


# TRAFFIC ANALYSIS
@app.route("/traffic_analysis")
def traffic_analysis():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM challans")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(fine_amount) FROM challans")
    total_fine = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT SUM(fine_amount)
        FROM challans
        WHERE payment_status='Paid'
    """)
    paid_amount = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT SUM(fine_amount)
        FROM challans
        WHERE payment_status='Pending'
    """)
    pending_amount = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT
            o.offence_name,
            COUNT(c.id) AS total_cases,
            SUM(c.fine_amount) AS total_fine
        FROM offences o
        LEFT JOIN challans c
        ON c.offence_id=o.id
        GROUP BY o.id, o.offence_name
        ORDER BY total_cases DESC
    """)

    offence_stats = cursor.fetchall()

    cursor.execute("""
        SELECT
            location,
            COUNT(*) AS total_cases
        FROM challans
        GROUP BY location
        ORDER BY total_cases DESC
    """)

    area_stats = cursor.fetchall()

    cursor.execute("""
        SELECT
            o.offence_name,
            COUNT(*) AS total_cases
        FROM challans c
        JOIN offences o
        ON c.offence_id=o.id
        GROUP BY o.offence_name
        ORDER BY total_cases DESC
        LIMIT 1
    """)

    most_common = cursor.fetchone()

    conn.close()

    return render_template(
        "traffic_analysis.html",
        total=total,
        total_fine=total_fine,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        offence_stats=offence_stats,
        area_stats=area_stats,
        most_common=most_common
    )


if __name__ == "__main__":
    app.run(debug=True)