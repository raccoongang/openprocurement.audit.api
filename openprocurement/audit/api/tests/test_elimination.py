from openprocurement.audit.api.tests.base import BaseWebTest, DSWebTestMixin
from freezegun import freeze_time
from datetime import datetime
from hashlib import sha512
import unittest
import mock

from openprocurement.audit.api.tests.utils import get_errors_field_names


@freeze_time('2018-01-01T11:00:00+02:00')
class MonitoringEliminationBaseTest(BaseWebTest, DSWebTestMixin):

    def setUp(self):
        super(MonitoringEliminationBaseTest, self).setUp()
        self.app.app.registry.docservice_url = 'http://localhost'

    def create_active_monitoring(self, **kwargs):
        self.create_monitoring(**kwargs)
        self.app.authorization = ('Basic', (self.sas_token, ''))

        self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "decision": {
                    "description": "text",
                    "date": datetime.now().isoformat()
                },
                "status": "active",
            }}
        )

        # get credentials for tha monitoring owner
        self.app.authorization = ('Basic', (self.broker_token, ''))
        with mock.patch('openprocurement.audit.api.validation.TendersClient') as mock_api_client:
            mock_api_client.return_value.extract_credentials.return_value = {
                'data': {'tender_token': sha512('tender_token').hexdigest()}
            }
            response = self.app.patch_json(
                '/monitorings/{}/credentials?acc_token={}'.format(self.monitoring_id, 'tender_token')
            )
        self.tender_owner_token = response.json['access']['token']

    def create_addressed_monitoring(self, **kwargs):
        self.create_active_monitoring(**kwargs)
        self.app.authorization = ('Basic', (self.sas_token, ''))
        self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "conclusion": {
                    "description": "Some text",
                    "violationOccurred": True,
                    "violationType": ["corruptionProcurementMethodType", "corruptionAwarded"],
                },
                "status": "addressed",
            }}
        )
        self.app.authorization = ('Basic', (self.broker_token, ''))

    def create_monitoring_with_elimination(self, **kwargs):
        self.create_addressed_monitoring(**kwargs)
        response = self.app.put_json(
            '/monitorings/{}/eliminationReport?acc_token={}'.format(self.monitoring_id, self.tender_owner_token),
            {"data": {
                "description": "It's a minimal required elimination report",
                "documents": [
                    {
                        'title': 'lorem.doc',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/msword',
                    }
                ]
            }},
        )
        self.elimination = response.json["data"]

    def create_monitoring_with_resolution(self, **kwargs):
        self.create_monitoring_with_elimination(**kwargs)
        self.app.authorization = ('Basic', (self.sas_token, ''))
        self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": {
                    "result": "partly",
                    "resultByType": {
                        "corruptionProcurementMethodType": "eliminated",
                        "corruptionAwarded": "not_eliminated",
                    },
                    "description": "Do you have spare crutches?",
                    "documents": [
                        {
                            'title': 'sign.p7s',
                            'url': self.generate_docservice_url(),
                            'hash': 'md5:' + '0' * 32,
                            'format': 'application/pkcs7-signature',
                        }
                    ]
                },
            }},
        )


@freeze_time('2018-01-01T11:00:00+02:00')
class MonitoringActiveEliminationResourceTest(MonitoringEliminationBaseTest):

    def setUp(self):
        super(MonitoringActiveEliminationResourceTest, self).setUp()
        self.create_active_monitoring()

    def test_fail_post_elimination_report_when_not_in_addressed_state(self):
        self.app.authorization = ('Basic', (self.broker_token, ''))
        request_data = {
            "description": "Five pint, six pint, seven pint, flour."
        }
        response = self.app.put_json(
            '/monitorings/{}/eliminationReport?acc_token={}'.format(self.monitoring_id, self.tender_owner_token),
            {"data": request_data},
            status=422
        )

        self.assertEqual(
            ('body', 'eliminationReport'),
            next(get_errors_field_names(response, 'Can\'t update in current active monitoring status.')))


