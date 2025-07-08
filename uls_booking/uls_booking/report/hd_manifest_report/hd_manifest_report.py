# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    filters = filters or {}

    # Build WHERE conditions
    conditions = []
    values = {}

    field_map = {
        "shipment_number": "shipment_number",
        "origin_port": "origin_port",
        "destination_port": "destination_port",
        "origin_country": "origin_country",
        "destination_country": "destination_country",
        "billing_term_field": "billing_term_field",
    }

    for key, field in field_map.items():
        if filters.get(key):
            conditions.append(f"{field} = %(value_{key})s")
            values[f"value_{key}"] = filters[key]

    if filters.get("date_type") in ["Shipped Date", "Import Date"]:
        date_field = "shipped_date" if filters["date_type"] == "Shipped Date" else "manifest_import_date"
        if filters.get("from_date") and filters.get("to_date"):
            conditions.append(f"{date_field} BETWEEN %(from_date)s AND %(to_date)s")
            values["from_date"] = filters["from_date"]
            values["to_date"] = filters["to_date"]
        elif filters.get("from_date"):
            conditions.append(f"{date_field} >= %(from_date)s")
            values["from_date"] = filters["from_date"]
        elif filters.get("to_date"):
            conditions.append(f"{date_field} <= %(to_date)s")
            values["to_date"] = filters["to_date"]

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f"""
        SELECT
            r2.shipment_number,
            r2.shipped_date,
            r2.manifest_import_date,
            r2.origin_country,
            r2.destination_country,
            r2.origin_port,
            r2.destination_port,
            r2.shipment_type,
            r2.shipment_weight,
            r2.shipment_weight_unit,
            r2.currency_code_for_invoice_total AS invoice_currency,
            r2.invoice_total,
            r2.billing_term_field,
            r2.bill_term_surcharge_indicator,
            r2.terms_of_shipment,
            r2.number_of_packages_in_shipment,
            r2.split_duty_and_vat_flag,
            r2.biling_type_shipment AS shipment_billing_type,
            r2.service_level,

            r21.custom_minimum_bill_weight AS minimum_bill_weight,
            r22.custom_package_tracking_number AS package_tracking_number,
            

            r3.shipper_number,
            r3.shipper_name,
            r3.shipper_postal_code,
            r3.shipper_building,
            r3.shipper_street,
            r3.shipper_city,
            r3.shipper_country,
            r3.shipper_phone_number AS shipper_contact_number,

            r4.consignee_number,
            r4.consignee_name,
            r4.consignee_contact_name,
            r4.consignee_building,
            r4.consignee_street,
            r4.consignee_city,
            r4.consignee_country_code AS consignee_country,
            r4.consignee_postal_code,
            r4.consignee_phone_number AS consignee_contact_number,
            
            r5.custom_invdesc AS invoice_description

        FROM (
            SELECT * FROM `tabR200000`
            {where_clause}
        ) AS r2

        LEFT JOIN (
            SELECT * FROM `tabR201000`
            WHERE shipment_number IN (
                SELECT shipment_number FROM `tabR200000`
                {where_clause}
            )
        ) AS r21 ON r2.shipment_number = r21.shipment_number

        LEFT JOIN (
            SELECT * FROM `tabR202000`
            WHERE shipment_number IN (
                SELECT shipment_number FROM `tabR200000`
                {where_clause}
            )
        ) AS r22 ON r2.shipment_number = r22.shipment_number

        LEFT JOIN (
            SELECT * FROM `tabR300000`
            WHERE shipment_number IN (
                SELECT shipment_number FROM `tabR200000`
                {where_clause}
            )
        ) AS r3 ON r2.shipment_number = r3.shipment_number

        LEFT JOIN (
            SELECT * FROM `tabR400000`
            WHERE shipment_number IN (
                SELECT shipment_number FROM `tabR200000`
                {where_clause}
            )
        ) AS r4 ON r2.shipment_number = r4.shipment_number

        
        LEFT JOIN (
            SELECT * FROM `tabR500000`
            WHERE shipment_number IN (
                SELECT shipment_number FROM `tabR200000`
                {where_clause}
            )
        ) AS r5 ON r2.shipment_number = r5.shipment_number

    """

    data = frappe.db.sql(query, values, as_dict=True)
    columns = [
        {'fieldname': 'shipment_number', 'label': _('Shipment Number'), 'fieldtype': 'Link', 'options': 'Shipment Number', 'width': 150},
        {'fieldname': 'package_tracking_number', 'label': _('Package Tracking Number'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'shipped_date', 'label': _('Shipped Date'), 'fieldtype': 'Date', 'width': 150},
        {'fieldname': 'import_date', 'label': _('Import Date'), 'fieldtype': 'Date', 'width': 150},
        {'fieldname': 'origin_country', 'label': _('Origin Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'destination_country', 'label': _('Destination Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'origin_port', 'label': _('Origin Port'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'destination_port', 'label': _('Destination Port'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'shipment_type', 'label': _('Shipment Type'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'shipment_billing_type', 'label': _('Shipment Billing Type'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'minimum_bill_weight', 'label': _('Minimum Bill Weight'), 'fieldtype': 'Float', 'width': 120},
        {'fieldname': 'shipment_weight', 'label': _('Shipment Weight'), 'fieldtype': 'Float', 'width': 120},
        {'fieldname': 'shipment_weight_unit', 'label': _('Shipment Weight Unit'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'invoice_currency', 'label': _('Invoice Currency'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'invoice_total', 'label': _('Invoice Total'), 'fieldtype': 'Currency', 'width': 120},
        {'fieldname': 'invoice_description', 'label': _('Invoice Description'), 'fieldtype': 'Text', 'width': 300},
        {'fieldname': 'shipper_number', 'label': _('Shipper Number'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'shipper_name', 'label': _('Shipper Name'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'shipper_contact_number', 'label': _('Shipper Contact Number'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'shipper_building', 'label': _('Shipper Building'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'shipper_street', 'label': _('Shipper Street'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'shipper_city', 'label': _('Shipper City'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'shipper_country', 'label': _('Shipper Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'shipper_postal_code', 'label': _('Shipper Postal Code'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'consignee_number', 'label': _('Consignee Number'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'consignee_name', 'label': _('Consignee Name'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'consignee_contact_name', 'label': _('Consignee Contact Name'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'consignee_contact_number', 'label': _('Consignee Contact Number'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'consignee_building', 'label': _('Consignee Building'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'consignee_street', 'label': _('Consignee Street'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'consignee_city', 'label': _('Consignee City'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'consignee_country', 'label': _('Consignee Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'consignee_postal_code', 'label': _('Consignee Postal Code'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'service_level', 'label': _('Service Level'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'billing_term_field', 'label': _('Billing Term Field'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'number_of_packages_in_shipment', 'label': _('Number Of Packages In Shipment'), 'fieldtype': 'Int', 'width': 120},
        {'fieldname': 'split_duty_and_vat_flag', 'label': _('Split Duty And VAT Flag'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'bill_term_surcharge_indicator', 'label': _('Bill Term Surcharge Indicator'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'terms_of_shipment', 'label': _('Terms Of Shipment'), 'fieldtype': 'Data', 'width': 120},
    ]

    return columns, data
