frappe.query_reports["Sales Invoice Summary"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "customer",
            label: "Customer",
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "custom_shipment_number",
            label: "Shipment Number",
            fieldtype: "Data"
        }
    ]
};

