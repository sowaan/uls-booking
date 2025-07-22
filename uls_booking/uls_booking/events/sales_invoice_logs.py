import frappe

def on_update(self, method=None):
    if self.owner != "salesinvoice_api@gmail.com":
        return

    comment_text = f"Processed by {self.created_byfrom_utility} via tool (Parent ID: {self.parent_idfrom_utility})."

    existing_comment = frappe.db.exists("Comment", {
        "reference_doctype": self.doctype,
        "reference_name": self.name,
        "content": comment_text
    })

    if not existing_comment:
        self.add_comment("Comment", comment_text)
