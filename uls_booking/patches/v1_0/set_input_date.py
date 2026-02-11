import frappe

def execute():
    # SQL Query to update the 'manifest_input_date' by converting 'input_date'
    sql_query = """
        UPDATE `tabR200000`
        SET manifest_input_date = 
            CASE
                WHEN LENGTH(input_date) = 8 AND input_date NOT LIKE '%-%' THEN STR_TO_DATE(input_date, '%d%b%Y')  -- For 'DDMMMYYYY' format
                WHEN LENGTH(input_date) = 10 AND input_date LIKE '%-%' THEN STR_TO_DATE(input_date, '%Y-%m-%d')  -- For 'YYYY-MM-DD' format
                ELSE NULL  -- Invalid or unrecognized formats
            END
        WHERE input_date != '000000'
    """
    
    # Execute the SQL query to update all the records
    frappe.db.sql(sql_query)

    print("Update completed.")

