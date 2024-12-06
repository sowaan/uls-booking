frappe.ui.form.on('Shipment Master Details', {
    refresh: function (frm) {
        frm.add_custom_button('Get Records', async function () {
            if (!frm.doc.master_package_id) {
                clear_form_fields(frm);  
                frm.refresh();
            } else {
                await get_records(frm);  
            }
        });
    },

    master_package_id: async function (frm) {
        if (!frm.doc.master_package_id) {
            clear_form_fields(frm);  
            frm.refresh();
        }
    }

});




function clear_form_fields(frm) {
    const fields_to_clear = [
        'shipment_number', 'origin_country', 'date_shipped', 'shipment_type','origin_port','destination_port','shipment_tracking_status',
        'bill_term_surcharge_indicator', 'split_duty_and_vat_flag', 'split_duty_and_vat_flag_master','billable_weight',
        'shipment_weight', 'destination_country', 'import_date', 'billing_term','dws_actual_weight','dws_dim',
        'shipment_weight_unit', 'number_of_packages_in_shipment','reference_number_1','reference_number_3',
        'shipper_number', 'shipper_contact_name', 'shipper_street', 'shipper_country','consignee_phone_number',
        'shipper_postal_code', 'shipper_name', 'shipper_building', 'shipper_city','reference_number_2','container_type_code',
        'consignee_number', 'consignee_contact_name', 'consignee_street', 'consignee_country','shipper_phone_number',
        'consignee_name', 'consignee_building', 'consignee_city', 'consignee_postal_code','rating_pkg_2_type_code',
        'invoice_description', 'invoice_value', 'shipper_email_address', 'consignee_email_address','shipment_billing_type'
    ];
    fields_to_clear.forEach(field => frm.set_value(field, null));
    frm.clear_table('dispute_invoice_number');
}







