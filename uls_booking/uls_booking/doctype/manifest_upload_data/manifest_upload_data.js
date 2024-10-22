// Copyright (c) 2024, fariz and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Manifest Upload Data', {
//     refresh: function (frm) {

//         if (frm.doc.docstatus == 1) {
//             // Add a custom button to the form
//             frm.add_custom_button(__('Generate Sales Invoice'), function () {
//                 // Show a message when the button is clicked
              
//                 frappe.call({
//                     method: "uls_booking.uls_booking.doctype.manifest_upload_data.manifest_upload_data.generate_sales_invoice",
//                     args: { doc_str: frm.doc },
//                     freeze : true ,

//                 });
            
//             });
//         }

//     },





//     on_submit: function (frm) {
//         // Reload the entire document after submission
//         frm.reload_doc();
//     },

//     shipment_numbers: function (frm) {
//         // Optional: Reload the form whenever 'shipment_numbers' changes
//         // This might not be needed if on_submit is already handling it
//         frm.reload_doc();
//     }
// });