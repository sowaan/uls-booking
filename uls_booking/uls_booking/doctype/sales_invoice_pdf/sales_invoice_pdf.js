// Copyright (c) 2024, Sowaan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Invoice PDF", {
    refresh(frm) {
        // Hide Add Row and Delete button in the child table
        frm.fields_dict["customer_with_sales_invoice"].grid.wrapper.find('.grid-add-row').hide();
        frm.fields_dict["customer_with_sales_invoice"].grid.wrapper.find('.grid-remove-rows').hide();

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button("Send Sales Invoice Email", function() {
                let selected_customers = [];
    
                (frm.fields_dict["customer_with_sales_invoice"].grid.get_selected_children() || []).forEach(row => {
                    if (row.customer) {
                        selected_customers.push(row.customer);
                    }
                });
    
                if (selected_customers.length === 0) {
                    frappe.msgprint(__("Please select at least one row."));
                    return;
                }
                
                frappe.call({
                    method: "uls_booking.uls_booking.api.email.send_multi_email_with_attachment",
                    args: { 
                        doc_name: frm.doc.name,
                        selected_customers: JSON.stringify(selected_customers)
                    },
                    callback: function(response) {
                        if (response.message) {
                            frappe.msgprint(response.message);
                        }
                    }
                });
            });
        

            frm.add_custom_button('Download ZIP', async () => {
                const selected = frm.fields_dict["customer_with_sales_invoice"].grid.get_selected_children();
            
                if (!selected.length) {
                    frappe.msgprint("Please select at least one row.");
                    return;
                }
            
                const selected_names = selected.map(row => row.name);

                // console.log("Selected Customers:", selected_names);
                // return
            
                let overlay = document.getElementById('custom-loading-overlay');
                if (!overlay) {
                    overlay = document.createElement('div');
                    overlay.id = 'custom-loading-overlay';
                    overlay.innerHTML = `
                        <div id="custom-loading-wrapper">
                            <div id="custom-loading-bar"><div class="custom-progress"></div></div>
                            <div style="margin-top: 5px; font-size: 10pt; color: #444;">Preparing ZIP...</div>
                        </div>`;
                    document.body.appendChild(overlay);
            
                    const style = document.createElement('style');
                    style.textContent = `
                        #custom-loading-overlay {
                            position: fixed;
                            bottom: 20px;
                            right: 20px;
                            background: rgba(255, 255, 255, 0.9);
                            padding: 10px 15px;
                            border-radius: 6px;
                            box-shadow: 0 0 8px rgba(0,0,0,0.15);
                            display: none;
                            z-index: 9999;
                        }
                        #custom-loading-wrapper {
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                        }
                        #custom-loading-bar {
                            width: 150px;
                            height: 6px;
                            background: #e0e0e0;
                            overflow: hidden;
                            border-radius: 4px;
                        }
                        .custom-progress {
                            height: 100%;
                            width: 40px;
                            background: #007bff;
                            animation: custom-slide 1s infinite linear;
                            border-radius: 4px;
                        }
                        @keyframes custom-slide {
                            from { margin-left: -40px; }
                            to { margin-left: 100%; }
                        }`;
                    document.head.appendChild(style);
                }
            
                overlay.style.display = 'flex';
            
                try {
                    const download_url = `/api/method/uls_booking.uls_booking.api.api.download_sales_invoices_zip?docname=${encodeURIComponent(frm.doc.name)}&selected_customers=${encodeURIComponent(JSON.stringify(selected_names))}`;
            
                    const res = await fetch(download_url, {
                        method: "GET",
                        headers: {
                            'X-Frappe-CSRF-Token': frappe.csrf_token
                        }
                    });
                    
                    if (!res.ok || res.headers.get("content-type") !== "application/zip") {
                        const errorText = await res.text();
                        frappe.show_alert({
                            message: `Failed to generate ZIP: ${errorText}`,
                            indicator: 'red'
                        });
                        return;
                    }
            
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `${frm.doc.name}_Customer_Invoices.zip`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                    
                } catch (err) {
                    frappe.show_alert({
                        message: `Error: ${err.message}`,
                        indicator: 'red'
                    });
                } finally {
                    overlay.style.display = 'none';
                }
            });
        
        
        
        
        
        }
    }
});

