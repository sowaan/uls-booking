frappe.ui.form.on('HD Ticket', {
	custom_shipment_master(frm) {
        let base_url = window.location.origin;
		// frappe.throw(str(base_url));
        // console.log(base_url);
        let url = base_url + '/app/shipment-master-details';
        window.open(url, '_blank');
	}
})