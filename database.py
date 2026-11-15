import sqlite3

def init_db():
    conn = sqlite3.connect("challenTrack.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offence_name TEXT NOT NULL,
        fine_amount INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS challans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_number TEXT NOT NULL,
        owner_name TEXT,
        offence_id INTEGER,
        fine_amount INTEGER,
        location TEXT,
        payment_status TEXT DEFAULT 'Pending'
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM offences")

    if cursor.fetchone()[0] == 0:
        offences = [
            ("No Helmet", 500),
            ("No Seat Belt", 1000),
            ("Signal Jumping", 1000),
            ("Overspeeding", 2000),
            ("No Parking", 500),
            ("Using Mobile While Driving", 1500)
        ]

        cursor.executemany(
            "INSERT INTO offences (offence_name, fine_amount) VALUES (?, ?)",
            offences
        )

    conn.commit()
    conn.close()

    print("Database created successfully!")


if __name__ == "__main__":
    init_db()