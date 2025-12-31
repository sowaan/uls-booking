import frappe

UNIQUE_DOCTYPES = (
    "R200000",
    "R300000",
    "R400000",
)

INDEX_ONLY_DOCTYPES = (
    "R201000",
    "R202000",
    "R401000",
    "R402000",
    "R500000",
    "R600000",
    "R900000",
)

FIELDS = ["shipment_number", "manifest_input_date"]


def execute():
    for doctype in UNIQUE_DOCTYPES:
        add_index(doctype, FIELDS, unique=False)

    for doctype in INDEX_ONLY_DOCTYPES:
        add_index(doctype, FIELDS, unique=False)


def add_index(doctype, fields, unique=False):
    table = f"tab{doctype}"
    index_name = (
        f"uniq_{doctype}_{'_'.join(fields)}"
        if unique
        else f"idx_{doctype}_{'_'.join(fields)}"
    )

    # ✅ Check index existence via information_schema
    exists = frappe.db.sql(
        """
        SELECT 1
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        LIMIT 1
        """,
        (table, index_name),
    )

    if exists:
        return

    index_type = "UNIQUE" if unique else "INDEX"

    frappe.db.sql(
        f"""
        ALTER TABLE `{table}`
        ADD {index_type} `{index_name}`
        ({', '.join(f'`{f}`' for f in fields)})
        """
    )
