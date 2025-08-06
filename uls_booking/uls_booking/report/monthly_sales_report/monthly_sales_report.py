# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime, timedelta


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data




def get_columns():
    return [
        {"label": "Salesperson Name", "fieldname": "sales_person", "fieldtype": "Link", "options": "Sales Person", "width": 150},
        {"label": "Customer Name", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Customer Group", "fieldname": "customer_group", "fieldtype": "Link", "options": "Customer Group", "width": 150},
        {"label": "Account Number", "fieldname": "account_number", "fieldtype": "Data", "width": 120},
        {"label": "Product", "fieldname": "product", "fieldtype": "Data", "width": 80},

        {"label": "Last Day Shipments", "fieldname": "last_day_shipments", "fieldtype": "Int", "width": 130},
        {"label": "Last Day Weight", "fieldname": "last_day_weight", "fieldtype": "Float", "width": 120},
        {"label": "Last Day Revenue", "fieldname": "last_day_revenue", "fieldtype": "Currency", "width": 130},

        {"label": "MTD Shipments", "fieldname": "mtd_shipments", "fieldtype": "Int", "width": 120},
        {"label": "MTD Weight", "fieldname": "mtd_weight", "fieldtype": "Float", "width": 100},
        {"label": "MTD Revenue", "fieldname": "mtd_revenue", "fieldtype": "Currency", "width": 120},

        {"label": "Last Month Shipments", "fieldname": "last_month_shipments", "fieldtype": "Int", "width": 150},
        {"label": "Last Month Weight", "fieldname": "last_month_weight", "fieldtype": "Float", "width": 140},
        {"label": "Last Month Revenue", "fieldname": "last_month_revenue", "fieldtype": "Currency", "width": 150}
    ]

def get_data(filters=None):
    counter = 0
    last_date = frappe.utils.getdate(filters.get("last_date") or frappe.utils.today())
    start_of_this_month = last_date.replace(day=1)
    end_of_last_month = start_of_this_month - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)

    condition_str = build_conditions(filters)
    join_icris, icris_condition = get_icris_condition(filters)

    query_filters = filters.copy()
    query_filters.update({
        "start_date": start_of_last_month,
        "end_date": last_date
    })
    

    raw_data = frappe.db.sql(f"""
        SELECT
            st.sales_person,
            si.customer,
            cu.customer_group,
            CASE 
                WHEN si.custom_import__export_si = 'Export' THEN si.custom_shipper_number
                ELSE si.custom_consignee_number
            END AS account_number,
            si.custom_import__export_si AS product,
            CASE 
                WHEN si.custom_import__export_si = 'Export' THEN si.custom_date_shipped
                ELSE si.custom_import_date
            END AS actual_date,
            si.name AS invoice,
            si.custom_shipment_weight AS weight,
            si.base_grand_total AS revenue
        FROM(
			SELECT *
			FROM `tabSales Invoice`
			WHERE docstatus = 1 AND custom_freight_invoices = 1
			AND (
                (custom_import__export_si = 'Export' AND custom_date_shipped BETWEEN %(start_date)s AND %(end_date)s)
                OR
                (custom_import__export_si = 'Import' AND custom_import_date BETWEEN %(start_date)s AND %(end_date)s)
            )
		) si
        JOIN `tabCustomer` cu ON cu.name = si.customer
        {join_icris}
        JOIN `tabSales Team` st ON st.parent = si.name AND st.parenttype = 'Sales Invoice'
        WHERE si.docstatus = 1
            {condition_str}
            {icris_condition}
    """, values=query_filters, as_dict=True)

    result = {}

    def init_row(row):
        return {
            "sales_person": row.sales_person,
            "customer": row.customer,
            "customer_group": row.customer_group,
            "account_number": row.account_number,
            "product": row.product,
            "last_day_shipments": 0,
            "last_day_weight": 0,
            "last_day_revenue": 0,
            "mtd_shipments": 0,
            "mtd_weight": 0,
            "mtd_revenue": 0,
            "last_month_shipments": 0,
            "last_month_weight": 0,
            "last_month_revenue": 0,
        }
    

    for row in raw_data:
        key = (
            row.sales_person,
            row.customer,
            row.customer_group,
            row.account_number,
            row.product
        )

        if key not in result:
            result[key] = init_row(row)

        actual_date = row.actual_date
        weight = row.weight or 0
        revenue = row.revenue or 0

        if actual_date == last_date:
            result[key]["last_day_shipments"] += 1
            result[key]["last_day_weight"] += weight
            result[key]["last_day_revenue"] += revenue

        if start_of_this_month <= actual_date <= last_date:
            result[key]["mtd_shipments"] += 1
            result[key]["mtd_weight"] += weight
            result[key]["mtd_revenue"] += revenue

        if start_of_last_month <= actual_date <= end_of_last_month:
            result[key]["last_month_shipments"] += 1
            result[key]["last_month_weight"] += weight
            result[key]["last_month_revenue"] += revenue

    return list(result.values())

def build_conditions(filters):
    conditions = []

    if filters.get("sales_person"):
        conditions.append("st.sales_person = %(sales_person)s")

    if filters.get("customer"):
        conditions.append("si.customer = %(customer)s")

    if filters.get("customer_group"):
        conditions.append("cu.customer_group = %(customer_group)s")

    if filters.get("product"):
        conditions.append("si.custom_import__export_si = %(product)s")

    return " AND " + " AND ".join(conditions) if conditions else ""

def get_icris_condition(filters):
    icris = filters.get("icris")
    station = filters.get("station")

    join_clause = ""
    where_clause = ""

    if station:
        join_clause = """
            LEFT JOIN `tabICRIS Account` icris_acc
                ON icris_acc.name = 
                    CASE 
                        WHEN si.custom_import__export_si = 'Export' THEN si.custom_shipper_number
                        ELSE si.custom_consignee_number
                    END
        """
        where_clause += " AND icris_acc.station = %(station)s"

    if icris:
        where_clause += """
            AND CASE 
                    WHEN si.custom_import__export_si = 'Export' THEN si.custom_shipper_number
                    ELSE si.custom_consignee_number
                END = %(icris)s
        """

    return join_clause, where_clause
