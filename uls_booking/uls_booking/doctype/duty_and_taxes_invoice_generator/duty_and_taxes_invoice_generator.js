// Copyright (c) 2024, Sowaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Duty and Taxes Invoice Generator", {
	
    refresh(frm) 
    {
        $('button.btn.btn-xs.btn-secondary.grid-add-row').eq(0).hide();

        if (frm.doc.docstatus == 1 && frm.doc.all_sales_invoice_created != 1)
        {
            frm.add_custom_button('Sales Invoices', () => {
                console.log("Create Sales Invoies");
                // frm.create_sales_invoices();
                
                frappe.call({
                    method: "uls_booking.uls_booking.doctype.duty_and_taxes_invoice_generator.duty_and_taxes_invoice_generator.create_sales_invoices",
                    args: {
                        rec_name : frm.doc.name ,
                    },
                    callback: function (r) {
                        if (!r.exc) {
                            frm.reload_doc();
                        }
                    }
                });
            },'Create')
        }


        if (frm.doc.docstatus == 1 && frm.doc.purchase_invoice_created != 1)
        {
            frm.add_custom_button('Purchase Invoice', () => {
                console.log("Create Purchase Invoice");
                frappe.call({
                    method: "uls_booking.uls_booking.doctype.duty_and_taxes_invoice_generator.duty_and_taxes_invoice_generator.create_purchase_invoice",
                    args: {
                        rec_name : frm.doc.name ,
                    },
                    callback: function (r) {
                        if (!r.exc) {
                            frm.reload_doc();
                        }
                    }
                });
            },'Create')
        }

	},

    onload(frm)
    {
        $('button.btn.btn-xs.btn-secondary.grid-add-row').eq(0).hide();
    },



});
