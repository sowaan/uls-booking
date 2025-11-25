// Copyright (c) 2024, fariz and contributors
// For license information, please see license.txt



frappe.ui.form.on('Manifest Upload Data', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status) {
            frm.page.set_indicator(frm.doc.status, {
                "Started": "orange",
                "Completed": "green",
                "Failed": "red",
                "Draft": "gray"
            }[frm.doc.status]);
        }

        if (frm.doc.docstatus === 1 && frm.doc.failed_shipments > 0 && (frm.doc.status === "Failed" || frm.doc.status === "Completed")) {
        //if (frm.doc.docstatus === 1 && (frm.doc.status === "Failed" || frm.doc.status === "Completed")) {
            frm.add_custom_button(
                __('Reprocess Shipments'),
                function() {
                    frappe.call({
                        method: "uls_booking.uls_booking.doctype.manifest_upload_data.manifest_upload_data.reprocess_shipments",
                        args: { docname: frm.doc.name },
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                            }
                        }
                    });
                }
            ).addClass('btn-primary');

        }

    },
    // manifest_modification_process: function (frm) {
    //     if (frm.doc.manifest_modification_process == 1) {
    //         frm.set_value("date_format", "%Y-%m-%d");
    //     }
    //     else{
    //         frm.set_value("date_format", "%d%b%Y");
    //     }
    // },


    // opsys_upload_data: function(frm){
    //     if (frm.doc.opsys_upload_data == 1){
    //         frm.set_value("date_format","%d%b%Y")
    //     }
    //     else{
    //         frm.set_value("date_format", "%d%b%Y");
    //     }
    // },

    manifest_file_type: function(frm){
        if (frm.doc.manifest_file_type == "DWS"){
            frm.set_value("date_format", "%Y-%m-%d");
        }
        else if (frm.doc.manifest_file_type == "OPSYS"){
            frm.set_value("date_format","%d%b%Y")
        }

        else if (frm.doc.manifest_file_type == "ISPS"){
            frm.set_value("date_format", "%d%b%Y");
        }
    },

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