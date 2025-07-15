# import frappe


def after_save(self, method):
    if self.owner != "salesinvoice_api@gmail.com":
        return
    if self.is_new():
        return
    if self.parent_idfrom_utility and self.created_byfrom_utility:
        self.add_comment("Comment", f"Processed by {self.created_byfrom_utility} via tool (Parent ID: {self.parent_idfrom_utility}).")
