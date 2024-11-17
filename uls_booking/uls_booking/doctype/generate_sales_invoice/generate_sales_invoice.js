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

            let count = 0;
            
            // Loop through the rows in the child table
            frm.doc.shipment_numbers_and_sales_invoices.forEach(function(row) {
                if (row.sales_invoice) {
                    count++;  // Increment the counter if sales_invoice is set
                }
            });
            console.log(count)
            frm.set_value('total_sales_invoices_generated', count)
            // frm.save()
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
