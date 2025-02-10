frappe.ui.form.on('Sales Invoice', {
    custom_selling_percentage(frm) {
        // Get the custom selling percentage value
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
            frappe.db.get_single_value("Additional Charges Page", "feul_surcharge_percentage_on_freight_amount").then((percentage) => {
                console.log(percentage);  // Log the percentage value
                // Assuming total_fuel is defined somewhere in your form
                const total_fuel = frm.doc.custom_total_surcharges_incl_fuel; // Make sure this field exists

                // Calculate fsc_vv
                const fsc_vv = (rate + total_fuel) * percentage / 100;

                // Find the row with the item code "FSC"
                const fscItem = frm.doc.items.find(item => item.item_code === "FSC");

                if (fscItem) {
                    // Set the rate for the FSC item
                    frappe.model.set_value("Sales Invoice Item", fscItem.name, "rate", fsc_vv);
                    // Refresh the item table to reflect changes
                    frm.refresh_field('items');
                } else {
                    console.log("FSC item not found in the invoice items.");
                }
            });
        } else {
            console.log("Export Saver item not found in the invoice items.");
        }
    },

    async custom_insurance_amount(frm) {
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

                if (!declare) {
                    console.error("Declare Value document not found.");
                    return; // Exit if document is not found
                }

                const minimum = declare.minimum_amount;
                const percentage = declare.percentage;

                const after_perc = insured_amt * (percentage / 100);
                console.log(after_perc);

                if (after_perc > minimum) {
                    const INSITEM = frm.doc.items.find(item => item.item_code === "Ins");
                    if (INSITEM) {
                        frappe.model.set_value("Sales Invoice Item", INSITEM.name, "rate", after_perc);
                        console.log(INSITEM.rate);
                        frm.refresh_field("items");
                    } else {
                        console.error("INS item not found in items.");
                    }
                }
            } catch (error) {
                console.error("Error fetching Declare Value:", error);
            }
        }
    }
});
