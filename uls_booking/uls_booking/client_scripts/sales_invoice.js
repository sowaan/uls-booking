let INS = "INS";
let FSC = "FSC";
let FCHG = "FCHG";

async function load_manifest_codes() {
    const res = await frappe.db.get_value("Manifest Setting Definition", null, [
        "insurance_charges", "fuel_charges", "freight_charges"
    ]);
    if (res && res.message) {
        INS = res.message.insurance_charges || "INS";
        FSC = res.message.fuel_charges || "FSC";
        FCHG = res.message.freight_charges || "FCHG";
    }
}

frappe.ui.form.on('Sales Invoice', {

    async custom_selling_percentage(frm) {
        await load_manifest_codes();

        frm.set_value("custom_inserted", 1);
        const customPercentage = frm.doc.custom_selling_percentage;

        const exportSaverItem = frm.doc.items.find(item => item.item_code === FCHG);

        if (exportSaverItem) {
            const originalAmount = exportSaverItem.amount;
            const discountAmount = (originalAmount * customPercentage) / 100;
            frm.set_value("custom_amount_after_discount",  originalAmount - discountAmount);
            frm.set_value("discount_amount", discountAmount);

            frappe.call({
                method: "uls_booking.uls_booking.events.sales_invoice.get_fuel_percentage_for_date",
                args: {
                    date_shipped: frm.doc.custom_date_shipped
                },
                callback: function(r) {
                    const percentage = r.message;
                    const total_fuel = frm.doc.custom_total_surcharges_incl_fuel || 0;
                    const fsc_vv = (frm.doc.custom_amount_after_discount + total_fuel) * percentage / 100;

                    const fscItem = frm.doc.items.find(item => item.item_code === FSC);
                    if (fscItem) {
                        frappe.model.set_value("Sales Invoice Item", fscItem.name, "rate", fsc_vv);
                        frm.refresh_field('items');
                    } else {
                        console.log("FSC item not found.");
                    }
                }
            });

        } else {
            console.log(`${FCHG} item not found.`);
        }
    },

    async custom_insurance_amount(frm) {
        await load_manifest_codes();

        if (frm.doc.custom_insurance_amount) {
            const insured_amt = frm.doc.custom_insurance_amount;

            try {
                const response = await frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Additional Charges",
                        name: "Declare Value"
                    }
                });

                const declare = response.message;
                if (!declare) return;

                const minimum = declare.minimum_amount;
                const percentage = declare.percentage;
                const after_perc = insured_amt * (percentage / 100);

                if (after_perc > minimum) {
                    const INSITEM = frm.doc.items.find(item => item.item_code === INS);
                    if (INSITEM) {
                        frappe.model.set_value("Sales Invoice Item", INSITEM.name, "rate", after_perc);
                        frm.refresh_field("items");
                    } else {
                        console.error(`${INS} item not found.`);
                    }
                }
            } catch (error) {
                console.error("Error fetching Declare Value:", error);
            }
        }
    },

    custom_shipper_number(frm) {
        get_icris_name(frm, "export", frm.doc.custom_shipper_number);
    },

    custom_consignee_number(frm) {
        get_icris_name(frm, "import", frm.doc.custom_consignee_number);
    }
});

// frappe.ui.form.on('Sales Invoice', {
//     custom_selling_percentage(frm) {
//         frm.set_value("custom_inserted", 1);

//         const customPercentage = frm.doc.custom_selling_percentage;
//         const exportSaverItem = frm.doc.items.find(item => item.item_code === "FCHG");

//         if (!exportSaverItem) {
//             console.log("Export Saver item not found.");
//             return;
//         }

//         const originalAmount = exportSaverItem.amount;
//         const discountAmount = (originalAmount * customPercentage) / 100;
//         const reducedAmount = originalAmount - discountAmount;

//         frm.set_value("custom_amount_after_discount", reducedAmount);

//         // ✅ Use ERPNext's standard field for invoice-wide discount
//         frm.set_value("additional_discount_percentage", customPercentage);
//         frappe.ui.form.trigger("additional_discount_percentage");

//         // ✅ Continue with FSC update
//         frappe.call({
//             method: "uls_booking.uls_booking.events.sales_invoice.get_fuel_percentage_for_date",
//             args: {
//                 date_shipped: frm.doc.custom_date_shipped
//             },
//             callback: function(r) {
//                 const percentage = r.message;
//                 const total_fuel = frm.doc.custom_total_surcharges_incl_fuel || 0;
//                 const fsc_base = reducedAmount + total_fuel;
//                 const fsc_vv = (fsc_base * percentage) / 100;

//                 const fscItem = frm.doc.items.find(item => item.item_code === "FSC");
//                 if (fscItem) {
//                     frappe.model.set_value("Sales Invoice Item", fscItem.name, "rate", fsc_vv);
//                     frm.refresh_field('items');
//                 } else {
//                     console.log("FSC item not found in the invoice items.");
//                 }
//             }
//         });
//     },
//     custom_shipper_number(frm) {        
//         get_icris_name(frm, "export", frm.doc.custom_shipper_number);
//     },
//     custom_consignee_number(frm) {
//         get_icris_name(frm, "import", frm.doc.custom_consignee_number);
//     }
// });


function get_icris_name(frm, imp_exp, cond) {
    if (frm.doc.custom_freight_invoices && frm.doc.custom_import__export_si?.toLowerCase() === imp_exp) {
        frappe.db.get_value("Sales Invoice Definition", frm.doc.custom_sales_invoice_definition, "unassigned_icris_number")
            .then(def_res => {
                if (!def_res.message) return;

                const unassigned_icris_number = def_res.message.unassigned_icris_number;

                frappe.db.get_value("ICRIS Account", unassigned_icris_number, "shipper_name")
                    .then(unassigned_res => {
                        const fallback_name = unassigned_res.message ? unassigned_res.message.shipper_name : "";
                        if (cond) {
                            frappe.db.get_doc("ICRIS Account", cond)
                                .then(doc => {
                                    if (doc && doc.shipper_name) {
                                        frm.set_value("customer", doc.shipper_name);
                                    } else {
                                        frm.set_value("customer", fallback_name);
                                    }
                                })
                                .catch(err => {
                                    console.log("Error fetching ICRIS Account:", err);
                                    frm.set_value("customer", fallback_name);
                                });
                        } else {
                            frm.set_value("customer", fallback_name);
                        }
                    });
            });
    }
}

