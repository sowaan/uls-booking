frappe.ui.form.on('Payment Entry', {
    custom_get_outstanding_pdf_invoices: function (frm) {
        let d = new frappe.ui.Dialog({
            title: 'Select Sales Invoice PDF',
            fields: [
                {
                    label: 'Sales Invoice PDF',
                    fieldname: 'message',
                    fieldtype: 'Link',
                    options: 'Sales Invoice PDF',
                    reqd: 1,
                    get_query: () => ({
                        filters: {
                            docstatus: 1
                        }
                    })
                }
            ],
            primary_action_label: 'Get Invoices',
            primary_action(values) {
                if (!frm.doc.party || frm.doc.party_type !== 'Customer') {
                    frappe.msgprint('Please select a Customer first.');
                    return;
                }

                frm.clear_table('references');

                frappe.call({
                    method: 'uls_booking.uls_booking.api.api.get_outstanding_pdf_invoices',
                    args: {
                        party: frm.doc.party,
                        sales_invoice_pdf: values.message
                    },
                    callback: function (r) {
                        if (r.message && r.message.length > 0) {
                            r.message.forEach(d => {
                                const c = frm.add_child("references", {
                                    reference_doctype: d.voucher_type,
                                    reference_name: d.voucher_no,
                                    due_date: d.due_date,
                                    total_amount: d.invoice_amount,
                                    outstanding_amount: d.outstanding_amount,
                                    allocated_amount: d.allocated_amount,
                                    bill_no: d.bill_no,
                                    account: d.account,
                                    payment_term: d.payment_term,
                                    payment_term_outstanding: d.payment_term_outstanding,
                                    exchange_rate: d.exchange_rate || 1
                                });
                            });

                            frm.refresh_field("references");
                            // let total_allocated = frm.doc.references.reduce((sum, row) => {
                            //     return sum + flt(row.allocated_amount);
                            // }, 0);

                            // frm.set_value("base_total_allocated_amount", total_allocated);

                            // if (frm.doc.payment_type === "Receive") {
                            //     frm.set_value("paid_amount", total_allocated);
                            // } else if (frm.doc.payment_type === "Pay") {
                            //     frm.set_value("received_amount", total_allocated);
                            // }

                        } else {
                            frappe.msgprint('No outstanding PDF Invoices found for the selected customer.');
                        }

                        d.hide();
                    }
                });
            }
        });

        d.show();
    }
});
