# En tu_app/tu_app/payment_gateways/datafast.py
import frappe
import requests
from frappe import _

class DatafastController:
    def __init__(self, settings):
        self.settings = settings
        self.headers = {
            "Authorization": f"Bearer {self.settings.bearer_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def get_payment_url(self, **kwargs):
        """
        Paso 1: Prepara el checkout en Datafast y devuelve la URL del formulario.
        kwargs contendrá datos como amount, currency, reference_docname, etc.
        """
        # 1. Mapear datos de ERPNext a los campos que exige Datafast [citation:21][citation:26]
        payload = self._build_payload(kwargs)
        
        # 2. Hacer el POST a /v1/checkouts
        response = requests.post(
            f"{self.settings.base_url}v1/checkouts",
            data=payload,
            headers=self.headers
        )
        response.raise_for_status()
        checkout_id = response.json().get("id")

        # 3. Guardar el checkout_id en un Integration Request para seguimiento
        self._log_integration_request(kwargs, checkout_id)

        # 4. Devolver la URL que el frontend usará para renderizar el widget
        #    El frontend necesitará el checkout_id para el script de paymentWidgets.js
        return f"/payment/datafast/checkout?checkout_id={checkout_id}"

    def _build_payload(self, kwargs):
        """
        Aquí ocurre la 'interpolación' entre ERPNext y Datafast.
        """
        ref_doc = frappe.get_doc(kwargs.get("reference_doctype"), kwargs.get("reference_docname"))
        customer = frappe.get_doc("Customer", ref_doc.customer) if ref_doc.get("customer") else None
        # ... obtener dirección, items, etc.
        
        payload = {
            "entityId": self.settings.entity_id,
            "amount": kwargs.get("amount"),
            "currency": "USD",
            "paymentType": "DB",
            "merchantTransactionId": ref_doc.name, # ID único de la transacción
            # --- Mapeo de cliente ---
            "customer.givenName": customer.first_name if customer else "N/A",
            "customer.surname": customer.last_name if customer else "N/A",
            "customer.email": customer.email_id if customer else "test@test.com",
            "customer.ip": frappe.local.request_ip or "127.0.0.1",
            # --- Mapeo de items (simplificado, deberías iterar) ---
            "cart.items[0].name": ref_doc.items[0].item_name if ref_doc.get("items") else "Item",
            "cart.items[0].price": ref_doc.items[0].rate if ref_doc.get("items") else kwargs.get("amount"),
            "cart.items[0].quantity": ref_doc.items[0].qty if ref_doc.get("items") else 1,
            # --- Campos requeridos por Datafast/SRI ---
            "customParameters[SHOPPER_VAL_IVA]": self._get_iva_amount(ref_doc),
            "customParameters[SHOPPER_VAL_BASE0]": self._get_base0_amount(ref_doc),
            # ... otros campos de la tabla de Datafast
        }
        return payload

    def _get_iva_amount(self, ref_doc):
        # Lógica para extraer el IVA de los taxes de la factura
        return 0.0

    def _log_integration_request(self, kwargs, checkout_id):
        # Crear un doc "Integration Request" con el checkout_id
        pass

@frappe.whitelist(allow_guest=True)
def callback(resourcePath=None):
    if not resourcePath:
        frappe.throw(_("No se recibió el resourcePath"))

    # 1. Obtener la configuración
    settings = frappe.get_single("Datafast Settings")
    
    # 2. Consultar el estado real a Datafast
    response = requests.get(
        f"{settings.base_url.rstrip('/')}{resourcePath}",
        headers={"Authorization": f"Bearer {settings.bearer_token}"}
    )
    data = response.json()
    
    # 3. Verificar si el pago fue exitoso (según la documentación de OPPWA)
    if data.get("result", {}).get("code") in ["000.000.000", "000.100.110"]: # Códigos de éxito
        # 4. Disparar el evento de pago en ERPNext
        #    Necesitas encontrar la Payment Request asociada al merchantTransactionId
        #    y llamar a su método on_payment_authorized("Completed")
        pass
    else:
        # Marcar como fallido
        pass

    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/payment/success" # Redirigir a una página de éxito