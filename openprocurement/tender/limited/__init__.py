from openprocurement.tender.limited.models import Tender


def includeme(config):
    config.add_tender_procurementMethodType(Tender)
    config.scan("openprocurement.tender.limited.views")
