import frappe


def before_save(self, method):
    if self.is_new():
        self.add_comment("Comment", f"Processed by {self.created_byfrom_utility} via tool (Parent ID: {self.parent_idfrom_utility}).")
        return

    is_exist = frappe.db.get_value("Sales Invoice Logs", {"shipment_number": self.shipment_number}, "parent_idfrom_utility")
    if not is_exist:
        self.add_comment("Comment", f"Processed by {self.created_byfrom_utility} via tool (Parent ID: {self.parent_idfrom_utility}).")
        return

    if self.parent_idfrom_utility and is_exist != self.parent_idfrom_utility:
        self.add_comment("Comment", f"Processed by {self.created_byfrom_utility} via tool (Parent ID: {self.parent_idfrom_utility}).")