@freeze_time('2018-01-01T11:00:00+02:00')
class MonitoringEliminationResourceTest(MonitoringEliminationBaseTest):

    def setUp(self):
        super(MonitoringEliminationResourceTest, self).setUp()
        self.create_addressed_monitoring()

    def test_get_elimination(self):
        self.app.get(
            '/monitorings/{}/eliminationReport'.format(self.monitoring_id),
            status=403
        )

    def test_patch_elimination(self):
        self.app.patch_json(
            '/monitorings/{}/eliminationReport?acc_token={}'.format(self.monitoring_id, self.tender_owner_token),
            {"data": {"description": "One pint, two pint, three pint, four,"}},
            status=405
        )

    def test_patch_sas_elimination(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        self.app.patch_json(
            '/monitorings/{}/eliminationReport'.format(self.monitoring_id),
            {"data": {"description": "One pint, two pint, three pint, four,"}},
            status=405
        )

    def test_success_put(self):
        self.app.authorization = ('Basic', (self.broker_token, ''))
        request_data = {
            "description": "Five pint, six pint, seven pint, flour.",
            "dateCreated": "1988-07-11T15:53:06.068598+03:00",
            "documents": [
                {
                    'title': 'lorem.doc',
                    'url': self.generate_docservice_url(),
                    'hash': 'md5:' + '0' * 32,
                    'format': 'application/msword',
                }
            ],
        }
        response = self.app.put_json(
            '/monitorings/{}/eliminationReport?acc_token={}'.format(self.monitoring_id, self.tender_owner_token),
            {"data": request_data},
        )
        self.assertEqual(response.status_code, 200)

        # get monitoring
        self.app.authorization = None
        response = self.app.get('/monitorings/{}'.format(self.monitoring_id))
        data = response.json["data"]["eliminationReport"]
        self.assertEqual(data["description"], request_data["description"])
        self.assertEqual(data["dateCreated"], "2018-01-01T11:00:00+02:00")
        self.assertNotIn("resolution", data)
        self.assertEqual(len(data["documents"]), 1)
        document = data["documents"][0]
        self.assertNotEqual(document["url"], request_data["documents"][0]["url"])
        self.assertEqual(document["author"], "tender_owner")

    def test_fail_update_resolution(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        request_data = {
            "result": "partly",
            "resultByType": {
                "corruptionProcurementMethodType": "eliminated",
                "corruptionAwarded": "not_eliminated",
            },
            "description": "Do you have spare crutches?",
            "documents": [
                {
                    'title': 'sign.p7s',
                    'url': self.generate_docservice_url(),
                    'hash': 'md5:' + '0' * 32,
                    'format': 'application/pkcs7-signature',
                }
            ]
        }
        self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": request_data,
            }},
            status=422
        )