async function get_records(frm) {
    const tracking_number = frm.doc.master_package_id;
    try {
        // Fetch R600000 records to get shipment number and other values
        const r6 = await frappe.db.get_list('R600000', {
            filters: { 'expanded_package_tracking_number': tracking_number },
            fields: ["shipment_number", "shipment_tracking_status", "dws_actual_weight", "dws_dim"]
        });
        
        if (r6 && r6.length > 0) {
            const r6_record = r6[0]; 
            const ship_num = r6_record.shipment_number;
            frm.set_value('shipment_number', r6_record.shipment_number || '');
            frm.set_value('shipment_tracking_status', r6_record.shipment_tracking_status || '');
            frm.set_value('dws_actual_weight', r6_record.dws_actual_weight || '');
            frm.set_value('dws_dim', r6_record.dws_dim || '');
            




            // Fetch R202000 record based on shipment number
            const r22 = await frappe.db.get_list('R202000', {
                filters: { 'shipment_number': ship_num },
                fields: ["custom_rating_pkg_2_type_code", "custom_container_type_code"]
            });
            if (r22 && r22.length > 0) {
                const r2_record = r22[0];
                frm.set_value('container_type_code', r2_record.custom_container_type_code || '');
                frm.set_value('rating_pkg_2_type_code', r2_record.custom_rating_pkg_2_type_code || '');

            }else{
                frm.set_value('container_type_code', '');
                frm.set_value('rating_pkg_2_type_code', '');
                frappe.msgprint(__('No R202000 record on this Shipment number: [{0}]', [ship_num]));
            }






            // Fetch R200000 record based on shipment number
            const r2 = await frappe.db.get_list('R200000', {
                filters: { 'shipment_number': ship_num },
                fields: [
                    "origin_country","shipment_type","shipped_date",
                    "bill_term_surcharge_indicator", "split_duty_and_vat_flag",
                    "shipment_weight", "destination_country", "import_date","destination_port",
                    "billing_term_field", "shipment_weight_unit","origin_port",
                    "number_of_packages_in_shipment","biling_type_shipment"
                ]
            });
            if (r2 && r2.length > 0) {
                const record = r2[0];
                frm.set_value('origin_country', record.origin_country || '');
                frm.set_value('date_shipped', record.shipped_date || '');
                frm.set_value('shipment_type', record.shipment_type || '');
                frm.set_value('bill_term_surcharge_indicator', record.bill_term_surcharge_indicator || '');
                frm.set_value('split_duty_and_vat_flag', record.split_duty_and_vat_flag || '');
                frm.set_value('split_duty_and_vat_flag_master', record.split_duty_and_vat_flag || '');
                frm.set_value('shipment_weight', record.shipment_weight || '');
                frm.set_value('destination_country', record.destination_country || '');
                frm.set_value('import_date', record.import_date || '');
                frm.set_value('billing_term', record.billing_term_field || '');
                frm.set_value('shipment_weight_unit', record.shipment_weight_unit || '');
                frm.set_value('number_of_packages_in_shipment', record.number_of_packages_in_shipment || '');
                frm.set_value('shipment_billing_type', record.biling_type_shipment || '');
                frm.set_value('destination_port', record.destination_port || '');
                frm.set_value('origin_port', record.origin_port || '');
            } else {
                frm.set_value('origin_country', '');
                frm.set_value('date_shipped', '');
                frm.set_value('shipment_type', '');
                frm.set_value('bill_term_surcharge_indicator', '');
                frm.set_value('split_duty_and_vat_flag', '');
                frm.set_value('split_duty_and_vat_flag_master', '');
                frm.set_value('shipment_weight', '');
                frm.set_value('destination_country', '');
                frm.set_value('import_date', '');
                frm.set_value('billing_term', '');
                frm.set_value('terms_of_shipment', '');
                frm.set_value('shipment_weight_unit', '');
                frm.set_value('number_of_packages_in_shipment', '');
                frm.set_value('shipment_billing_type', '');
                frm.set_value('origin_port',  '');
                frm.set_value('destination_port',  '');
                frappe.msgprint(__('No R200000 record on this tracking number: [{0}]', [tracking_number]));
            }




            // Fetch R201000 record based on shipment number
            const r21 = await frappe.db.get_value('R201000', {'shipment_number': ship_num}, 'custom_minimum_bill_weight');
            if (r21.message) {
                const billWeight = r21.message.custom_minimum_bill_weight || '';
                frm.set_value('billable_weight', billWeight);
            
            } else {
                frm.set_value('billable_weight', '');
                frappe.msgprint(__('No R201000 record on this Shipment number: [{0}]', [ship_num]));
            }






            // Fetch R300000 records based on shipment number
            const r3 = await frappe.db.get_list('R300000', {
                filters: { 'shipment_number': ship_num },
                fields: [
                    'shipper_number', 'shipper_contact_name', 'shipper_street',
                    'shipper_country', 'shipper_postal_code', 'shipper_name',
                    'shipper_building', 'shipper_city','shipper_phone_number','alternate_tracking_number_1'
                ]
            });
            
            if (r3 && r3.length > 0) {
                const shipper = r3[0];
                frm.set_value('shipper_number', shipper.shipper_number || '');
                frm.set_value('shipper_contact_name', shipper.shipper_contact_name || '');
                frm.set_value('shipper_street', shipper.shipper_street || '');
                frm.set_value('shipper_country', shipper.shipper_country || '');
                frm.set_value('shipper_postal_code', shipper.shipper_postal_code || '');
                frm.set_value('shipper_name', shipper.shipper_name || '');
                frm.set_value('shipper_building', shipper.shipper_building || '');
                frm.set_value('shipper_city', shipper.shipper_city || '');
                frm.set_value('shipper_phone_number', shipper.shipper_phone_number || '');
                frm.set_value('reference_number_1', shipper.alternate_tracking_number_1 || '');
            } else {
                frm.set_value('shipper_number', '');
                frm.set_value('shipper_contact_name', '');
                frm.set_value('shipper_street', '');
                frm.set_value('shipper_country', '');
                frm.set_value('shipper_postal_code', '');
                frm.set_value('shipper_name', '');
                frm.set_value('shipper_building', '');
                frm.set_value('shipper_city', '');
                frm.set_value('shipper_phone_number', '');
                frm.set_value('reference_number_1', '');
                frappe.msgprint(__('No R300000 record found for Shipment number: [{0}]', [ship_num]));
            }





          
            // Fetch R400000 records based on shipment number
            const r4 = await frappe.db.get_list('R400000', {
                filters: { 'shipment_number': ship_num },
                fields: [
                    'consignee_number', 'consignee_contact_name', 'consignee_street','alternate_tracking_number_2',
                    'consignee_county', 'consignee_name', 'consignee_building','consignee_po_number',
                    'consignee_city', 'consignee_postal_code','consignee_phone_number'
                ]
            });
            
            if (r4 && r4.length > 0) {
                const consignee = r4[0];
                frm.set_value('consignee_number', consignee.consignee_number || '');
                frm.set_value('consignee_contact_name', consignee.consignee_contact_name || '');
                frm.set_value('consignee_street', consignee.consignee_street || '');
                frm.set_value('consignee_country', consignee.consignee_county || ''); 
                frm.set_value('consignee_name', consignee.consignee_name || '');
                frm.set_value('consignee_building', consignee.consignee_building || '');
                frm.set_value('consignee_city', consignee.consignee_city || '');
                frm.set_value('consignee_postal_code', consignee.consignee_postal_code || '');
                frm.set_value('consignee_phone_number', consignee.consignee_phone_number || '');
                frm.set_value('reference_number_2', consignee.alternate_tracking_number_2 || '');
                frm.set_value('reference_number_3', consignee.consignee_po_number || '');
            } else {
                frm.set_value('consignee_number', '');
                frm.set_value('consignee_contact_name', '');
                frm.set_value('consignee_street', '');
                frm.set_value('consignee_country', '');
                frm.set_value('consignee_name', '');
                frm.set_value('consignee_building', '');
                frm.set_value('consignee_city', '');
                frm.set_value('consignee_postal_code', '');
                frm.set_value('consignee_phone_number', '');
                frm.set_value('reference_number_2', '');
                frm.set_value('reference_number_3', '');
                frappe.msgprint(__('No R400000 record found for Shipment number: [{0}]', [ship_num]));
            }



            

            // Fetch R500000 records based on shipment number
            const r5 = await frappe.db.get_list('R500000', {
                filters: { 'shipment_number': ship_num },
                fields: ['custom_invdesc', 'invoice_1_price']
            });
            
            if (r5 && r5.length > 0) {
                const invoice = r5[0];
                frm.set_value('invoice_description', invoice.custom_invdesc || '');
                frm.set_value('invoice_value', invoice.invoice_1_price || '');
            } else {
                frm.set_value('invoice_description', '');
                frm.set_value('invoice_value', '');
            
                frappe.msgprint(__('No R500000 record found for Shipment number: [{0}]', [ship_num]));
            }



            

            let shipper_number = frm.doc.shipper_number;
            let consignee_number = frm.doc.consignee_number;
            let origin_country = frm.doc.origin_country;

            if (origin_country) {
                if (origin_country.toUpperCase() === 'PK' || origin_country.toUpperCase() === 'PAK' || origin_country.toUpperCase() === 'PAKISTAN') {
                    const icris_shipper = await frappe.db.get_value('ICRIS List', {'shipper_no': shipper_number}, 'shipper_name');
                    if (icris_shipper.message) {
                        const email_id_shipper = await frappe.db.get_value('Customer', {'customer_name': icris_shipper.message.shipper_name}, 'email_id');
                        if (email_id_shipper.message) {
                            frm.set_value('shipper_email_address', email_id_shipper.message.email_id);
                            console.log(icris_shipper.message.shipper_name );
                            // console.log('Shipper');
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
                            console.log(icris_consignee.message.shipper_name );
                            // console.log('Consignee');
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
            clear_form_fields(frm);
            frappe.msgprint(__('No R600000 record on this tracking number: [{0}]', [tracking_number]));
        }
    } catch (error) {
        console.error(error);
        frappe.msgprint(__('An error occurred while fetching records: ' + error.name + ' - ' + error.message));
    }
}
