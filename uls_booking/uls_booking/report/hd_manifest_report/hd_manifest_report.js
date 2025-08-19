// Copyright (c) 2025, Sowaan and contributors
// For license information, please see license.txt

frappe.query_reports["HD Manifest Report"] = {
    "filters": [
		{
            "fieldname": "date_type",
            "label": __("Date Type"),
            "fieldtype": "Select",
            "options": "\nShipped Date\nImport Date"
        },
		{
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "shipment_number",
            "label": __("Shipment Number"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "custom_package_tracking_number",
            "label": __("Package Tracking Number"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "origin_port",
            "label": __("Origin Port"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "destination_port",
            "label": __("Destination Port"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "shipper_number",
            "label": __("Shipper Number"),
            "fieldtype": "Link",
            "options": "ICRIS Account",
        },
        {
            "fieldname": "consignee_number",
            "label": __("Consignee Number"),
            "fieldtype": "Link",
            "options": "ICRIS Account",
        },
        {
            "fieldname": "shipper_country",
            "label": __("Shipper Country"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "consignee_country_code",
            "label": __("Consignee Country"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "origin_country",
            "label": __("Origin Country"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "destination_country",
            "label": __("Destination Country"),
            "fieldtype": "Data"
        },
        {
            "fieldname": "billing_term_field",
            "label": __("Billing Term"),
            "fieldtype": "Data"
        }
    ]
};
