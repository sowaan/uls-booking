frappe.ui.form.on('Payment Entry', {
    party: function (frm) {
        if (frm.doc.custom_sales_invoice_pdf_ref) {
            frm.set_value('custom_sales_invoice_pdf_ref', null);
            frm.set_value('custom_customer_invoice', null);
        }
    },

    custom_get_pdf_outstanding_invoices: function (frm) {
        let d = new frappe.ui.Dialog({
            title: 'Select Sales Invoice PDF',
            fields: [
                {
                    label: 'Sales Invoice PDF',
                    fieldname: 'message',
                    fieldtype: 'MultiSelectList',
                    reqd: 1,
                    get_data: function (txt) {
                        if (!frm.doc.party || frm.doc.party_type !== 'Customer') {
                            return [];
                        }

                        return frappe.call({
                            method: 'uls_booking.uls_booking.api.api.get_outstanding_sales_invoice_pdf_options',
                            args: {
                                party: frm.doc.party,
                                txt: txt || ''
                            }
                        }).then((r) => r.message || []);
                    }
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
                    freeze: true,
                    freeze_message: __("Fetching outstanding invoices..."),
                    callback: function (r) {
                        let selected_pdfs = Array.isArray(values.message)
                            ? values.message
                            : (values.message ? [values.message] : []);
                        let pdf_ref_value = selected_pdfs.length === 1 ? selected_pdfs[0] : null;
                        let emp_id = r.message ? r.message.emp_id : '';

                        frm.set_value('custom_sales_invoice_pdf_ref', pdf_ref_value || null);
                        frm.set_value('custom_customer_invoice', emp_id || null);

                        if (r.message && r.message.invoices && r.message.invoices.length > 0) {
                            let invoices = r.message.invoices;
    
                            let remaining = frm.doc.payment_type === 'Receive'
                                ? flt(frm.doc.paid_amount)
                                : flt(frm.doc.received_amount);
    
                            let total_allocated = 0;
                            let total_positive_outstanding = 0;
                            let total_negative_outstanding = 0;
                            let company_currency = frappe.defaults.get_default("currency");
    
                            invoices.forEach(inv => {
                                let to_allocate = 0;
                                if (remaining > 0) {
                                    to_allocate = Math.min(remaining, flt(inv.outstanding_amount));
                                    remaining -= to_allocate;
                                }
    
                                total_allocated += to_allocate;
    
                                frm.add_child("references", {
                                    reference_doctype: inv.voucher_type,
                                    reference_name: inv.voucher_no,
                                    due_date: inv.due_date,
                                    total_amount: inv.invoice_amount,
                                    outstanding_amount: inv.outstanding_amount,
                                    allocated_amount: to_allocate,
                                    bill_no: inv.bill_no,
                                    account: inv.account,
                                    payment_term: inv.payment_term,
                                    payment_term_outstanding: inv.payment_term_outstanding,
                                    exchange_rate: inv.exchange_rate || 1
                                });
    
                                if (flt(inv.outstanding_amount) > 0)
                                    total_positive_outstanding += flt(inv.outstanding_amount);
                                else
                                    total_negative_outstanding += Math.abs(flt(inv.outstanding_amount));
                            });
    
                            frm.refresh_field("references");
                            frm.set_value("base_total_allocated_amount", total_allocated);
    
                            if (
                                (frm.doc.payment_type === "Receive" && frm.doc.party_type === "Customer") ||
                                (frm.doc.payment_type === "Pay" && ["Supplier", "Employee"].includes(frm.doc.party_type))
                            ) {
                                if (total_positive_outstanding > total_negative_outstanding && !frm.doc.paid_amount) {
                                    frm.set_value("paid_amount", total_positive_outstanding - total_negative_outstanding);
                                }
                            } else if (
                                total_negative_outstanding &&
                                total_positive_outstanding < total_negative_outstanding &&
                                !frm.doc.received_amount
                            ) {
                                frm.set_value("received_amount", total_negative_outstanding - total_positive_outstanding);
                            }
    
                            frm.events.allocate_party_amount_against_ref_docs(
                                frm,
                                frm.doc.payment_type === "Receive" ? frm.doc.paid_amount : frm.doc.received_amount,
                                false
                            );
    
                        } else {
                            frm.refresh_field("references");
                            frappe.msgprint(__('No outstanding PDF Invoices found for {0}.', [frm.doc.party]));
                        }
    
                        d.hide();
                    }
                });
            }
        });
    
        d.show();
    },
    

    allocate_party_amount_against_ref_docs: async function (frm, paid_amount, paid_amount_change) {
		await frm.call("allocate_amount_to_references", {
			paid_amount: paid_amount,
			paid_amount_change: paid_amount_change,
			allocate_payment_amount: frappe.flags.allocate_payment_amount ?? false,
		});

		frm.events.set_total_allocated_amount(frm);
	},
    set_total_allocated_amount: function (frm) {
		let exchange_rate = 1;
		if (frm.doc.payment_type == "Receive") {
			exchange_rate = frm.doc.source_exchange_rate;
		} else if (frm.doc.payment_type == "Pay") {
			exchange_rate = frm.doc.target_exchange_rate;
		}
		var total_allocated_amount = 0.0;
		var base_total_allocated_amount = 0.0;
		$.each(frm.doc.references || [], function (i, row) {
			if (row.allocated_amount) {
				total_allocated_amount += flt(row.allocated_amount);
				base_total_allocated_amount += flt(
					flt(row.allocated_amount) * flt(exchange_rate),
					precision("base_paid_amount")
				);
			}
		});
		frm.set_value("total_allocated_amount", Math.abs(total_allocated_amount));
		frm.set_value("base_total_allocated_amount", Math.abs(base_total_allocated_amount));

		frm.events.set_unallocated_amount(frm);
	},
    set_unallocated_amount: function (frm) {
		let unallocated_amount = 0;
		let deductions_to_consider = 0;

		for (const row of frm.doc.deductions || []) {
			if (!row.is_exchange_gain_loss) deductions_to_consider += flt(row.amount);
		}
		const included_taxes = get_included_taxes(frm);

		if (frm.doc.party) {
			if (
				frm.doc.payment_type == "Receive" &&
				frm.doc.base_total_allocated_amount < frm.doc.base_paid_amount + deductions_to_consider
			) {
				unallocated_amount =
					(frm.doc.base_paid_amount +
						deductions_to_consider -
						frm.doc.base_total_allocated_amount -
						included_taxes) /
					frm.doc.source_exchange_rate;
			} else if (
				frm.doc.payment_type == "Pay" &&
				frm.doc.base_total_allocated_amount < frm.doc.base_received_amount - deductions_to_consider
			) {
				unallocated_amount =
					(frm.doc.base_received_amount -
						deductions_to_consider -
						frm.doc.base_total_allocated_amount -
						included_taxes) /
					frm.doc.target_exchange_rate;
			}
		}
		frm.set_value("unallocated_amount", unallocated_amount);
		frm.trigger("set_difference_amount");
	},

	set_difference_amount: function (frm) {
		var difference_amount = 0;
		var base_unallocated_amount =
			flt(frm.doc.unallocated_amount) *
			(frm.doc.payment_type == "Receive" ? frm.doc.source_exchange_rate : frm.doc.target_exchange_rate);

		var base_party_amount = flt(frm.doc.base_total_allocated_amount) + base_unallocated_amount;

		if (frm.doc.payment_type == "Receive") {
			difference_amount = base_party_amount - flt(frm.doc.base_received_amount);
		} else if (frm.doc.payment_type == "Pay") {
			difference_amount = flt(frm.doc.base_paid_amount) - base_party_amount;
		} else {
			difference_amount = flt(frm.doc.base_paid_amount) - flt(frm.doc.base_received_amount);
		}

		var total_deductions = frappe.utils.sum(
			$.map(frm.doc.deductions || [], function (d) {
				return flt(d.amount);
			})
		);

		frm.set_value(
			"difference_amount",
			difference_amount - total_deductions + flt(frm.doc.base_total_taxes_and_charges)
		);

		frm.events.hide_unhide_fields(frm);
	},

	unallocated_amount: function (frm) {
		frm.trigger("set_difference_amount");
	}
});

function get_included_taxes(frm) {
	let included_taxes = 0;
	for (const tax of frm.doc.taxes) {
		if (!tax.included_in_paid_amount) continue;

		if (tax.add_deduct_tax == "Add") {
			included_taxes += tax.base_tax_amount;
		} else {
			included_taxes -= tax.base_tax_amount;
		}
	}

	return included_taxes;
}
