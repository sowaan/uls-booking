// Copyright (c) 2024, fariz and contributors
// For license information, please see license.txt



frappe.ui.form.on('Manifest Upload Data', {
    manifest_modification_process: function (frm) {
        if (frm.doc.manifest_modification_process == 1) {
            frm.set_value("date_format", "%Y-%m-%d");
        }
        else{
            frm.set_value("date_format", "%d%b%Y");
        }
    },


    opsys_upload_data: function(frm){
        if (frm.doc.opsys_upload_data == 1){
            frm.set_value("date_format","%d%b%Y")
        }
        else{
            frm.set_value("date_format", "%d%b%Y");
        }
    }
});


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