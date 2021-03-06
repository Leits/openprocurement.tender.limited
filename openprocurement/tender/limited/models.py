from zope.interface import implementer
from pyramid.security import Allow
from schematics.transforms import whitelist
from schematics.types import StringType, FloatType, IntType, URLType, BooleanType, BaseType, EmailType, MD5Type
from schematics.types.compound import ModelType, ListType, DictType
from schematics.types.serializable import serializable
from openprocurement.api.models import (plain_role, view_role, create_role,
                                        edit_role, enquiries_role, listing_role,
                                        cancel_role, Administrator_role,
                                        schematics_default_role,
                                        chronograph_role, chronograph_view_role)

from openprocurement.api.models import (Value, IsoDateTimeType, Document, Bid,
                                        Organization, Item, SchematicsDocument,
                                        Model, Period, Contract, Revision
                                        )
from openprocurement.api.models import validate_cpv_group, validate_items_uniq
from openprocurement.api.models import Award as BaseAward
from openprocurement.api.models import Cancellation as BaseCancellation
from openprocurement.api.models import ITender


class Award(BaseAward):

    bid_id = MD5Type(required=False)
    lotID = None
    complaints = []

    def validate_lotID(self, data, lotID):
        return

class Cancellation(BaseCancellation):
    cancellationOf = StringType(required=True, choices=['tender'], default='tender')

    def validate_relatedLot(self, data, relatedLot):
        return


@implementer(ITender)
class Tender(SchematicsDocument, Model):
    """Data regarding tender process - publicly inviting prospective contractors
       to submit bids for evaluation and selecting a winner or winners.
    """

    class Options:
        roles = {
            'plain': plain_role,
            'create': create_role,
            'edit': edit_role,
            'edit_active': edit_role,
            'edit_active.awarded': cancel_role,
            'edit_complete': whitelist(),
            'edit_unsuccessful': whitelist(),
            'edit_cancelled': whitelist(),
            'view': view_role,
            'listing': listing_role,
            'active': enquiries_role,
            'active.awarded': view_role,
            'complete': view_role,
            'unsuccessful': view_role,
            'cancelled': view_role,
            'Administrator': Administrator_role,
            'chronograph': chronograph_role,  # remove after chronograph fix
            'chronograph_view': chronograph_view_role, # remove after chronograph fix
            'default': schematics_default_role,
        }

    title = StringType(required=True)
    title_en = StringType()
    title_ru = StringType()
    description = StringType()
    description_en = StringType()
    description_ru = StringType()
    tenderID = StringType()  # TenderID should always be the same as the OCID. It is included to make the flattened data structure more convenient.
    items = ListType(ModelType(Item), required=True, min_size=1, validators=[validate_cpv_group, validate_items_uniq])  # The goods and services to be purchased, broken into line items wherever possible. Items should not be duplicated, but a quantity of 2 specified instead.
    value = ModelType(Value, required=True)  # The total estimated value of the procurement.
    procurementMethod = StringType(choices=['open', 'selective', 'limited'], default='limited')  # Specify tendering method as per GPA definitions of Open, Selective, Limited (http://www.wto.org/english/docs_e/legal_e/rev-gpr-94_01_e.htm)
    procurementMethodRationale = StringType()  # Justification of procurement method, especially in the case of Limited tendering.
    procurementMethodRationale_en = StringType()
    procurementMethodRationale_ru = StringType()
    procurementMethodType = StringType(default="reporting")
    bids = ListType(ModelType(Bid), default=list())  # A list of all the companies who entered submissions for the tender.
    procuringEntity = ModelType(Organization, required=True)  # The entity managing the procurement, which may be different from the buyer who is paying / using the items being procured.
    documents = ListType(ModelType(Document), default=list())  # All documents and attachments related to the tender.
    awards = ListType(ModelType(Award), default=list())
    contracts = ListType(ModelType(Contract), default=list())
    revisions = ListType(ModelType(Revision), default=list())
    status = StringType(choices=['active', 'complete', 'cancelled', 'unsuccessful'], default='active')
    mode = StringType(choices=['test'])
    cancellations = ListType(ModelType(Cancellation), default=list())
    _attachments = DictType(DictType(BaseType), default=dict())  # couchdb attachments
    dateModified = IsoDateTimeType()
    owner_token = StringType()
    owner = StringType()

    __parent__ = None
    __name__ = ''

    def __local_roles__(self):
        return dict([('{}_{}'.format(self.owner, self.owner_token), 'tender_owner')])

    def get_role(self):
        root = self.__parent__
        request = root.request
        if request.authenticated_role == 'Administrator':
            role = 'Administrator'
        elif request.authenticated_role == 'chronograph':
            role = 'chronograph'
        else:
            role = 'edit_{}'.format(request.context.status)
        return role

    def __acl__(self):
        acl = [
            (Allow, '{}_{}'.format(self.owner, self.owner_token), 'edit_tender'),
            (Allow, '{}_{}'.format(self.owner, self.owner_token), 'upload_tender_documents'),
            (Allow, '{}_{}'.format(self.owner, self.owner_token), 'review_complaint'),
        ]
        return acl

    def __repr__(self):
        return '<%s:%r@%r>' % (type(self).__name__, self.id, self.rev)

    @serializable(serialized_name='id')
    def doc_id(self):
        """A property that is serialized by schematics exports."""
        return self._id

    def import_data(self, raw_data, **kw):
        """
        Converts and imports the raw data into the instance of the model
        according to the fields in the model.
        :param raw_data:
            The data to be imported.
        """
        data = self.convert(raw_data, **kw)
        del_keys = [k for k in data.keys() if data[k] == self.__class__.fields[k].default or data[k] == getattr(self, k)]
        for k in del_keys:
            del data[k]

        self._data.update(data)
        return self
