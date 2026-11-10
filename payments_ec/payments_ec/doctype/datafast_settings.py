# En tu_app/tu_app/doctype/datafast_settings/datafast_settings.py
import frappe
from frappe.model.document import Document

class DatafastSettings(Document):
    def validate(self):
        # Aquí podrías validar las credenciales contra el API de Datafast
        pass