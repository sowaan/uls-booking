# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt
import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    def custom_scrub(txt):
        return txt.lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace('&', '_')

    columns = [
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120, "nowrap": 1},
        {"label": "Tracking No", "fieldname": "custom_tracking_number", "fieldtype": "Data", "width": 150, "nowrap": 1, "word-break": "break-word"},
        {"label": "Shipper", "fieldname": "custom_shipper_name", "fieldtype": "Data", "width": 150, "nowrap": 1, "word-break": "break-word"},
    ]

    filter_values = {
        "tracking_number": filters.get("tracking_number"),
        "from_date": filters.get("from_date"),
        "to_date": filters.get("to_date"),
        "customer": filters.get("customer"),
        "consignee_number": filters.get("consignee_number"),
        "consignee_name": filters.get("consignee_name"),
        "invoice_number": filters.get("invoice_number"),
        "arrival_date": filters.get("arrival_date"),
        "location": filters.get("location"),
        "mawb_number": filters.get("mawb_number")
    }

    item_list = frappe.db.sql("""
        SELECT DISTINCT i.item_code
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        JOIN `tabItem` i ON sii.item_code = i.item_code
        WHERE si.status IN ('Overdue', 'Unpaid') AND si.docstatus = 1
            AND si.custom_duty_and_taxes_invoice = 1
            AND (si.custom_tracking_number = %(tracking_number)s OR %(tracking_number)s IS NULL)
            AND (si.posting_date >= %(from_date)s OR %(from_date)s IS NULL)
            AND (si.posting_date <= %(to_date)s OR %(to_date)s IS NULL)
            AND (si.customer_name = %(customer)s OR %(customer)s IS NULL)
            AND (si.custom_consignee_number = %(consignee_number)s OR %(consignee_number)s IS NULL)
            AND (si.custom_consignee_name = %(consignee_name)s OR %(consignee_name)s IS NULL)
            AND (si.name = %(invoice_number)s OR %(invoice_number)s IS NULL)
            AND (si.custom_arrival_date = %(arrival_date)s OR %(arrival_date)s IS NULL)
            AND (si.custom_location = %(location)s OR %(location)s IS NULL)
            AND (si.custom_mawb_number = %(mawb_number)s OR %(mawb_number)s IS NULL)
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

    # Add total field as the last column
    columns.append({
        "label": "Total",
        "fieldname": "total",
        "fieldtype": "Currency",
        "width": 120,
        "align": "center",
        "precision": 0
    })

    # Get invoice-item-amount mapping along with additional fields
    results = frappe.db.sql("""
        SELECT
            si.name AS invoice,
            si.posting_date,
            si.customer,
            si.custom_shipper_name,
            si.custom_tracking_number,
            si.total,
            i.item_code,
            sii.amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        JOIN `tabItem` i ON sii.item_code = i.item_code
        WHERE si.status IN ('Overdue', 'Unpaid') AND si.docstatus = 1
            AND si.custom_duty_and_taxes_invoice = 1
            AND (si.custom_tracking_number = %(tracking_number)s OR %(tracking_number)s IS NULL)
            AND (si.posting_date >= %(from_date)s OR %(from_date)s IS NULL)
            AND (si.posting_date <= %(to_date)s OR %(to_date)s IS NULL)
            AND (si.customer_name = %(customer)s OR %(customer)s IS NULL)
            AND (si.custom_consignee_number = %(consignee_number)s OR %(consignee_number)s IS NULL)
            AND (si.custom_consignee_name = %(consignee_name)s OR %(consignee_name)s IS NULL)
            AND (si.name = %(invoice_number)s OR %(invoice_number)s IS NULL)
            AND (si.custom_arrival_date = %(arrival_date)s OR %(arrival_date)s IS NULL)
            AND (si.custom_location = %(location)s OR %(location)s IS NULL)
            AND (si.custom_mawb_number = %(mawb_number)s OR %(mawb_number)s IS NULL)
            
    """, values=filter_values, as_dict=True)

    # Process into crosstab
    invoice_map = {}
    total_amount = 0.00

    for row in results:
        invoice = row.invoice
        if invoice not in invoice_map:
            invoice_map[invoice] = {
                "posting_date": row.posting_date,
                "custom_shipper_name": row.custom_shipper_name,
                "custom_tracking_number": row.custom_tracking_number,
                "total": row.total
            }
        invoice_map[invoice][custom_scrub(row.item_code)] = round(row.amount)
        total_amount += row.amount

    report_summary = [
        {
            "label": "Total Amount",
            "value": frappe.utils.fmt_money(total_amount),
            "indicator": "Blue",
        }
    ]

    return columns, list(invoice_map.values()), None, report_summary

