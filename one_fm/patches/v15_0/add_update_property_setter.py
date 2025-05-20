import frappe
from one_fm.custom.property_setter.property_setter import create_property_setter
from one_fm.setup import get_field_properties

def execute():
    create_property_setter(get_field_properties())
