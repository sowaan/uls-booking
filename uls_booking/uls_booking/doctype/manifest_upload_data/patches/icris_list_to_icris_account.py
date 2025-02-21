import frappe

def execute():
    icris_list = frappe.get_all(
        "ICRIS List",
        fields=["shipper_no", "contact", "shipper_name", "active_account", "business_initiative", "station", "price_list", "center"]
    )

    for i in icris_list:
        icris_account = frappe.get_value("ICRIS Account", {"name": i.shipper_no}, "name")

        if icris_account:
            frappe.db.set_value("ICRIS Account", icris_account, {
                "active_account": i.active_account,
                "business_initiative": i.business_initiative,
                "station": i.station,
                "price_list": i.price_list,
                "contact": i.contact,
                "shipper_name": i.shipper_name,
                "center": i.center
            })
            frappe.db.commit()