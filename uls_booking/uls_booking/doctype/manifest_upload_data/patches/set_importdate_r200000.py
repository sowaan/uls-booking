import frappe

def execute():
    # SQL Query to update the 'manifest_import_date' by converting 'import_date'
    sql_query = """
        UPDATE `tabR200000`
        SET manifest_import_date = STR_TO_DATE(import_date, '%y%m%d')
        WHERE import_date != '000000'
    """
    
    # Execute the SQL query to update all the records
    frappe.db.sql(sql_query)

    print("Update completed.")