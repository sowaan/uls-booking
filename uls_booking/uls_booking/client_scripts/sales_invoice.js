frappe.ui.form.on('Sales Invoice', {
    custom_selling_percentage(frm) {
        // Get the custom selling percentage value
        frm.set_value("custom_inserted", 1) ;
        const customPercentage = frm.doc.custom_selling_percentage;

        // Find the row with the item code "FCHG"
        const exportSaverItem = frm.doc.items.find(item => item.item_code === "FCHG");

        if (exportSaverItem) {
            // Get the original amount
            const originalAmount = exportSaverItem.amount; // Assuming 'amount' is the correct field
            
            // Calculate the discount amount based on the custom selling percentage
            const discountAmount = (originalAmount * customPercentage) / 100; // Calculate the discount
            frm.doc.custom_amount_after_discount = originalAmount - discountAmount;

            // Update the item directly in the items array
            frm.set_value("discount_amount", discountAmount);

            // Calculate rate
            const rate = originalAmount - discountAmount;

            // Fetch the percentage from the Additional Charges doctype
            // frappe.db.get_single_value("Additional Charges Page", "fuel_surcharge_percentages_on_freight_amount").then((percentage) => {
            //     console.log(percentage);  // Log the percentage value
            //     // Assuming total_fuel is defined somewhere in your form
            //     const total_fuel = frm.doc.custom_total_surcharges_incl_fuel; // Make sure this field exists

            //     // Calculate fsc_vv
            //     const fsc_vv = (rate + total_fuel) * percentage / 100;
            //     console.log('fsc', fsc_vv);

            //     // Find the row with the item code "FSC"
            //     const fscItem = frm.doc.items.find(item => item.item_code === "FSC");

            //     if (fscItem) {
            //         // Set the rate for the FSC item
            //         frappe.model.set_value("Sales Invoice Item", fscItem.name, "rate", fsc_vv);
            //         // Refresh the item table to reflect changes
            //         frm.refresh_field('items');
            //     } else {
            //         console.log("FSC item not found in the invoice items.");
            //     }
            // });

            // ############################ UMAIR WORK ############################
            frappe.call({
                method: "uls_booking.uls_booking.events.sales_invoice.get_fuel_percentage_for_date",
                args: {
                    date_shipped: frm.doc.custom_date_shipped
                },
                callback: function(r) {
                    const percentage = r.message;
                    console.log("Matched FSC percentage:", percentage);
            
                    const total_fuel = frm.doc.custom_total_surcharges_incl_fuel || 0;
                    // const rate = frm.doc.custom_base_freight_rate || 0;
            
                    const fsc_vv = (rate + total_fuel) * percentage / 100;
                    console.log("fsc_vv:", fsc_vv);
            
                    const fscItem = frm.doc.items.find(item => item.item_code === "FSC");
                    if (fscItem) {
                        frappe.model.set_value("Sales Invoice Item", fscItem.name, "rate", fsc_vv);
                        frm.refresh_field('items');
                    } else {
                        console.log("FSC item not found in the invoice items.");
                    }
                }
            });
            
        } else {
            console.log("Export Saver item not found in the invoice items.");
        }
    },
    custom_shipper_number(frm) {        
        get_icris_name(frm, "export", frm.doc.custom_shipper_number);
    },
    custom_consignee_number(frm) {
        get_icris_name(frm, "import", frm.doc.custom_consignee_number);
    }
    // customer: function(frm) {
    //     check_gst_exemption_and_clear_taxes(frm);
    // },
    // customer: function(frm) {
    //     if (!frm.doc.customer || !frm.doc.custom_duty_and_taxes_invoice) return;

    //     frappe.db.get_value("Customer", frm.doc.customer, "custom_exempt_gst")
    //         .then(r => {
    //             console.log(r.message.custom_exempt_gst);
    //             if (r.message.custom_exempt_gst) {
    //                 frm.set_value("taxes_and_charges", null);
    //                 frm.set_value("taxes", null);
    //             }
    //         });
    

    // },
    // refresh(frm) {
    //     if (
    //         frm.doc.custom_duty_and_taxes_invoice &&
    //         frm.doc.customer &&
    //         (
    //             frm.doc.taxes_and_charges ||
    //             (!frm.doc.taxes_and_charges && frm.doc.total_taxes_and_charges > 0)
    //         )
    //     )
    //     {
    //         frappe.db.get_value('Customer', frm.doc.customer, 'custom_exempt_gst')
    //             .then(r => {
    //                 if (r && r.message && r.message.custom_exempt_gst) {
    //                     frm.set_value("taxes_and_charges", null);
    //                     frm.set_value("taxes", null);
    //                 }
    //         });
    //     }
            
        
    // }
    // ,
    // reload(frm) {
    //     if (frm.doc.custom_duty_and_taxes_invoice)
    //         frm.set_value("taxes_and_charges", None);
    // }
    // ,
    // after_save: function(frm) {
    //     const cust_values = frappe.db.get_value("Customer", frm.doc.customer, ["custom_import_account_no", "custom_billing_type"], as_dict = true);
    //     if (cust_values.custom_import_account_no === frm.doc.custom_account_no && cust_values.custom_billing_type === frm.doc.custom_billing_type) {
    //         return;
    //     }else{
    //         frm.set_value("Customer", frm.doc.customer);
    //     }
    //         // frm.set_value("custom_import_account_no", cust_values.custom_import_account_no);
    // }
    // ,

    // async custom_insurance_amount(frm) {
    //     if (frm.doc.custom_insurance_amount) {
    //         const insured_amt = frm.doc.custom_insurance_amount;

    //         try {
    //             const response = await frappe.call({
    //                 method: "frappe.client.get",
    //                 args: {
    //                     doctype: "Additional Charges",
    //                     name: "Declare Value"
    //                 }
    //             });

    //             const declare = response.message;

    //             if (!declare) {
    //                 console.error("Declare Value document not found.");
    //                 return; // Exit if document is not found
    //             }

    //             const minimum = declare.minimum_amount;
    //             const percentage = declare.percentage;

    //             const after_perc = insured_amt * (percentage / 100);
    //             console.log(after_perc);

    //             if (after_perc > minimum) {
    //                 const INSITEM = frm.doc.items.find(item => item.item_code === "Ins");
    //                 if (INSITEM) {
    //                     frappe.model.set_value("Sales Invoice Item", INSITEM.name, "rate", after_perc);
    //                     console.log(INSITEM.rate);
    //                     frm.refresh_field("items");
    //                 } else {
    //                     console.error("INS item not found in items.");
    //                 }
    //             }
    //         } catch (error) {
    //             console.error("Error fetching Declare Value:", error);
    //         }
    //     }
    // },

    // custom_shipper_city: function(frm) {
    //     let shipper_city = frm.doc.custom_shipper_city;
    //     let shipper_country = frm.doc.custom_shipper_country; 
    //     if ( shipper_city && shipper_country == "PAKISTAN" ) {
    //         // Fetch territory based on shipper city
    //         frappe.call({
    //             method: 'frappe.client.get',
    //             args: {
    //                 doctype: 'Territory',
    //                 filters: { 'name': shipper_city }
    //             },
    //             callback: function(response) {
    //                 let territory = response.message;
                    
    //                 if (territory) {
    //                     let parent_territory = territory.parent_territory;

    //                     if (parent_territory && parent_territory !== "All Territories") {
    //                         // Fetch the 'custom_exempt_gst' from Customer doctype
    //                         frappe.call({
    //                             method: 'frappe.client.get_value',
    //                             args: {
    //                                 doctype: 'Customer',
    //                                 filters: { 'name': frm.doc.customer },
    //                                 fieldname: 'custom_exempt_gst'
    //                             },
    //                             callback: function(cust_response) {
    //                                 let exempt_customer = cust_response.message.custom_exempt_gst;

    //                                 // Proceed only if 'custom_exempt_gst' is 0
    //                                 if (exempt_customer == 0) {
    //                                     frappe.call({
    //                                         method: 'frappe.client.get',
    //                                         args: {
    //                                             doctype: 'Sales Taxes and Charges Template',
    //                                             filters: { 'custom_province': parent_territory }
    //                                         },
    //                                         callback: function(tax_response) {
    //                                             let tax_template = tax_response.message;

    //                                             if (tax_template) {
    //                                                 frm.set_value('taxes_and_charges', tax_template.name);
    //                                                 frm.clear_table('taxes');

    //                                                 $.each(tax_template.taxes, function(index, row) {
    //                                                     let new_row = frm.add_child('taxes');
    //                                                     new_row.charge_type = row.charge_type;
    //                                                     new_row.description = row.description;
    //                                                     new_row.account_head = row.account_head;
    //                                                     new_row.cost_center = row.cost_center;
    //                                                     new_row.rate = row.rate;
    //                                                     new_row.account_currency = row.account_currency;
    //                                                 });

    //                                                 frm.refresh_field('taxes');
    //                                             }
    //                                         }
    //                                     });
    //                                 }
    //                             }
    //                         });
    //                     }
    //                 }
    //             }
    //         });
    //     }
    // },

    // custom_consignee_city: function(frm) {
    //     let consignee_city = frm.doc.custom_consignee_city;
    //     let consignee_country = frm.doc.custom_consignee_country; 
    //     if ( consignee_city && consignee_country == "PAKISTAN" ) {
    //         // Fetch territory based on shipper city
    //         frappe.call({
    //             method: 'frappe.client.get',
    //             args: {
    //                 doctype: 'Territory',
    //                 filters: { 'name': consignee_city }
    //             },
    //             callback: function(response) {
    //                 let territory = response.message;
                    
    //                 if (territory) {
    //                     let parent_territory = territory.parent_territory;

    //                     if (parent_territory && parent_territory !== "All Territories") {
    //                         // Fetch the 'custom_exempt_gst' from Customer doctype
    //                         frappe.call({
    //                             method: 'frappe.client.get_value',
    //                             args: {
    //                                 doctype: 'Customer',
    //                                 filters: { 'name': frm.doc.customer },
    //                                 fieldname: 'custom_exempt_gst'
    //                             },
    //                             callback: function(cust_response) {
    //                                 let exempt_customer = cust_response.message.custom_exempt_gst;

    //                                 // Proceed only if 'custom_exempt_gst' is 0
    //                                 if (exempt_customer == 0) {
    //                                     frappe.call({
    //                                         method: 'frappe.client.get',
    //                                         args: {
    //                                             doctype: 'Sales Taxes and Charges Template',
    //                                             filters: { 'custom_province': parent_territory }
    //                                         },
    //                                         callback: function(tax_response) {
    //                                             let tax_template = tax_response.message;

    //                                             if (tax_template) {
    //                                                 frm.set_value('taxes_and_charges', tax_template.name);
    //                                                 frm.clear_table('taxes');

    //                                                 $.each(tax_template.taxes, function(index, row) {
    //                                                     let new_row = frm.add_child('taxes');
    //                                                     new_row.charge_type = row.charge_type;
    //                                                     new_row.description = row.description;
    //                                                     new_row.account_head = row.account_head;
    //                                                     new_row.cost_center = row.cost_center;
    //                                                     new_row.rate = row.rate;
    //                                                     new_row.account_currency = row.account_currency;
    //                                                 });

    //                                                 frm.refresh_field('taxes');
    //                                             }
    //                                         }
    //                                     });
    //                                 }
    //                             }
    //                         });
    //                     }
    //                 }
    //             }
    //         });
    //     }
    // }
        // else{
        //     frappe.msgprint("No Tax Template Found for this Territory");
        // }
    
});



