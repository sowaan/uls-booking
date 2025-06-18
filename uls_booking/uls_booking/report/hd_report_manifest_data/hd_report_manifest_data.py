# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _




def execute(filters=None):
    filters = filters or {}
    conditions = []
    values = {}

    # if (filters.get("from_date") or filters.get("to_date")) and not filters.get("date_type"):
    #     frappe.throw(_("Date Type is mandatory when using a Date Range filter."))

    filter_mapping = [
        ("shipment_number", "r2.shipment_number", "="),
        ("custom_package_tracking_number", "r22.custom_package_tracking_number", "="),
        # ("shipped_date", "r2.shipped_date", "="),
        # ("manifest_import_date", "r2.manifest_import_date", "="),
        ("origin_port", "r2.origin_port", "="),
        ("destination_port", "r2.destination_port", "="),
        ("shipper_number", "r3.shipper_number", "="),
        ("consignee_number", "r4.consignee_number", "="),
        ("shipper_country", "r3.shipper_country", "="),
        ("consignee_country_code", "r4.consignee_country_code", "="),
        ("origin_country", "r2.origin_country", "="),
        ("destination_country", "r2.destination_country", "="),
        ("billing_term", "r2.billing_term_field", "=")
    ]

    for filter_key, column, operator in filter_mapping:
        if filters.get(filter_key):
            conditions.append(f"{column} {operator} %({filter_key})s")
            values[filter_key] = filters[filter_key]

    # Handle date range filters
    if filters.get("date_type"):
        date_column = {
            "Shipped Date": "r2.shipped_date",
            "Import Date": "r2.manifest_import_date"
        }.get(filters.get("date_type"))

        if date_column:
            conditions.append(f"{date_column} IS NOT NULL")

            if filters.get("from_date"):
                conditions.append(f"{date_column} >= %(from_date)s")
                values["from_date"] = filters["from_date"]

            if filters.get("to_date"):
                conditions.append(f"{date_column} <= %(to_date)s")
                values["to_date"] = filters["to_date"]

    # Build the WHERE clause
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    frappe.msgprint(str(where_clause))
    frappe.msgprint(str(values))
    # frappe.msgprint(_("Where Clause: {0}").format(where_clause))
    print(where_clause)  # Debugging line to check the where clause


    query = f"""
        SELECT DISTINCT
            r2.shipment_number AS 'shipment_number',
            r2.destination_country AS 'destination_country',
            r2.origin_country AS 'origin_country',
            r2.shipped_date AS 'shipped_date',
            r2.manifest_import_date AS 'import_date',
            r2.origin_port AS 'origin_port',
            r2.destination_port AS 'destination_port',
            r2.shipment_type AS 'shipment_type',
            r2.shipment_weight AS 'shipment_weight',
            r2.shipment_weight_unit AS 'shipment_weight_unit',
            r2.currency_code_for_invoice_total AS 'invoice_currency',
            r2.invoice_total AS 'invoice_total',
            r2.billing_term_field AS 'billing_term_field',
            r2.bill_term_surcharge_indicator AS 'bill_term_surcharge_indicator',
            r2.terms_of_shipment AS 'terms_of_shipment',
            r2.number_of_packages_in_shipment AS 'number_of_packages_in_shipment',
            r2.split_duty_and_vat_flag AS 'split_duty_and_vat_flag',
            r2.biling_type_shipment AS 'shipment_billing_type',
            r2.service_level AS 'service_level'
        FROM `tabR200000` r2
        WHERE {where_clause}
        GROUP BY r2.shipment_number
    """



    data = frappe.db.sql(query, values=values, as_dict=1)
    # frappe.msgprint(str(data))

    columns = [
        {'fieldname': 'shipment_number', 'label': _('Shipment Number'), 'fieldtype': 'Link', 'options': 'Shipment Number', 'width': 150},
        {'fieldname': 'shipped_date', 'label': _('Shipped Date'), 'fieldtype': 'Date', 'width': 150},
        {'fieldname': 'import_date', 'label': _('Import Date'), 'fieldtype': 'Date', 'width': 150},
        {'fieldname': 'origin_country', 'label': _('Origin Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'destination_country', 'label': _('Destination Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'origin_port', 'label': _('Origin Port'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'destination_port', 'label': _('Destination Port'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'shipment_type', 'label': _('Shipment Type'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'shipment_billing_type', 'label': _('Shipment Billing Type'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'shipment_weight', 'label': _('Shipment Weight'), 'fieldtype': 'Float', 'width': 120},
        {'fieldname': 'shipment_weight_unit', 'label': _('Shipment Weight Unit'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'invoice_currency', 'label': _('Invoice Currency'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'invoice_total', 'label': _('Invoice Total'), 'fieldtype': 'Currency', 'width': 120},
        {'fieldname': 'billing_term_field', 'label': _('Billing Term Field'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'bill_term_surcharge_indicator', 'label': _('Bill Term Surcharge Indicator'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'terms_of_shipment', 'label': _('Terms Of Shipment'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'number_of_packages_in_shipment', 'label': _('Number Of Packages In Shipment'), 'fieldtype': 'Int', 'width': 120},
        {'fieldname': 'split_duty_and_vat_flag', 'label': _('Split Duty And VAT Flag'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'service_level', 'label': _('Service Level'), 'fieldtype': 'Data', 'width': 120},
    ]



    return columns, data
