frappe.ui.form.on('Shipment Master Details', {
    master_package_id: async function (frm) {
        await get_records(frm);
    }
});







async function get_records(frm) {
    const tracking_number = frm.doc.master_package_id;

    // if (!tracking_number) {
    //     frappe.msgprint(__('Please enter a Master Package ID.'));
    //     return;
    // }

    try {
        // Fetch R200000 records
        const r2 = await frappe.db.get_list('R200000', {
            filters: {
                'custom_package_tracking_number': tracking_number
            },
            fields: [
                "shipment_number", "origin_country", "shipped_date", "shipment_type",
                "bill_term_surcharge_indicator", "split_duty_and_vat_flag",
                "shipment_weight", "destination_country", "import_date",
                "billing_term_field", "terms_of_shipment", "shipment_weight_unit",
                "number_of_packages_in_shipment"
            ]
        });

        if (r2 && r2.length > 0) {
            const record = r2[0];
            frm.set_value('shipment_number', record.shipment_number);
            frm.set_value('origin_country', record.origin_country);
            frm.set_value('date_shipped', record.shipped_date);
            frm.set_value('shipment_type', record.shipment_type);
            frm.set_value('bill_term_surcharge_indicator', record.bill_term_surcharge_indicator);
            frm.set_value('split_duty_and_vat_flag', record.split_duty_and_vat_flag);
            frm.set_value('split_duty_and_vat_flag_master', record.split_duty_and_vat_flag);
            frm.set_value('shipment_weight', record.shipment_weight);
            frm.set_value('destination_country', record.destination_country);
            frm.set_value('import_date', record.import_date);
            frm.set_value('billing_term', record.billing_term_field);
            frm.set_value('terms_of_shipment', record.terms_of_shipment);
            frm.set_value('shipment_weight_unit', record.shipment_weight_unit);
            frm.set_value('number_of_packages_in_shipment', record.number_of_packages_in_shipment);

            // Fetch R201000 record based on shipment number
            const r21 = await frappe.db.get_value('R201000', {'shipment_number': record.shipment_number}, 'custom_minimum_bill_weight');
            if (r21.message) {
                frm.set_value('billable_weight', r21.message.custom_minimum_bill_weight);
            } else {
                frappe.msgprint(__('No R201000 record on this Shipment number: [{0}]', [record.shipment_number]));
            }

            // Fetch R300000 records based on shipment number
            const r3 = await frappe.db.get_list('R300000', {
                filters: {
                    'shipment_number': record.shipment_number
                },
                fields: [
                    'shipper_number', 'shipper_contact_name', 'shipper_street',
                    'shipper_country', 'shipper_postal_code', 'shipper_name',
                    'shipper_building', 'shipper_city'
                ]
            });
            if (r3 && r3.length > 0) {
                const shipper = r3[0];
                frm.set_value('shipper_number', shipper.shipper_number);
                frm.set_value('shipper_contact_name', shipper.shipper_contact_name);
                frm.set_value('shipper_street', shipper.shipper_street);
                frm.set_value('shipper_country', shipper.shipper_country);
                frm.set_value('shipper_postal_code', shipper.shipper_postal_code);
                frm.set_value('shipper_name', shipper.shipper_name);
                frm.set_value('shipper_building', shipper.shipper_building);
                frm.set_value('shipper_city', shipper.shipper_city);
            } else {
                frappe.msgprint(__('No R300000 record on this Shipment number: [{0}]', [record.shipment_number]));
            }

            // Fetch R400000 records based on shipment number
            const r4 = await frappe.db.get_list('R400000', {
                filters: {
                    'shipment_number': record.shipment_number
                },
                fields: [
                    'consignee_number', 'consignee_contact_name', 'consignee_street',
                    'consignee_county', 'consignee_name', 'consignee_building',
                    'consignee_city', 'consignee_postal_code'
                ]
            });
            if (r4 && r4.length > 0) {
                const consignee = r4[0];
                frm.set_value('consignee_number', consignee.consignee_number);
                frm.set_value('consignee_contact_name', consignee.consignee_contact_name);
                frm.set_value('consignee_street', consignee.consignee_street);
                frm.set_value('consignee_country', consignee.consignee_county);
                frm.set_value('consignee_name', consignee.consignee_name);
                frm.set_value('consignee_building', consignee.consignee_building);
                frm.set_value('consignee_city', consignee.consignee_city);
                frm.set_value('consignee_postal_code', consignee.consignee_postal_code);
            } else {
                frappe.msgprint(__('No R400000 record on this Shipment number: [{0}]', [record.shipment_number]));
            }

            // Fetch R500000 records based on shipment number
            const r5 = await frappe.db.get_list('R500000', {
                filters: {
                    'shipment_number': record.shipment_number
                },
                fields: ['custom_invdesc', 'invoice_1_price']
            });
            if (r5 && r5.length > 0) {
                const invoice = r5[0];
                frm.set_value('invoice_description', invoice.custom_invdesc);
                frm.set_value('invoice_value', invoice.invoice_1_price);
            } else {
                frappe.msgprint(__('No R500000 record on this Shipment number: [{0}]', [record.shipment_number]));
            }

            // Additional logic for origin country handling
            let shipper_number = frm.doc.shipper_number;
            let consignee_number = frm.doc.consignee_number;
            let origin_country = frm.doc.origin_country;

            if (origin_country) {
                if (origin_country === 'PK') {
                    const icris_shipper = await frappe.db.get_value('ICRIS List', {'shipper_no': shipper_number}, 'shipper_name');
                    if (icris_shipper.message) {
                        const email_id_shipper = await frappe.db.get_value('Customer', {'customer_name': icris_shipper.message.shipper_name}, 'email_id');
                        if (email_id_shipper.message) {
                            frm.set_value('shipper_email_address', email_id_shipper.message.email_id);
                            console.log(icris_shipper.message.shipper_name);
                            console.log('Shipper');
                            frm.fields_dict.dispute_invoice_number.grid.get_field("customers_sales_invoice").get_query = function (frm, cdt, cdn) {
                                return {
                                    filters: {
                                        customer: icris_shipper.message.shipper_name
                                    },
                                };
                            };
                        
                        }
                    }else{
                        frappe.msgprint(__('There is no shipper of this shipper number in Icris List.'));
                    
                    }
                } else {
                    const icris_consignee = await frappe.db.get_value('ICRIS List', {'shipper_no': consignee_number}, 'shipper_name');
                    if (icris_consignee.message) {
                        const email_id_consignee = await frappe.db.get_value('Customer', {'customer_name': icris_consignee.message.shipper_name}, 'email_id');
                        if (email_id_consignee.message) {
                            frm.set_value('consignee_email_address', email_id_consignee.message.email_id);
                            console.log(icris_consignee.message.shipper_name);
                            console.log('Consignee');
                            frm.fields_dict.dispute_invoice_number.grid.get_field("customers_sales_invoice").get_query = function (frm, cdt, cdn) {
                                return {
                                    filters: {
                                        customer: icris_consignee.message.shipper_name
                                    },
                                };
                            };
                        
                        }
                    }else{
                        frappe.msgprint(__('There is no consignee of this consignee number in Icris List.'));
                    
                    }
                }
            } else {
                frappe.msgprint(__('Nothing in origin country.'));
            }
        } else {
            frappe.msgprint(__('No R200000 record on this tracking number: [{0}]', [tracking_number]));
        }
    } catch (error) {
        console.error(error);
        frappe.msgprint(__('An error occurred while fetching records: ' + error.name + ' - ' + error.message));

    }
}