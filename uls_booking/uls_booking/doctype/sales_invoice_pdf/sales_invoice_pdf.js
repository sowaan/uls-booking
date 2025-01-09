// Copyright (c) 2024, Sowaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice PDF", {
    refresh(frm) {
        // Hide Add Row and Delete button in the child table
        frm.fields_dict["customer_with_sales_invoice"].grid.wrapper.find('.grid-add-row').hide();
        frm.fields_dict["customer_with_sales_invoice"].grid.wrapper.find('.grid-remove-rows').hide();

        if (frm.doc.docstatus !== 1) {
            return;  // Exit if docstatus is not 1
        }

        frm.add_custom_button("Send Sales Invoice Email", function() {
            let selected_customers = [];

            (frm.fields_dict["customer_with_sales_invoice"].grid.get_selected_children() || []).forEach(row => {
                if (row.customer) {
                    selected_customers.push(row.customer);
                }
            });

            if (selected_customers.length === 0) {
                frappe.msgprint(__("Please select at least one row."));
                return;
            }

            frappe.call({
                method: "uls_booking.uls_booking.api.email.send_multi_email_with_attachment",
                args: { 
                    doc_name: frm.doc.name, 
                    selected_customers: JSON.stringify(selected_customers) 
                },
                callback: function(response) {
                    if (response.message) {
                        frappe.msgprint(response.message);
                    }
                }
            });
        });
    }
});

