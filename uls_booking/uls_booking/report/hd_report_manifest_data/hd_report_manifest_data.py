# Copyright (c) 2025, Sowaan and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    conditions = []
    values = {}

    if (filters.get("from_date") or filters.get("to_date")) and not filters.get("date_type"):
        frappe.throw(_("Date Type is mandatory when using a Date Range filter."))

    if filters.get("shipment_number"):
        conditions.append("r2.shipment_number = %(shipment_number)s")
        values["shipment_number"] = filters["shipment_number"]

    if filters.get("custom_package_tracking_number"):
        conditions.append("r2.custom_package_tracking_number = %(custom_package_tracking_number)s")
        values["custom_package_tracking_number"] = filters["custom_package_tracking_number"]

    if filters.get("date_type") and (filters.get("from_date") or filters.get("to_date")):
        date_column = {
            "Shipped Date": "r2.shipped_date",
            "Import Date": "r2.manifest_import_date"
        }.get(filters.get("date_type"))

        if filters.get("from_date"):
            conditions.append(f"{date_column} >= %(from_date)s")
            values["from_date"] = filters["from_date"]

        if filters.get("to_date"):
            conditions.append(f"{date_column} <= %(to_date)s")
            values["to_date"] = filters["to_date"]

    if filters.get("shipped_date"):
        conditions.append("r2.shipped_date = %(shipped_date)s")
        values["shipped_date"] = filters["shipped_date"]

    if filters.get("manifest_import_date"):
        conditions.append("r2.manifest_import_date = %(manifest_import_date)s")
        values["manifest_import_date"] = filters["manifest_import_date"]

    if filters.get("origin_port"):
        conditions.append("r2.origin_port = %(origin_port)s")
        values["origin_port"] = filters["origin_port"]

    if filters.get("destination_port"):
        conditions.append("r2.destination_port = %(destination_port)s")
        values["destination_port"] = filters["destination_port"]

    if filters.get("shipper_number"):
        conditions.append("r3.shipper_number = %(shipper_number)s")
        values["shipper_number"] = filters["shipper_number"]

    if filters.get("consignee_number"):
        conditions.append("r4.consignee_number = %(consignee_number)s")
        values["consignee_number"] = filters["consignee_number"]

    if filters.get("shipper_country"):
        conditions.append("r3.shipper_country = %(shipper_country)s")
        values["shipper_country"] = filters["shipper_country"]

    if filters.get("consignee_country_code"):
        conditions.append("r4.consignee_country_code = %(consignee_country_code)s")
        values["consignee_country_code"] = filters["consignee_country_code"]

    if filters.get("origin_country"):
        conditions.append("r2.origin_country = %(origin_country)s")
        values["origin_country"] = filters["origin_country"]

    if filters.get("destination_country"):
        conditions.append("r2.destination_country = %(destination_country)s")
        values["destination_country"] = filters["destination_country"]

    if filters.get("billing_term"):
        conditions.append("r2.billing_term_field = %(billing_term)s")
        values["billing_term"] = filters["billing_term"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"


    query = f"""
        SELECT
            r2.shipment_number AS 'Shipment Number',
            r22.custom_package_tracking_number AS 'Package Tracking Number',
            r2.destination_country AS 'Destination Country',
            r2.origin_country AS 'Origin Country',
            r3.shipper_number AS 'Shipper Number',
            r3.shipper_name AS 'Shipper Name',
            r2.shipped_date AS 'Shipped Date',
            r2.manifest_import_date AS 'Import Date',
            r2.origin_port AS 'Origin Port',
            r2.destination_port AS 'Destination Port',
            r2.shipment_type AS 'Shipment Type',
            r21.custom_minimum_bill_weight AS 'Minimum Bill Weight',
            r2.shipment_weight AS 'Shipment Weight',
            r2.shipment_weight_unit AS 'Shipment Weight Unit',
            r5.custom_invdesc AS 'Invoice Description',
            r3.shipper_building AS 'Shipper Building',
            r3.shipper_street AS 'Shipper Street',
            r3.shipper_city AS 'Shipper City',
            r3.shipper_country AS 'Shipper Country',
            r4.consignee_number AS 'Consignee Number',
            r4.consignee_name AS 'Consignee Name',
            r4.consignee_contact_name AS 'Consignee Contact Name',
            r4.consignee_building AS 'Consignee Building',
            r4.consignee_street AS 'Consignee Street',
            r4.consignee_city AS 'Consignee City',
            r4.consignee_country_code AS 'Consignee Country',
            r2.billing_term_field AS 'Billing Term Field',
            r2.bill_term_surcharge_indicator AS 'Bill Term Surcharge Indicator',
            r2.terms_of_shipment AS 'Terms Of Shipment',
            r2.number_of_packages_in_shipment AS 'Number Of Packages In Shipment',
            r2.split_duty_and_vat_flag AS 'Split Duty And VAT Flag',
            r3.shipper_postal_code AS 'Shipper Postal Code',
			r2.biling_type_shipment AS 'Shipment Billing Type',
			r2.service_level AS 'Service Level',
			r4.consignee_postal_code AS 'Consignee Postal Code',
			r3.shipper_phone_number AS 'Shipper Contact Number',
			r4.consignee_phone_number AS 'Consignee Contact Number'
        FROM `tabR200000` AS r2 
        LEFT JOIN `tabR201000` AS r21 ON r2.shipment_number = r21.shipment_number 
        LEFT JOIN `tabR202000` AS r22 ON r21.shipment_number = r22.shipment_number 
        LEFT JOIN `tabR300000` AS r3 ON r22.shipment_number = r3.shipment_number 
        LEFT JOIN `tabR400000` AS r4 ON r3.shipment_number = r4.shipment_number 
        LEFT JOIN `tabR500000` AS r5 ON r4.shipment_number = r5.shipment_number 
        WHERE {where_clause}
        GROUP BY r2.shipment_number
    """

    data = frappe.db.sql(query, values=values, as_dict=1)

    columns = [
        {'fieldname': 'Shipment Number', 'label': _('Shipment Number'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'Package Tracking Number', 'label': _('Package Tracking Number'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'Destination Country', 'label': _('Destination Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Origin Country', 'label': _('Origin Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Shipper Number', 'label': _('Shipper Number'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Shipper Name', 'label': _('Shipper Name'), 'fieldtype': 'Data', 'width': 120},
		{'fieldname': 'Shipper Contact Number', 'label': _('Shipper Contact Number'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'Shipped Date', 'label': _('Shipped Date'), 'fieldtype': 'Date', 'width': 150},
        {'fieldname': 'Import Date', 'label': _('Import Date'), 'fieldtype': 'Date', 'width': 150},
        {'fieldname': 'Origin Port', 'label': _('Origin Port'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'Destination Port', 'label': _('Destination Port'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'Shipment Type', 'label': _('Shipment Type'), 'fieldtype': 'Data', 'width': 120},
    	{'fieldname': 'Shipment Billing Type', 'label': _('Shipment Billing Type'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'Minimum Bill Weight', 'label': _('Minimum Bill Weight'), 'fieldtype': 'Float', 'width': 120},
        {'fieldname': 'Shipment Weight', 'label': _('Shipment Weight'), 'fieldtype': 'Float', 'width': 120},
        {'fieldname': 'Shipment Weight Unit', 'label': _('Shipment Weight Unit'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Invoice Description', 'label': _('Invoice Description'), 'fieldtype': 'Text', 'width': 300},
        {'fieldname': 'Shipper Building', 'label': _('Shipper Building'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Shipper Street', 'label': _('Shipper Street'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Shipper City', 'label': _('Shipper City'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Shipper Country', 'label': _('Shipper Country'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Shipper Postal Code', 'label': _('Shipper Postal Code'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Consignee Number', 'label': _('Consignee Number'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Consignee Name', 'label': _('Consignee Name'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Consignee Contact Name', 'label': _('Consignee Contact Name'), 'fieldtype': 'Data', 'width': 120},
		{'fieldname': 'Consignee Contact Number', 'label': _('Consignee Contact Number'), 'fieldtype': 'Data', 'width': 150},
        {'fieldname': 'Consignee Building', 'label': _('Consignee Building'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Consignee Street', 'label': _('Consignee Street'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Consignee City', 'label': _('Consignee City'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Consignee Country', 'label': _('Consignee Country'), 'fieldtype': 'Data', 'width': 120},
		{'fieldname': 'Consignee Postal Code', 'label': _('Consignee Postal Code'), 'fieldtype': 'Data', 'width': 120},
		{'fieldname': 'Service Level', 'label': _('Service Level'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Billing Term Field', 'label': _('Billing Term Field'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Number Of Packages In Shipment', 'label': _('Number Of Packages In Shipment'), 'fieldtype': 'Int', 'width': 120},
        {'fieldname': 'Split Duty And VAT Flag', 'label': _('Split Duty And VAT Flag'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Bill Term Surcharge Indicator', 'label': _('Bill Term Surcharge Indicator'), 'fieldtype': 'Data', 'width': 120},
        {'fieldname': 'Terms Of Shipment', 'label': _('Terms Of Shipment'), 'fieldtype': 'Data', 'width': 120},
        

    ]

    return columns, data
