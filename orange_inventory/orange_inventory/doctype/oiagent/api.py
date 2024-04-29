
import frappe


@frappe.whitelist()
def welcome_agent(agent_id:str, agent_name:str)->None:
    return True