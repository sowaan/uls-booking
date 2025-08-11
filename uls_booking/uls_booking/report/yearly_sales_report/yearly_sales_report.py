# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from datetime import date, timedelta
from frappe.utils import getdate, today

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

        {"label": "Quarterly Shipments", "fieldname": "quarterly_shipments", "fieldtype": "Int", "width": 130},
        {"label": "Quarterly Weight", "fieldname": "quarterly_weight", "fieldtype": "Float", "width": 120},
        {"label": "Quarterly Revenue", "fieldname": "quarterly_revenue", "fieldtype": "Currency", "width": 130},

        {"label": "YTD Shipments", "fieldname": "ytd_shipments", "fieldtype": "Int", "width": 120},
        {"label": "YTD Weight", "fieldname": "ytd_weight", "fieldtype": "Float", "width": 100},
        {"label": "YTD Revenue", "fieldname": "ytd_revenue", "fieldtype": "Currency", "width": 120},

        {"label": "Last Year Shipments", "fieldname": "last_year_shipments", "fieldtype": "Int", "width": 150},
        {"label": "Last Year Weight", "fieldname": "last_year_weight", "fieldtype": "Float", "width": 140},
        {"label": "Last Year Revenue", "fieldname": "last_year_revenue", "fieldtype": "Currency", "width": 150}
    ]

def get_data(filters=None):
    selected_year = int(filters.get("year"))
    selected_quarter = filters.get("quarter")

    quarter_start, quarter_end = get_quarter_dates(selected_year, selected_quarter)
    ytd_start = getdate(f"{selected_year}-01-01")
    ytd_end = getdate(today())

    last_year = selected_year - 1
    last_year_start = getdate(f"{last_year}-01-01")
    last_year_end = getdate(f"{last_year}-12-31")

    # query_filters = {
    #     "quarter_start": quarter_start,
    #     "quarter_end": quarter_end,
    #     "ytd_start": ytd_start,
    #     "ytd_end": ytd_end,
    #     "last_year_start": last_year_start,
    #     "last_year_end": last_year_end,
    #     "icris": filters.get("icris"),
    #     ""
    # }
    filters["last_year_start"] = last_year_start
    filters["ytd_end"] = ytd_end

    # msg = "<b>Query Filters:</b><br>"
    # for k, v in query_filters.items():
    #     msg += f"{k}: {v}<br>"

    # frappe.msgprint(msg)

    condition_str = build_conditions(filters)
    join_icris, icris_condition = get_icris_condition(filters)

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
            si.custom_shipment_weight AS weight,
            si.custom_amount_after_discount AS revenue
        FROM(
			SELECT *
			FROM `tabSales Invoice`
			WHERE docstatus = 1 AND custom_freight_invoices = 1
			AND (
                (custom_import__export_si = 'Export' AND custom_date_shipped BETWEEN %(last_year_start)s AND %(ytd_end)s)
                OR
                (custom_import__export_si = 'Import' AND custom_import_date BETWEEN %(last_year_start)s AND %(ytd_end)s)
            )
		) si
        JOIN `tabCustomer` cu ON cu.name = si.customer
        {join_icris}
        JOIN `tabSales Team` st ON st.parent = si.name AND st.parenttype = 'Sales Invoice'
        WHERE si.docstatus = 1
            {condition_str}
            {icris_condition}
    """, values=filters, as_dict=True)

    result = {}

    def init_row(row):
        return {
            "sales_person": row.sales_person,
            "customer": row.customer,
            "customer_group": row.customer_group,
            "account_number": row.account_number,
            "product": row.product,
            "quarterly_shipments": 0,
            "quarterly_weight": 0,
            "quarterly_revenue": 0,
            "ytd_shipments": 0,
            "ytd_weight": 0,
            "ytd_revenue": 0,
            "last_year_shipments": 0,
            "last_year_weight": 0,
            "last_year_revenue": 0,
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

        if quarter_start <= actual_date <= quarter_end:
            result[key]["quarterly_shipments"] += 1
            result[key]["quarterly_weight"] += weight
            result[key]["quarterly_revenue"] += revenue

        if ytd_start <= actual_date <= ytd_end:
            result[key]["ytd_shipments"] += 1
            result[key]["ytd_weight"] += weight
            result[key]["ytd_revenue"] += revenue

        if last_year_start <= actual_date <= last_year_end:
            result[key]["last_year_shipments"] += 1
            result[key]["last_year_weight"] += weight
            result[key]["last_year_revenue"] += revenue
            
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

def get_quarter_dates(year: int, quarter: str):
    if quarter == "1st":
        return getdate(f"{year}-01-01"), getdate(f"{year}-03-31")
    elif quarter == "2nd":
        return getdate(f"{year}-04-01"), getdate(f"{year}-06-30")
    elif quarter == "3rd":
        return getdate(f"{year}-07-01"), getdate(f"{year}-09-30")
    elif quarter == "4th":
        return getdate(f"{year}-10-01"), getdate(f"{year}-12-31")
    else:
        return None, None