class MonitoringEliminationResolutionResourceTest(MonitoringEliminationBaseTest):

    def setUp(self):
        super(MonitoringEliminationResolutionResourceTest, self).setUp()
        self.create_monitoring_with_resolution()

    def test_elimination_resolution_get(self):
        response = self.app.get('/monitorings/{}/eliminationResolution'.format(self.monitoring_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEquals('partly', response.json['data']['result'])
        self.assertEquals('Do you have spare crutches?', response.json['data']['description'])

    def test_elimination_report_get(self):
        response = self.app.get('/monitorings/{}/eliminationReport'.format(self.monitoring_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEquals('It\'s a minimal required elimination report', response.json['data']['description'])

class UpdateEliminationResourceTest(MonitoringEliminationBaseTest):

    def setUp(self):
        super(UpdateEliminationResourceTest, self).setUp()
        self.create_monitoring_with_elimination(parties=[self.initial_party])

    def test_forbidden_sas_patch(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        request_data = {
            "description": "I'm gonna change this",
            "documents": [],
        }
        self.app.patch_json(
            '/monitorings/{}/eliminationReport?acc_token={}'.format(self.monitoring_id, self.tender_owner_token),
            {"data": request_data},
            status=405
        )

    def test_forbidden_patch(self):
        self.app.authorization = ('Basic', (self.broker_token, ''))
        request_data = {
            "description": "I'm gonna change this",
            "documents": [],
        }
        self.app.patch_json(
            '/monitorings/{}/eliminationReport'.format(self.monitoring_id),
            {"data": request_data},
            status=405
        )

    def test_forbidden_put(self):
        self.app.authorization = ('Basic', (self.broker_token, ''))
        response = self.app.put_json(
            '/monitorings/{}/eliminationReport?acc_token={}'.format(self.monitoring_id, self.tender_owner_token),
            {"data": {
                "description": "Hi there",
                "documents": [
                    {
                        'title': 'texts.doc',
                        'url': self.generate_docservice_url(),
                        'hash': 'md5:' + '0' * 32,
                        'format': 'application/msword',
                    }
                ],
            }},
            status=403
        )
        self.assertEqual(
            response.json["errors"],
            [{u'description': u"Can't post another elimination report.", u'location': u'body', u'name': u'data'}],
        )

    def test_forbidden_sas_post_document(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        document = {
            'title': 'lol.doc',
            'url': self.generate_docservice_url(),
            'hash': 'md5:' + '0' * 32,
            'format': 'application/helloword',
        }
        self.app.post_json(
            '/monitorings/{}/eliminationReport/documents?acc_token={}'.format(
                self.monitoring_id, self.tender_owner_token),
            {"data": document},
            status=403
        )

    def test_forbidden_without_token_post_document(self):
        self.app.authorization = ('Basic', (self.broker_token, ''))
        document = {
            'title': 'lol.doc',
            'url': self.generate_docservice_url(),
            'hash': 'md5:' + '0' * 32,
            'format': 'application/helloword',
        }
        self.app.post_json(
            '/monitorings/{}/eliminationReport/documents'.format(self.monitoring_id),
            {"data": document},
            status=403
        )

    def test_success_post_document(self):
        # dateModified
        response = self.app.get('/monitorings/{}'.format(self.monitoring_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["dateModified"], '2018-01-01T11:00:00+02:00')

        self.app.authorization = ('Basic', (self.broker_token, ''))
        document = {
            'title': 'lol.doc',
            'url': self.generate_docservice_url(),
            'hash': 'md5:' + '0' * 32,
            'format': 'application/helloword',
        }
        post_time = '2018-01-13T13:35:00+02:00'
        with freeze_time(post_time):
            response = self.app.post_json(
                '/monitorings/{}/eliminationReport/documents?acc_token={}'.format(
                    self.monitoring_id, self.tender_owner_token),
                {"data": document},
            )
        self.assertEqual(response.status_code, 201)

        self.app.authorization = None
        response = self.app.get('/monitorings/{}'.format(self.monitoring_id))
        self.assertEqual(response.status_code, 200)
        data = response.json["data"]
        self.assertEqual(len(data["eliminationReport"]["documents"]), 2)
        self.assertEqual(data["eliminationReport"]["documents"][1]["title"], document["title"])
        self.assertEqual(data["dateModified"], post_time)

    def test_patch_document_forbidden(self):
        self.app.authorization = ('Basic', (self.broker_token, ''))
        document = {
            'title': 'another.txt',
            'url': self.generate_docservice_url(),
            'hash': 'md5:' + '0' * 32,
            'format': 'application/msword',
        }
        doc_to_update = self.elimination["documents"][0]

        self.app.patch_json(
            '/monitorings/{}/eliminationReport/documents/{}?acc_token={}'.format(
                self.monitoring_id, doc_to_update["id"], self.tender_owner_token
            ),
            {"data": document},
            status=403
        )

    def test_put_document_forbidden(self):
        self.app.authorization = ('Basic', (self.broker_token, ''))
        document = {
            'title': 'my_new_file.txt',
            'url': self.generate_docservice_url(),
            'hash': 'md5:' + '0' * 32,
            'format': 'text/css',
        }
        doc_to_update = self.elimination["documents"][0]

        self.app.put_json(
            '/monitorings/{}/eliminationReport/documents/{}?acc_token={}'.format(
                self.monitoring_id, doc_to_update["id"], self.tender_owner_token
            ),
            {"data": document},
            status=403
        )

    def test_fail_update_resolution_wo_result_by_type(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        request_data = {
            "result": "partly",
        }
        response = self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": request_data,
            }},
            status=422
        )
        self.assertEqual(response.json["errors"][0]["description"],
                         {"resultByType": ["This field is required."]})

    def test_fail_update_resolution_wrong_result_by_type(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        request_data = {
            "result": "partly",
            "resultByType": {
                "corruptionChanges": "eliminated",
            }
        }
        self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": request_data,
            }},
            status=422
        )

    def test_fail_update_resolution_wrong_result_by_type_value(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        request_data = {
            "result": "partly",
            "resultByType": {
                "corruptionProcurementMethodType": "eliminated",
                "corruptionAwarded": "Nope",
            }
        }
        self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": request_data,
            }},
            status=422
        )

    def test_success_update_resolution(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        request_data = {
            "result": "partly",
            "resultByType": {
                "corruptionProcurementMethodType": "eliminated",
                "corruptionAwarded": "not_eliminated",
            },
            "description": "Do you have spare crutches?",
            "documents": [
                {
                    'title': 'sign.p7s',
                    'url': self.generate_docservice_url(),
                    'hash': 'md5:' + '0' * 32,
                    'format': 'application/pkcs7-signature',
                }
            ]
        }
        response = self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": request_data,
            }},
        )
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/monitorings/{}'.format(self.monitoring_id))
        resolution = response.json["data"]["eliminationResolution"]

        self.assertEqual(resolution["result"], request_data["result"])
        self.assertEqual(resolution["resultByType"], request_data["resultByType"])
        self.assertEqual(resolution["description"], request_data["description"])
        self.assertEqual(resolution["dateCreated"], "2018-01-01T11:00:00+02:00")
        self.assertEqual(len(resolution["documents"]), len(request_data["documents"]))

    def test_success_update_party_resolution(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))

        response = self.app.get('/monitorings/{}'.format(self.monitoring_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        party_id = response.json['data']['parties'][0]['id']

        request_data = {
            "result": "partly",
            "resultByType": {
                "corruptionProcurementMethodType": "eliminated",
                "corruptionAwarded": "not_eliminated",
            },
            "description": "Do you have spare crutches?",
            "relatedParty": party_id
        }
        response = self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": request_data,
            }},
        )
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/monitorings/{}'.format(self.monitoring_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']['eliminationResolution']['relatedParty'], party_id)

    def test_success_update_party_resolution_party_id_not_exists(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))

        request_data = {
            "result": "partly",
            "resultByType": {
                "corruptionProcurementMethodType": "eliminated",
                "corruptionAwarded": "not_eliminated",
            },
            "description": "Do you have spare crutches?",
            "relatedParty": "Party with the devil"
        }
        response = self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": request_data,
            }}, status=422
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.content_type, 'application/json')

        self.assertEqual(
            ('body', 'eliminationResolution', 'relatedParty'),
            next(get_errors_field_names(response, 'relatedParty should be one of parties.')))

    def test_fail_change_status(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        response = self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "status": "completed",
            }},
            status=403
        )
        self.assertEqual(
            response.json["errors"],
            [{
                'description': "Can't change status to completed before elimination period ends.",
                'location': 'body',
                'name': 'data'
            }]
        )

    @freeze_time('2018-01-20T12:00:00.000000+03:00')
    def test_change_status_without_report(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "status": "completed",
            }}, status=422
        )


