"""Build deterministic Bronze, Silver, and Gold CSV fixtures for the Hive lesson.

The Week 2 source files do not contain order-to-customer or order-to-employee
foreign keys. This training fixture assigns those relationships by stable
round-robin position, and assigns employees to offices the same way. Bronze
retains unmatched order-detail rows, while Silver and Gold keep only complete,
valid order lines.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "docs/Training/Week2/sample_warehouse"
OUTPUT_DIR = REPO_ROOT / "docs/Training/Week3/2.1_hive_migration/tmp/data"
INGESTED_AT_UTC = "2026-09-22T00:00:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (SOURCE_DIR / name).open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def full_name(row: dict[str, str]) -> str:
    return f"{row['first_name']} {row['last_name']}"


def main() -> None:
    customers = sorted(read_csv("customers.csv"), key=lambda row: int(row["id"]))
    employees = sorted(read_csv("employees.csv"), key=lambda row: int(row["id"]))
    offices = sorted(read_csv("offices.csv"), key=lambda row: int(row["id"]))
    orders = sorted(read_csv("orders.csv"), key=lambda row: int(row["order_number"]))
    order_details = sorted(
        read_csv("orderdetails.csv"),
        key=lambda row: (int(row["order_number"]), row["product_number"]),
    )
    products = sorted(read_csv("products.csv"), key=lambda row: row["product_number"])

    order_by_number = {row["order_number"]: row for row in orders}
    product_by_number = {row["product_number"]: row for row in products}
    employee_office = {
        employee["id"]: offices[index % len(offices)]
        for index, employee in enumerate(employees)
    }
    order_assignments = {
        order["order_number"]: (
            customers[index % len(customers)],
            employees[index % len(employees)],
        )
        for index, order in enumerate(orders)
    }

    bronze_rows: list[dict[str, object]] = []
    for source_row_number, detail in enumerate(order_details, start=1):
        order = order_by_number.get(detail["order_number"])
        product = product_by_number.get(detail["product_number"])
        customer, employee = order_assignments.get(detail["order_number"], ({}, {}))
        office = employee_office.get(employee.get("id", ""), {})
        bronze_rows.append(
            {
                "bronze_row_id": source_row_number,
                "order_number": detail["order_number"],
                "order_date": order.get("order_date", "") if order else "",
                "expected_receiving_date": order.get("expected_receiving_date", "") if order else "",
                "shipping_date": order.get("shipping_date", "") if order else "",
                "order_status": order.get("status", "") if order else "",
                "customer_id": customer.get("id", ""),
                "customer_company": customer.get("company", ""),
                "customer_contact": full_name(customer) if customer else "",
                "employee_id": employee.get("id", ""),
                "employee_name": full_name(employee) if employee else "",
                "office_id": office.get("id", ""),
                "office_city": office.get("city", ""),
                "product_number": detail["product_number"],
                "product_name": product.get("product_name", "") if product else "",
                "product_category": product.get("product_category", "") if product else "",
                "source_product_category_code": detail["product_category"],
                "unit_price": detail["price"],
                "quantity": detail["quantity"],
                "source_file": "orderdetails.csv",
                "ingested_at_utc": INGESTED_AT_UTC,
            }
        )

    bronze_fields = list(bronze_rows[0])
    write_csv(OUTPUT_DIR / "bronze/sales_raw.csv", bronze_fields, bronze_rows)

    line_counters: defaultdict[str, int] = defaultdict(int)
    silver_rows: list[dict[str, object]] = []
    for bronze in bronze_rows:
        try:
            order_date = date.fromisoformat(str(bronze["order_date"]))
            expected_date = date.fromisoformat(str(bronze["expected_receiving_date"]))
            shipping_value = str(bronze["shipping_date"])
            shipping_date = date.fromisoformat(shipping_value) if shipping_value else None
            unit_price = Decimal(str(bronze["unit_price"]))
            quantity = int(str(bronze["quantity"]))
        except (ValueError, ArithmeticError):
            continue

        required_values = (
            bronze["order_status"],
            bronze["customer_id"],
            bronze["employee_id"],
            bronze["office_id"],
            bronze["product_name"],
            bronze["product_category"],
        )
        if not all(required_values) or unit_price <= 0 or quantity <= 0:
            continue

        order_number = str(bronze["order_number"])
        line_counters[order_number] += 1
        silver_rows.append(
            {
                "order_number": int(order_number),
                "order_line_number": line_counters[order_number],
                "order_date": order_date.isoformat(),
                "expected_receiving_date": expected_date.isoformat(),
                "shipping_date": shipping_date.isoformat() if shipping_date else "",
                "order_status": bronze["order_status"],
                "customer_id": int(str(bronze["customer_id"])),
                "employee_id": int(str(bronze["employee_id"])),
                "office_id": int(str(bronze["office_id"])),
                "product_number": bronze["product_number"],
                "product_name": bronze["product_name"],
                "product_category": bronze["product_category"],
                "unit_price": f"{unit_price:.2f}",
                "quantity": quantity,
                "sales_amount": f"{unit_price * quantity:.2f}",
                "shipping_days": (shipping_date - order_date).days if shipping_date else "",
            }
        )

    silver_fields = list(silver_rows[0])
    write_csv(OUTPUT_DIR / "silver/sales_clean.csv", silver_fields, silver_rows)

    used_customer_ids = {str(row["customer_id"]) for row in silver_rows}
    used_employee_ids = {str(row["employee_id"]) for row in silver_rows}
    used_product_numbers = {str(row["product_number"]) for row in silver_rows}
    used_statuses = sorted({str(row["order_status"]) for row in silver_rows})
    used_dates = sorted({date.fromisoformat(str(row["order_date"])) for row in silver_rows})

    category_names = sorted(
        {product_by_number[number]["product_category"] for number in used_product_numbers}
    )
    category_keys = {name: index for index, name in enumerate(category_names, start=1)}
    category_rows = [
        {"category_key": key, "product_category": name}
        for name, key in category_keys.items()
    ]

    used_products = [row for row in products if row["product_number"] in used_product_numbers]
    product_keys = {
        row["product_number"]: index for index, row in enumerate(used_products, start=1)
    }
    product_rows = [
        {
            "product_key": product_keys[row["product_number"]],
            "product_number": row["product_number"],
            "product_name": row["product_name"],
            "category_key": category_keys[row["product_category"]],
            "product_scale": row["product_scale"],
            "product_manufacturer": row["product_manufacturer"],
            "length": row["length"],
            "width": row["width"],
            "height": row["height"],
        }
        for row in used_products
    ]

    used_customers = [row for row in customers if row["id"] in used_customer_ids]
    customer_keys = {row["id"]: index for index, row in enumerate(used_customers, start=1)}
    customer_rows = [
        {
            "customer_key": customer_keys[row["id"]],
            "customer_id": row["id"],
            "company": row["company"],
            "contact_name": full_name(row),
            "phone": row["phone"],
            "address": row["address"],
            "city_and_state": row["city_and_state"],
            "postal_code": row["postal_code"],
            "country": row["country"],
        }
        for row in used_customers
    ]

    office_keys = {row["id"]: index for index, row in enumerate(offices, start=1)}
    office_rows = [
        {
            "office_key": office_keys[row["id"]],
            "office_id": row["id"],
            "city": row["city"],
            "phone": row["phone"],
            "address_1": row["address_1"],
            "address_2": row["address_2"],
            "state_or_region": row["state_or_region"],
            "country": row["country"],
            "postal_code": row["post_code"],
        }
        for row in offices
    ]

    used_employees = [row for row in employees if row["id"] in used_employee_ids]
    employee_keys = {row["id"]: index for index, row in enumerate(used_employees, start=1)}
    employee_rows = [
        {
            "employee_key": employee_keys[row["id"]],
            "employee_id": row["id"],
            "employee_name": full_name(row),
            "badge_code": row["badge_code"],
            "email": row["email"],
            "job_title": row["job_title"],
            "office_key": office_keys[employee_office[row["id"]]["id"]],
        }
        for row in used_employees
    ]

    date_rows = [
        {
            "date_key": int(value.strftime("%Y%m%d")),
            "full_date": value.isoformat(),
            "year": value.year,
            "quarter": ((value.month - 1) // 3) + 1,
            "month": value.month,
            "month_name": value.strftime("%B"),
            "day_of_month": value.day,
            "day_of_week": value.strftime("%A"),
        }
        for value in used_dates
    ]
    date_keys = {row["full_date"]: row["date_key"] for row in date_rows}

    status_keys = {status: index for index, status in enumerate(used_statuses, start=1)}
    status_rows = [
        {"status_key": key, "order_status": status}
        for status, key in status_keys.items()
    ]

    fact_rows = [
        {
            "sales_key": index,
            "order_number": row["order_number"],
            "order_line_number": row["order_line_number"],
            "order_date_key": date_keys[str(row["order_date"])],
            "product_key": product_keys[str(row["product_number"])],
            "customer_key": customer_keys[str(row["customer_id"])],
            "employee_key": employee_keys[str(row["employee_id"])],
            "status_key": status_keys[str(row["order_status"])],
            "quantity": row["quantity"],
            "unit_price": row["unit_price"],
            "sales_amount": row["sales_amount"],
            "shipping_days": row["shipping_days"],
        }
        for index, row in enumerate(silver_rows, start=1)
    ]

    gold_outputs = {
        "dim_customer.csv": customer_rows,
        "dim_date.csv": date_rows,
        "dim_employee.csv": employee_rows,
        "dim_office.csv": office_rows,
        "dim_order_status.csv": status_rows,
        "dim_product.csv": product_rows,
        "dim_product_category.csv": category_rows,
        "fact_sales.csv": fact_rows,
    }
    for name, rows in gold_outputs.items():
        write_csv(OUTPUT_DIR / "gold" / name, list(rows[0]), rows)


if __name__ == "__main__":
    main()
