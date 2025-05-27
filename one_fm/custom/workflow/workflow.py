import frappe
import json
import os
from frappe import _
from one_fm.utils import get_json_file

def get_workflow_json_file(file_name):
    """
    Load JSON data from a workflow file.
    Args:
        file_name (str): The name of the JSON file located in the 'workflow' folder.
    Return:
        dict: The JSON data loaded from the file.
    """
    folder = frappe.get_app_path("one_fm", "custom", "workflow")
    return get_json_file(file_name, folder)

def create_workflow(workflow:dict):
    """
    Create or update a Workflow along with its states and actions.
    Args:
        workflow (dict): A dictionary representing the workflow data.
            - workflow_name (str): The name of the workflow.
            - document_type (str): The document type associated with the workflow.
            - is_active (int): Whether the workflow is active (1) or inactive (0).
            - override_status (int): Whether the workflow can override document status (1) or not (0).
            - send_email_alert (int): Whether to send email alerts for workflow actions (1) or not (0).
            - workflow_state_field (str): The field name used to store the current workflow state in documents.
            - doctype (str): The internal document type associated with the workflow.
            - states (list): A list of dictionaries representing workflow states.
                - state (str): The name of the workflow state.
                - doc_status (str): The document status associated with the state (optional).
                - is_optional_state (int): Whether the state is optional (1) or mandatory (0).
                - avoid_status_override (int): Whether to prevent manual status overrides in this state (1) or not (0).
                - allow_edit (str): The user role allowed to edit documents in this state.
            - transitions (list): A list of dictionaries representing workflow transitions.
                - state (str): The starting state for the transition.
                - action (str): The action name used to trigger the transition.
                - next_state (str): The state to transition to after the action is performed.
                - allowed (str): The user role allowed to perform the action.
                - allow_self_approval (int): Whether self-approval is allowed for the action (1) or not (0).
                - skip_multiple_action (int): Whether to skip choosing multiple actions (1) or not (0).
                - skip_creation_of_workflow_action (int): Whether to skip creating a workflow action record (1) or not (0).
                - custom_confirm_transition (int): Whether a custom confirmation is required before performing the action (1) or not (0).
    Returns:
        None
    """
    if not isinstance(workflow, dict) or not ("states" in workflow and "transitions" in workflow):
        frappe.log_error("Invalid or incomplete workflow definition.")
        return

    try:
        state_values = [{"workflow_state_name": state["state"]} for state in workflow["states"]]
        create_workflow_state(state_values)

        actions = list(set([transition["action"] for transition in workflow["transitions"]]))
        create_workflow_action_master(actions)

        if not frappe.db.exists("Workflow", workflow["workflow_name"]):
            frappe.get_doc(workflow).insert(ignore_permissions=True)
        else:
            workflow_obj = frappe.get_doc("Workflow", workflow["workflow_name"])
            workflow_obj.update(workflow)
            workflow_obj.save()
    except Exception as e:
        frappe.log_error(
            title="Workflow Creation Error",
            message=f"Failed to create or update workflow '{workflow.get('workflow_name', '')}':\n{frappe.get_traceback()}"
        )

def create_workflow_state(states: list):
    """
    Create or update Workflow States.
    Args:
        states (list[dict]): A list of state dictionaries with:
            - Each key in the dictionary represents the name of a state.
            - The corresponding value should be another dictionary with the following keys:
                - `workflow_state_name` (str): The name of the workflow state
                - `style` (str, optional): The style of the workflow state
                (e.g., Primary, Info, Success, Warning, Danger and Inverse)

    Returns:
        None
    """
    for state in states:
        try:
            if not frappe.db.exists("Workflow State", state["workflow_state_name"]):
                frappe.get_doc({"doctype": "Workflow State", **state}).insert(ignore_permissions=True)
            else:
                workflow_state = frappe.get_doc("Workflow State", state["workflow_state_name"])
                workflow_state.update(state)
                workflow_state.save()
        except Exception as e:
            frappe.log_error(
                title="Workflow State Error",
                message=f"Failed to create/update state '{state.get('workflow_state_name')}':\n{frappe.get_traceback()}"
            )

def create_workflow_action_master(action_masters):
    """
    Create or update Workflow Action Masters.

    Args:
        action_masters (str or list[str]): Action(s) to be created if not already present.

    Returns:
        None
    """
    if isinstance(action_masters, str):
        action_masters = [action_masters]

    if not isinstance(action_masters, list):
        frappe.log_error("Workflow actions must be a list or string.")
        return

    # Clean and deduplicate
    action_masters = list(set([a.strip() for a in action_masters if isinstance(a, str) and a.strip()]))

    if not action_masters:
        return

    try:
        existing_actions = frappe.get_all(
            "Workflow Action Master",
            filters={"workflow_action_name": ["in", action_masters]},
            pluck="workflow_action_name"
        )

        to_create = set(action_masters) - set(existing_actions)

        for action in to_create:
            frappe.get_doc({
                "doctype": "Workflow Action Master",
                "workflow_action_name": action
            }).insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(
            title="Workflow Action Master Error",
            message=f"Error while creating workflow actions:\n{frappe.get_traceback()}"
        )


def delete_workflow(workflow:dict):
    """
    Delete a Workflow by name.
    Args:
        workflow (dict): A dictionary representing the workflow data.
            - workflow_name (str): The name of the workflow.
    Returns:
        None
    """
    name = workflow.get("workflow_name")
    if not name:
        frappe.log_error("Missing 'workflow_name' in workflow deletion input.")
        return

    try:
        if frappe.db.exists("Workflow", name):
            frappe.delete_doc("Workflow", name, ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            title="Workflow Deletion Error",
            message=f"Failed to delete workflow '{name}':\n{frappe.get_traceback()}"
        )
