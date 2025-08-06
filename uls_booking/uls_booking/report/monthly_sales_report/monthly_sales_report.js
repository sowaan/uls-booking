// Copyright (c) 2025, Sowaan and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Sales Report"] = {
    "filters": [
        {
            "fieldname": "sales_person",
            "label": "Sales Person",
            "fieldtype": "Link",
            "options": "Sales Person"
        },
        {
            "fieldname": "last_date",
            "label": "Last Date",
            "fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
        },
        {
            "fieldname": "customer",
            "label": "Customer",
            "fieldtype": "Link",
            "options": "Customer"
        },
        {
            "fieldname": "customer_group",
            "label": "Customer Group",
            "fieldtype": "Link",
            "options": "Customer Group"
        },
        {
            "fieldname": "icris",
            "label": "ICRIS",
            "fieldtype": "Link",
            "options": "ICRIS Account"
        },
        {
            "fieldname": "product",
            "label": "Product",
            "fieldtype": "Select",
            "options": "\nImport\nExport"
        },
        {
			"fieldname": "station",
			"label": "Station",
			"fieldtype": "Select",
			"options": [
				"",
				"Faisalabad",
				"Gujranwala",
				"Islamabad",
				"Karachi",
				"Lahore",
				"Peshawar",
				"Sialkot",
				"Wazirabad"
			].join("\n")
		}
		
    ]
};
