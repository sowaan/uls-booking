// Copyright (c) 2024, Sowaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Generate Sales Invoice", {
	refresh(frm) {
        
        if (frm.doc.docstatus == 1) {
            // Add a custom button to the form
            frm.add_custom_button(__('Generate Sales Invoice'), function () {
                // Show a message when the button is clicked
                
                frappe.call({
                    method: "uls_booking.uls_booking.doctype.manifest_upload_data.manifest_upload_data.generate_sales_invoice",
                    args: { doc_str: frm.doc },
                    freeze : true ,

                });
            
            });
        }

        // if (frm.doc.docstatus == 1) {
        //     // Add a custom button to the form
        //     frm.add_custom_button(__('Reload'), function () {
        //         frappe.call({
        //             method: "uls_booking.uls_booking.doctype.manifest_upload_data.manifest_upload_data.generate_sales_invoice",
        //             args: { doc_str: frm.doc },
        //             freeze : true ,

        //         });
            
        //     });
        // }
        
	},
    on_submit(frm) {
        
        frm.reload_doc();
    },

    shipment_numbers(frm) {
       
        frm.reload_doc();
    },
    sales_invoices(frm) {
       
        frm.reload_doc();
    }
});