@freeze_time('2018-01-01T12:00:00.000000+03:00')
class ResolutionMonitoringResourceTest(MonitoringEliminationBaseTest):

    def setUp(self):
        super(ResolutionMonitoringResourceTest, self).setUp()
        self.create_monitoring_with_resolution()

    def test_change_report_not_allowed(self):
        self.app.authorization = ('Basic', (self.broker_token, ''))
        self.app.patch_json(
            '/monitorings/{}/eliminationReport?acc_token={}'.format(self.monitoring_id, self.tender_owner_token),
            {"data": {"description": "I want to change this description"}},
            status=405
        )

    @freeze_time('2018-01-20T12:00:00.000000+03:00')
    def test_success_change_status(self):
        self.app.authorization = ('Basic', (self.sas_token, ''))
        response = self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "status": "completed",
            }},
        )
        self.assertEqual(response.json["data"]["status"], "completed")

        # can't update resolution
        self.app.patch_json(
            '/monitorings/{}'.format(self.monitoring_id),
            {"data": {
                "eliminationResolution": {
                    "result": "completely",
                },
            }},
            status=422
        )

        # can't update elimination report
        self.app.authorization = ('Basic', (self.broker_token, ''))
        self.app.patch_json(
            '/monitorings/{}/eliminationReport?acc_token={}'.format(self.monitoring_id, self.tender_owner_token),
            {"data": {"description": "I want to change this description"}},
            status=405
        )


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(MonitoringActiveEliminationResourceTest))
    s.addTest(unittest.makeSuite(MonitoringEliminationResourceTest))
    s.addTest(unittest.makeSuite(MonitoringEliminationResolutionResourceTest))
    s.addTest(unittest.makeSuite(UpdateEliminationResourceTest))
    s.addTest(unittest.makeSuite(ResolutionMonitoringResourceTest))
    return s


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
