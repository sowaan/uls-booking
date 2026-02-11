import frappe
# from frappe.database.utils import rename_table

def execute():
    create_index(
        "Full Tariff",
        "idx_full_tariff_lookup",
        ["country", "rate_type", "service_type", "package_type", "valid_from", "expiry_date"]
    )

    create_index(
        "Selling Rate",
        "idx_selling_rate_lookup",
        ["zone", "service_type", "package_type", "rate_group"]
    )

    create_index(
        "Fuel Surcharge Percentage on Freight Amount",
        "idx_fuel_surcharge_parent_date",
        ["parent", "from_date", "expiry_date"]
    )


def create_index(doctype, index_name, columns):
    table = f"tab{doctype}"
    cols = ", ".join(columns)

    if not index_exists(table, index_name):
        frappe.db.sql(
            f"CREATE INDEX {index_name} ON `{table}` ({cols})"
        )
        frappe.db.commit()


def index_exists(table, index_name):
    result = frappe.db.sql(f"""
        SELECT 1
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE table_schema = DATABASE()
        AND table_name = %s
        AND index_name = %s
    """, (table, index_name))

    return bool(result)
