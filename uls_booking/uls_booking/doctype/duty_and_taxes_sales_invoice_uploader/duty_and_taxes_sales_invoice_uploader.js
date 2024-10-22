// Copyright (c) 2024, Sowaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Duty and Taxes Sales Invoice Uploader", {
	
    refresh(frm) 
    {
        $('button.btn.btn-xs.btn-secondary.grid-add-row').eq(0).hide();
	},

    onload(frm)
    {
        $('button.btn.btn-xs.btn-secondary.grid-add-row').eq(0).hide();
    },



});
