# -*- coding: utf-8 -*-
from openprocurement.audit.api.utils import (
    op_resource,
    APIResource,
    apply_patch,
    upload_objects_documents,
    set_author,
)
from openprocurement.api.utils import (
    json_view,
    get_now,
    context_unpack,
)
from openprocurement.audit.api.validation import (
    validate_elimination_report_data,
)


@op_resource(name='Monitoring Elimination',
             path='/monitorings/{monitoring_id}/eliminationReport',
             description='Elimination of the violation')
class EliminationReportResource(APIResource):

    @json_view(permission='view_monitoring')
    def get(self):
        return {'data': self.context.serialize('view')}

    @json_view(content_type='application/json',
               validators=(validate_elimination_report_data,),
               permission='create_elimination_report')
    def put(self):
        elimination = self.request.validated['eliminationreport']
        elimination.datePublished = elimination.dateCreated
        set_author(elimination.documents, self.request, 'author')
        upload_objects_documents(self.request, elimination)
        apply_patch(self.request, data=dict(eliminationReport=elimination), date_modified=elimination.dateCreated)
        self.LOGGER.info('Updated elimination {}'.format(self.request.context.id),
                         extra=context_unpack(self.request, {'MESSAGE_ID': 'elimination_put'}))
        return {'data': elimination.serialize('view')}
