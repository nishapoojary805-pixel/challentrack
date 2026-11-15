import json
import os
import re
from datetime import datetime

DATA_FILE = "challans.json"

OFFENCES = {
    "No Helmet": 500,
    "No Seat Belt": 1000,
    "Over Speeding": 2000,
    "Signal Jumping": 1000,
    "No Parking": 500,
    "Drunk Driving": 10000,
    "Using Mobile While Driving": 1500
}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)

    return {
        "offences": OFFENCES.copy(),
        "challans": []
    }


data = load_data()


def save_data():
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


def validate_vehicle(vehicle):
    pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"
    return re.match(pattern, vehicle) is not None


def display_offences():
    print("\n========== TRAFFIC OFFENCES ==========")

    for i, (offence, fine) in enumerate(data["offences"].items(), 1):
        print(f"{i}. {offence} - Rs.{fine}")


def add_offence():
    offence = input("Enter offence name: ").strip().title()

    if not offence:
        print("Offence name cannot be empty!")
        return

    if offence in data["offences"]:
        print("Offence already exists!")
        return

    try:
        fine = int(input("Enter fine amount: "))

        if fine <= 0:
            print("Fine must be greater than zero!")
            return

        data["offences"][offence] = fine
        save_data()

        print("Offence added successfully!")

    except ValueError:
        print("Enter a valid fine amount!")


def issue_challan():
    print("\n========== ISSUE CHALLAN ==========")

    vehicle = input("Enter vehicle number: ").strip().upper()

    if not validate_vehicle(vehicle):
        print("Invalid vehicle number!")
        print("Example: KA01AB1234")
        return

    display_offences()

    offence = input("\nEnter offence name: ").strip().title()

    if offence not in data["offences"]:
        print("Invalid offence!")
        return

    base_fine = data["offences"][offence]

    repeat_count = sum(
        1 for c in data["challans"]
        if c["vehicle"] == vehicle and c["offence"] == offence
    )

    fine = int(base_fine * (1 + 0.5 * repeat_count))

    challan = {
        "id": max(
            [c["id"] for c in data["challans"]],
            default=0
        ) + 1,
        "vehicle": vehicle,
        "offence": offence,
        "fine": fine,
        "paid": 0,
        "date": datetime.now().strftime("%d-%m-%Y"),
        "status": "Pending"
    }

    data["challans"].append(challan)
    save_data()

    print("\nChallan issued successfully!")
    print("Challan ID:", challan["id"])
    print("Vehicle:", vehicle)
    print("Offence:", offence)
    print("Repeat offences:", repeat_count)
    print("Final Fine: Rs.", fine)


def pay_challan():
    print("\n========== PAY CHALLAN ==========")

    try:
        challan_id = int(input("Enter challan ID: "))
    except ValueError:
        print("Invalid challan ID!")
        return

    for challan in data["challans"]:

        if challan["id"] == challan_id:

            due = challan["fine"] - challan["paid"]

            if due == 0:
                print("Challan already paid!")
                return

            print("Vehicle:", challan["vehicle"])
            print("Total Fine: Rs.", challan["fine"])
            print("Amount Due: Rs.", due)

            try:
                amount = int(input("Enter payment amount: "))

                if amount <= 0 or amount > due:
                    print("Invalid payment amount!")
                    return

                challan["paid"] += amount

                if challan["paid"] == challan["fine"]:
                    challan["status"] = "Paid"
                else:
                    challan["status"] = "Partially Paid"

                save_data()

                print("Payment recorded successfully!")
                print("Remaining Amount: Rs.",
                      challan["fine"] - challan["paid"])

            except ValueError:
                print("Enter a valid amount!")

            return

    print("Challan not found!")


def pending_challans():
    print("\n========== PENDING CHALLANS ==========")

    vehicle = input("Enter vehicle number: ").strip().upper()

    if not validate_vehicle(vehicle):
        print("Invalid vehicle number!")
        return

    pending = [
        c for c in data["challans"]
        if c["vehicle"] == vehicle
        and c["paid"] < c["fine"]
    ]

    if not pending:
        print("No pending challans found!")
        return

    total_due = 0

    for c in pending:
        due = c["fine"] - c["paid"]
        total_due += due

        print("\nChallan ID:", c["id"])
        print("Offence:", c["offence"])
        print("Fine: Rs.", c["fine"])
        print("Paid: Rs.", c["paid"])
        print("Due: Rs.", due)
        print("Status:", c["status"])

    print("\nTotal Pending Challans:", len(pending))
    print("Total Amount Due: Rs.", total_due)


def display_all_challans():
    print("\n========== ALL CHALLANS ==========")

    if not data["challans"]:
        print("No challans available!")
        return

    for c in data["challans"]:
        print("\nChallan ID:", c["id"])
        print("Vehicle:", c["vehicle"])
        print("Offence:", c["offence"])
        print("Fine: Rs.", c["fine"])
        print("Paid: Rs.", c["paid"])
        print("Status:", c["status"])
        print("Date:", c["date"])


def main():
    while True:
        print("\n========================================")
        print("       CHALLAN TRACK SYSTEM")
        print(" TRAFFIC VIOLATION AND PENALTY MANAGEMENT")
        print("========================================")
        print("1. Display Traffic Offences")
        print("2. Add New Offence")
        print("3. Issue Challan")
        print("4. Record Challan Payment")
        print("5. List Pending Challans")
        print("6. Display All Challans")
        print("7. Exit")
        print("========================================")

        choice = input("Enter your choice: ")

        if choice == "1":
            display_offences()

        elif choice == "2":
            add_offence()

        elif choice == "3":
            issue_challan()

        elif choice == "4":
            pay_challan()

        elif choice == "5":
            pending_challans()

        elif choice == "6":
            display_all_challans()

        elif choice == "7":
            print("Thank you for using ChallanTrack!")
            break

        else:
            print("Invalid choice! Try again.")


if __name__ == "__main__":
    main()