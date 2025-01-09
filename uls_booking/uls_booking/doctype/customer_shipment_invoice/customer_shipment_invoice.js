// Copyright (c) 2025, Sowaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customer Shipment Invoice", {
	refresh(frm) {
        frm.add_custom_button("Send Invoice Email", function() {
                        frappe.call({
                            method: "uls_booking.uls_booking.api.email.send_email_with_attachment",
                            args: { doc_name: frm.doc.name },  // Fix: Ensure doc_name is passed correctly
                            callback: function(response) {
                                if (response.message) {
                                    frappe.msgprint(response.message);
                                }
                            }
                        });
                    });
                },
	},
);
