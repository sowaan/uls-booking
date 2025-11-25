frappe.query_reports["Invoice-wise Sales Tax"] = {
    "filters": [
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
            reqd: 0
        },
        {
            fieldname: "icris_number",
            label: __("ICRIS Number"),
            fieldtype: "Link",
            options: "ICRIS List",
            reqd: 0
        },
        {
            fieldname: "date_type",
            label: __("Date Type"),
            fieldtype: "Select",
            options: "\nPosting Date\nShipped Date\nImport Date\nArrival Date",
            reqd: 0,
            default: "Posting Date"
        },
        {
            fieldname: "date",
            label: __("Date"),
            fieldtype: "Date",
            reqd: 0
        },
        {
            fieldname: "import_export",
            label: __("Import / Export"),
            fieldtype: "Select",
            options: "\nImport\nExport",
            reqd: 0
        }
    ]
};
