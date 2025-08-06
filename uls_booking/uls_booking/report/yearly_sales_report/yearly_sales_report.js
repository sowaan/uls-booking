frappe.query_reports["Yearly Sales Report"] = {
    filters: [
        {
            fieldname: "sales_person",
            label: "Sales Person",
            fieldtype: "Link",
            options: "Sales Person"
        },
        {
            fieldname: "quarter",
            label: "Quarter",
            fieldtype: "Select",
            options: ["", "1st", "2nd", "3rd", "4th"].join("\n"),
            reqd: 1
        },
        {
            fieldname: "year",
            label: "Year",
            fieldtype: "Select",
            options: [],
            default: (new Date()).getFullYear().toString(),
            reqd: 1
        },
        {
            fieldname: "customer",
            label: "Customer",
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "customer_group",
            label: "Customer Group",
            fieldtype: "Link",
            options: "Customer Group"
        },
        {
            fieldname: "icris",
            label: "ICRIS",
            fieldtype: "Link",
            options: "ICRIS Account"
        },
        {
            fieldname: "product",
            label: "Product",
            fieldtype: "Select",
            options: ["", "Import", "Export"].join("\n")
        },
        {
            fieldname: "station",
            label: "Station",
            fieldtype: "Select",
            options: [
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
    ],

    onload: function(report) {
		const currentYear = (new Date()).getFullYear();
		const yearFilter = report.get_filter("year");

		if (yearFilter) {
			const years = [];
			for (let year = currentYear; year >= 2000; year--) {
				years.push(year.toString());
			}
			yearFilter.df.options = years.join('\n');
			yearFilter.refresh();
		}
	}

};