// function check_gst_exemption_and_clear_taxes(frm) {
//     if (frm.doc.custom_duty_and_taxes_invoice && frm.doc.customer) {
//         frappe.db.get_value("Customer", frm.doc.customer, "custom_exempt_gst")
//             .then(r => {
//                 if (r.message.custom_exempt_gst) {
//                     // Clear tax fields
//                     frm.set_value("taxes_and_charges", null);
//                     frm.clear_table("taxes");

//                     frm.set_value("total_taxes_and_charges", 0);
//                     frm.set_value("base_total_taxes_and_charges", 0);

//                     frm.set_value("grand_total", frm.doc.net_total);
//                     frm.set_value("base_grand_total", frm.doc.base_net_total);

//                     // Optional: Update in_words manually if needed
//                     frappe.call({
//                         method: "uls_booking.uls_booking.events.sales_invoice.get_money_in_words",
//                         args: {
//                             amount: frm.doc.grand_total,
//                             currency: frm.doc.currency
//                         },
//                         callback: function(response) {
//                             frm.set_value("in_words", response.message);
//                         }
//                     });

//                     frm.refresh_fields();
//                 }
//             });
//     }
// }


function get_icris_name(frm, imp_exp, cond) {
    console.log("get_icris_name called with imp_exp:", imp_exp, "and cond:", cond, "for doc imp exp:", frm.doc.custom_import__export_si?.toLowerCase());
    if (frm.doc.custom_freight_invoices && frm.doc.custom_import__export_si?.toLowerCase() === imp_exp) {
        frappe.db.get_value("Sales Invoice Definition", frm.doc.custom_sales_invoice_definition, "unassigned_icris_number")
            .then(def_res => {
                if (!def_res.message) return;

                const unassigned_icris_number = def_res.message.unassigned_icris_number;

                frappe.db.get_value("ICRIS Account", unassigned_icris_number, "shipper_name")
                    .then(unassigned_res => {
                        const fallback_name = unassigned_res.message ? unassigned_res.message.shipper_name : "";

                        if (cond) {
                            frappe.db.get_value("ICRIS Account", cond, "shipper_name")
                                .then(r => {
                                    if (r.message) {
                                        frm.set_value("customer", r.message.shipper_name);
                                    } else {
                                        frm.set_value("customer", fallback_name);
                                    }
                                });
                        } else {
                            frm.set_value("customer", fallback_name);
                        }
                    });
            });
    }
}

