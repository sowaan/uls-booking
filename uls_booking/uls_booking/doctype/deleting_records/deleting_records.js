// Copyright (c) 2025, Sowaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Deleting Records", {
	delete_sales_invoice_links(frm) {
        frappe.call({
            method: "uls_booking.uls_booking.doctype.deleting_records.deleting_records.delete_sales_invoice_links",
            args: {
                docname: frm.doc.name,
            },
            callback: function (r) {
                if (r.message) {
                    frappe.show_alert({
                        message: __("Sales Invoice links deleted successfully."),
                        indicator: "green",
                    });
                } else {
                    frappe.show_alert({
                        message: __("No Sales Invoice links found to delete."),
                        indicator: "red",
                    });
                }
            },
        });
	},
});
