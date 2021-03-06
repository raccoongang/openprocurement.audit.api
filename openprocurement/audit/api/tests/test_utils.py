import unittest

import mock
from datetime import datetime, timedelta
from openprocurement.api.constants import TZ

from openprocurement.audit.api.utils import (
    calculate_business_date,
    get_access_token,
    get_monitoring_accelerator,
    calculate_normalized_business_date,
    calculate_normalized_date,
)


class CalculateBusinessDateTests(unittest.TestCase):
    """
    Test calendar:
        2018-01-01 - Mon (holiday)
        2018-01-02 - Tue
        2018-01-03 - Wed
        2018-01-04 - Thu
        2018-01-05 - Fri (holiday)
        2018-01-06 - Sat (weekend)
        2018-01-07 - Sun (weekend)
    """

    working_days_mock = {
        '2018-01-01': True,
        '2018-01-05': True,
    }

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_starts_on_non_working(self):
        date = datetime(2018, 1, 1, 12, 0, 0, tzinfo=TZ)
        result = calculate_business_date(date, timedelta(days=1), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 3, 0, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_starts_on_non_working_before_non_working(self):
        date = datetime(2017, 12, 31, 12, 0, 0, tzinfo=TZ)
        result = calculate_normalized_business_date(date, timedelta(days=1), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 3, 0, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_starts_on_working(self):
        date = datetime(2018, 1, 2, 12, 0, 0, tzinfo=TZ)
        result = calculate_business_date(date, timedelta(days=1), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 3, 12, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_ends_before_non_working(self):
        date = datetime(2018, 1, 2, 12, 0, 0, tzinfo=TZ)
        result = calculate_business_date(date, timedelta(days=2), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 4, 12, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_ends_on_non_working(self):
        date = datetime(2018, 1, 2, 12, 0, 0, tzinfo=TZ)
        result = calculate_business_date(date, timedelta(days=3), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 8, 12, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_ends_after_non_working(self):
        date = datetime(2018, 1, 2, 12, 0, 0, tzinfo=TZ)
        result = calculate_business_date(date, timedelta(days=4), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 9, 12, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.audit.api.utils.calculate_business_date_base')
    def test_days_calculation_base_call(self, base_calculate_mock):
        date = datetime.now()
        result = calculate_business_date(date, timedelta(days=10), working_days=False)
        base_calculate_mock.assert_called_once_with(date, timedelta(days=10), working_days=False)
        self.assertEqual(result, base_calculate_mock.return_value)

    def test_accelerator(self):
        date = datetime.now()
        result = calculate_business_date(date, timedelta(days=10), accelerator=2)
        self.assertEqual(result, date + timedelta(days=10/2))


class CalculateNormalizedBusinessDateTests(unittest.TestCase):
    """
    Test calendar:
        2018-01-01 - Mon (holiday)
        2018-01-02 - Tue
        2018-01-03 - Wed
        2018-01-04 - Thu
        2018-01-05 - Fri (holiday)
        2018-01-06 - Sat (weekend)
        2018-01-07 - Sun (weekend)
    """

    working_days_mock = {
        '2018-01-01': True,
        '2018-01-05': True,
    }

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_starts_on_non_working(self):
        date = datetime(2018, 1, 1, 12, 0, 0, tzinfo=TZ)
        result = calculate_normalized_business_date(date, timedelta(days=1), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 3, 0, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_starts_on_non_working_before_non_working(self):
        date = datetime(2017, 12, 31, 12, 0, 0, tzinfo=TZ)
        result = calculate_normalized_business_date(date, timedelta(days=1), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 3, 0, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_starts_on_working(self):
        date = datetime(2018, 1, 2, 12, 0, 0, tzinfo=TZ)
        result = calculate_normalized_business_date(date, timedelta(days=1), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 4, 0, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_ends_before_non_working(self):
        date = datetime(2018, 1, 2, 12, 0, 0, tzinfo=TZ)
        result = calculate_normalized_business_date(date, timedelta(days=2), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 5, 0, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_ends_on_non_working(self):
        date = datetime(2018, 1, 2, 12, 0, 0, tzinfo=TZ)
        result = calculate_normalized_business_date(date, timedelta(days=3), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 9, 0, 0, 0, tzinfo=TZ))

    @mock.patch('openprocurement.tender.core.utils.WORKING_DAYS', working_days_mock)
    def test_ends_after_non_working(self):
        date = datetime(2018, 1, 2, 12, 0, 0, tzinfo=TZ)
        result = calculate_normalized_business_date(date, timedelta(days=4), working_days=True)
        self.assertEqual(result, datetime(2018, 1, 10, 0, 0, 0, tzinfo=TZ))


class TestGetMonitoringAccelerator(unittest.TestCase):

    def test_acceleration_value(self):
        self.assertEqual(get_monitoring_accelerator({'monitoringDetails': 'accelerator=2'}), 2)

    def test_no_acceleration(self):
        self.assertEqual(get_monitoring_accelerator({}), 0)


class GetAccessTokenTests(unittest.TestCase):

    def test_token_query_param(self):
        self.assertEqual(get_access_token(
            request=mock.Mock(params={'acc_token': 'test_token'})),
            'test_token'
        )

    def test_token_headers(self):
        self.assertEqual(get_access_token(
            request=mock.Mock(params={}, headers={'X-Access-Token': 'test_token'})),
            'test_token'
        )

    def test_token_body(self):
        request = mock.Mock(
            method='POST',
            content_type='application/json',
            params={},
            headers={},
            json_body={
                'access': {
                    'token': 'test_token'
                }
            }
        )
        self.assertEqual(get_access_token(request=request), 'test_token')

    def test_no_token(self):
        request = mock.Mock(
            method='POST',
            content_type='application/json',
            params={},
            headers={},
            json_body={}
        )
        self.assertRaises(ValueError, get_access_token, request=request)


class CalculateNormalizedDateTest(unittest.TestCase):

    def test_calculate_ceil(self):
        self.assertEqual(
            calculate_normalized_date(datetime(2018, 1, 1, 12, 0, 0, tzinfo=TZ), ceil=True),
            datetime(2018, 1, 2, 0, 0, 0, tzinfo=TZ)
        )

    def test_calculate_no_ceil(self):
        self.assertEqual(
            calculate_normalized_date(datetime(2018, 1, 1, 12, 0, 0, tzinfo=TZ), ceil=False),
            datetime(2018, 1, 1, 0, 0, 0, tzinfo=TZ)
        )
