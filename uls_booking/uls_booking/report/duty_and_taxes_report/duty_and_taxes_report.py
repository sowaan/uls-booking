# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt
import frappe


def execute(filters=None):
    if not filters:
        filters = {}

    def custom_scrub(txt):
        return txt.lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('&', '_')

    columns = [
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120, "nowrap": 1},
        {"label": "Invoice Number", "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 150, "nowrap": 1, "word-break": "break-word"},
        {"label": "Tracking No", "fieldname": "custom_tracking_number", "fieldtype": "Data", "width": 150, "nowrap": 1, "word-break": "break-word"},
        {"label": "Billing Term", "fieldname": "billing_term", "fieldtype": "Data", "width": 100, "nowrap": 1, "word-break": "break-word"},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150, "nowrap": 1, "word-break": "break-word"},
        {
            "label": "Customer Group",
            "fieldname": "customer_grp",
            "fieldtype": "Link",
            "options": "Customer Group",
            "width": 120
        },
        {"label": "Shipper", "fieldname": "custom_shipper_name", "fieldtype": "Data", "width": 150, "nowrap": 1, "word-break": "break-word"},
        {"label": "Consignee", "fieldname": "custom_consignee_name", "fieldtype": "Data", "width": 150, "nowrap": 1, "word-break": "break-word"},
        {"label": "Arrival Date", "fieldname": "custom_arrival_date", "fieldtype": "Data", "width": 150, "nowrap": 1, "word-break": "break-word"},
        {"label": "Location", "fieldname": "custom_location", "fieldtype": "Data", "width": 150, "nowrap": 1, "word-break": "break-word"},
        {"label": "MAWB Number", "fieldname": "custom_mawb_number", "fieldtype": "Data", "width": 150, "nowrap": 1, "word-break": "break-word"},
    ]

    where_clause, filter_values = get_conditions(filters)

    item_list = frappe.db.sql(f"""
        SELECT DISTINCT i.item_code
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        JOIN `tabItem` i ON sii.item_code = i.item_code
        WHERE {where_clause}
    """, values=filter_values, as_dict=True)

    item_columns = [item.item_code for item in item_list]

    for item in item_columns:
        columns.append({
            "label": item,
            "fieldname": custom_scrub(item),
            "fieldtype": "Currency",
            "width": 120,
            "align": "center",
            "precision": 0
        })

    columns.append({
        "label": "Total",
        "fieldname": "total",
        "fieldtype": "Currency",
        "width": 120,
        "align": "center",
        "precision": 0
    })

    results = frappe.db.sql(f"""
        SELECT
            si.name AS invoice,
            si.posting_date,
            si.custom_billing_term AS billing_term,
            si.customer,
            cust.customer_group AS customer_grp,
            si.custom_shipper_name,
            si.custom_tracking_number,
            si.total,
            si.custom_consignee_name,
            si.custom_arrival_date,
            si.custom_location,
            si.custom_mawb_number,
            i.item_code,
            sii.amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        JOIN `tabItem` i ON sii.item_code = i.item_code
        JOIN `tabCustomer` cust ON si.customer = cust.name
        WHERE {where_clause}
    """, values=filter_values, as_dict=True)

    # frappe.throw("Total records fetched: {0}").format(len(results))

    # Process into crosstab
    invoice_map = {}
    total_amount = 0.0

    for row in results:
        invoice = row.invoice
        if invoice not in invoice_map:
            invoice_map[invoice] = {
                "posting_date": row.posting_date,
                "invoice": invoice,
                "billing_term": row.billing_term,
                "customer": row.customer,
                "customer_grp": row.customer_grp,
                "custom_shipper_name": row.custom_shipper_name,
                "custom_consignee_name": row.custom_consignee_name,
                "custom_tracking_number": row.custom_tracking_number,
                "custom_arrival_date": row.custom_arrival_date,
                "custom_location": row.custom_location,
                "custom_mawb_number": row.custom_mawb_number,
                "total": row.total
            }
        invoice_map[invoice][custom_scrub(row.item_code)] = round(row.amount)
        total_amount += row.amount

    report_summary = [{
        "label": "Total Amount",
        "value": frappe.utils.fmt_money(total_amount),
        "indicator": "Blue",
    }]

    return columns, list(invoice_map.values()), None, report_summary


def get_conditions(filters):
    # frappe.throw("Filters: {0}").format(filters)
    conditions = []
    values = {}

    if filters.get("tracking_number"):
        conditions.append("si.custom_tracking_number = %(tracking_number)s")
        values["tracking_number"] = filters["tracking_number"]
    
    if filters.get("billing_term"):
        conditions.append("UPPER(si.custom_billing_term) = UPPER(%(billing_term)s)")
        values["billing_term"] = filters["billing_term"]


    if filters.get("customer"):
        conditions.append("si.customer_name = %(customer)s")
        values["customer"] = filters["customer"]

    if filters.get("invoice_number"):
        conditions.append("si.name = %(invoice_number)s")
        values["invoice_number"] = filters["invoice_number"]

    if filters.get("location"):
        conditions.append("si.custom_location = %(location)s")
        values["location"] = filters["location"]

    if filters.get("mawb_number"):
        conditions.append("si.custom_mawb_number = %(mawb_number)s")
        values["mawb_number"] = filters["mawb_number"]

    date_field = "si.custom_arrival_date" if filters.get("date_type") == "Arrival Date" else "si.posting_date"

    if filters.get("from_date"):
        conditions.append(f"{date_field} >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append(f"{date_field} <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("customer_group"):
        cus_grp = filters.get("customer_group")
        customers_from_grps = frappe.db.get_all(
            "Customer",
            filters={"customer_group": cus_grp},
            pluck="name"
        )
        if customers_from_grps:
            conditions.append("si.customer IN %(customers)s")
            values["customers"] = tuple(customers_from_grps)
        else:
            conditions.append("1=0")
            frappe.msgprint(f"No customers found for the selected customer group: {cus_grp}")


    conditions.append("si.status IN ('Overdue', 'Unpaid')")
    conditions.append("si.docstatus = 1")
    conditions.append("si.custom_duty_and_taxes_invoice = 1")

    where_clause = " AND ".join(conditions)
    return where_clause, values
