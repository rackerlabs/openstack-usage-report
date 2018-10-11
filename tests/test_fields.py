import datetime
import mock
import unittest

from fakes import FakeReading
from usage.fields import field_function
from usage.fields.item import billing_entity
from usage.fields.item import currency_code
from usage.fields.item import description
from usage.fields.item import item_rate
from usage.fields.item import line_item_type
from usage.fields.item import meter_name
from usage.fields.item import operation
from usage.fields.item import product_code
from usage.fields.item import product_name
from usage.fields.item import usage_type
from usage.fields.reading import availability_zone
from usage.fields.reading import billing_period_end_date
from usage.fields.reading import billing_period_start_date
from usage.fields.reading import cost
from usage.fields.reading import display_name
from usage.fields.reading import hours
from usage.fields.reading import image_metadata_field
from usage.fields.reading import instance_type
from usage.fields.reading import metadata_field
from usage.fields.reading import payer_account_id
from usage.fields.reading import project_id
from usage.fields.reading import resource_id
from usage.fields.reading import timeinterval
from usage.fields.reading import usage_account_id
from usage.fields.reading import usage_amount
from usage.fields.reading import usage_end_date
from usage.fields.reading import usage_start_date
from usage.fields.reading import volume_type
from usage.fields.report import invoice_id
from usage.exc import UnknownFieldFunctionError


def broken_field(d, i, r):
    raise Exception("I am broken.")
    return 'worked'


class TestFieldFunction(unittest.TestCase):
    """Tests the conversion plugin loaded."""
    def test_unknown_field_function(self):
        with self.assertRaises(UnknownFieldFunctionError):
            field_function('doesntexist', 'd', 'i', 'r')

    @mock.patch(
        'usage.fields.FIELD_FUNCTIONS',
        {'broken_field': broken_field}
    )
    def test_broken_field_function(self):
        self.assertTrue(
            field_function('broken_field', 'd', 'i', 'r') is None
        )


class TestMetadataField(unittest.TestCase):
    """Tests the metadata field function."""

    key = 'metadata:test'

    def test_metadata_field_not_present(self):
        r = FakeReading(metadata={})
        self.assertTrue(metadata_field(self.key, r) is None)

    def test_nova_metadata(self):
        metadata = {'metadata.test': 'nova'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field(self.key, r), 'nova')

        # Test insensitive metadata
        metadata = {'metadata.TeSt': 'nova'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field(self.key, r), 'nova')

        # Test insensitive key
        self.assertEquals(metadata_field('metadata:TEst', r), 'nova')

    def test_glance_metdata(self):
        metadata = {'properties.test': 'glance'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field(self.key, r), 'glance')

        # Test insensitive metadata
        metadata = {'properties.TeST': 'glance'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field(self.key, r), 'glance')

        # Test insensitive key
        self.assertEquals(metadata_field('metadata:tESt', r), 'glance')

    def test_snapshot_metadata(self):
        # Test snapshot metadata. Nested in resource metadata.
        metadata = {'metadata': unicode("{'tESt': 'glance'}")}
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field('metadata:TesT', r), 'glance')

    def test_cinder_metadata(self):
        metadata = {
            'metadata': unicode("[{'key': 'test', 'value': 'cinder'}]")
        }
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field(self.key, r), 'cinder')

        # Test insensitive metadata
        metadata = {
            'metadata': unicode("[{'key': 'TeSt', 'value': 'cinder'}]")
        }
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field(self.key, r), 'cinder')

        # Test insensitive key
        self.assertEquals(metadata_field('metadata:tEsT', r), 'cinder')

    def test_swift_metadata(self):
        metadata = {'x-container-meta-test': 'swift'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field(self.key, r), 'swift')

        # Test insensitive metadata
        metadata = {'X-Container-Meta-Test': 'swift'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field(self.key, r), 'swift')

        # Test insensitive key
        metadata = {'x-container-meta-test': 'swift'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(metadata_field('metadata:tESt', r), 'swift')


class TestImageMetadataField(unittest.TestCase):
    """Tests the image metadata field function."""
    key = 'image_metadata:test'

    def test_image_metadata(self):
        metadata = {'image_meta.test': 'value'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(image_metadata_field(self.key, r), 'value')

        # Test case insensitivity
        metadata = {'image_meta.TeST': 'value'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(
            image_metadata_field('image_metadata:tEsT', r),
            'value'
        )

        # Test missing metadata
        metadata = {}
        r = FakeReading(metadata=metadata)
        assert(image_metadata_field(self.key, r) is None)


class TestResourceId(unittest.TestCase):
    """Tests the resource_id field function."""
    def test_resource_id(self):
        r = FakeReading()
        self.assertEquals(resource_id(None, None, r), 'resource_id')


class TestPayerAccountId(unittest.TestCase):
    """Tests the payer_account_id field function."""
    def test_payer_account_id(self):
        r = FakeReading()
        self.assertEquals(payer_account_id(None, None, r), 'project_id')


class TestProjectId(unittest.TestCase):
    """Tests the project_id field function."""
    def test_project_id(self):
        r = FakeReading()
        self.assertEquals(project_id(None, None, r), 'project_id')


class TestTimeInterval(unittest.TestCase):
    """Tests the timeinterval field function."""
    def test_timeinterval(self):
        stop = datetime.datetime.utcnow()
        start = stop - datetime.timedelta(hours=1)
        r = FakeReading(start=start, stop=stop)
        expected = '{}/{}'.format(start.isoformat(), stop.isoformat())
        self.assertEquals(timeinterval(None, None, r), expected)


class TestInvoiceId(unittest.TestCase):
    """Tests the invoice id field function."""
    def test_invoice_id(self):
        # This function only returns the empty string right now.
        self.assertEquals(invoice_id(None, None, None), '')


class TestBillingEntity(unittest.TestCase):
    """Tests the billing entity field function."""
    def test_billing_entity(self):
        i = {'billing_entity': 'from_item'}
        d = {'billing_entity': 'from_definition'}
        self.assertEquals(billing_entity(d, i, None), 'from_item')
        self.assertEquals(billing_entity(d, {}, None), 'from_definition')


class TestBillingPeriodStartDate(unittest.TestCase):
    """Tests the billing period start date field function."""
    def test_billing_period_start_date(self):
        start = datetime.datetime.utcnow()
        r = FakeReading(start=start)
        self.assertEquals(
            billing_period_start_date(None, None, r),
            start.isoformat()
        )


class TestBillingPeriodEndDate(unittest.TestCase):
    """Tests the billing period end date field function."""
    def test_billing_period_end_date(self):
        stop = datetime.datetime.utcnow()
        r = FakeReading(stop=stop)
        self.assertEquals(
            billing_period_end_date(None, None, r),
            stop.isoformat()
        )


class TestCost(unittest.TestCase):
    """Tests the cost field function."""
    def test_cost(self):
        item = {'item_rate': 1.0}
        r = FakeReading(value='1.2345')
        # Test default {:.2f}
        self.assertEquals(cost({}, item, r), '1.23')

        # Test other
        d = {'cost_format': '{:.1f}'}
        self.assertEquals(cost(d, item, r), '1.2')


class TestDisplayName(unittest.TestCase):
    """Tests the display name field function."""
    def test_display_name(self):
        r = FakeReading()
        self.assertTrue(display_name(None, None, r) is None)
        r = FakeReading(metadata={'display_name': 'display_name'})
        self.assertEquals(display_name(None, None, r), 'display_name')


class TestHours(unittest.TestCase):
    """Tests the hours field function."""
    def test_hours(self):
        stop = datetime.datetime.utcnow()
        start = stop - datetime.timedelta(hours=1)
        r = FakeReading(start=start, stop=stop)
        self.assertEquals(hours(None, None, r), 1)

        stop = datetime.datetime.utcnow()
        start = stop - datetime.timedelta(hours=0.5)
        r = FakeReading(start=start, stop=stop)
        self.assertEquals(hours(None, None, r), 0.5)


class TestInstanceType(unittest.TestCase):
    """Tests the instance type field function."""
    def test_instance_type(self):
        r = FakeReading()
        self.assertTrue(instance_type(None, None, r) is None)
        r = FakeReading(metadata={'instance_type': 'instance_type'})
        self.assertEquals(instance_type(None, None, r), 'instance_type')


class TestUsageAccountId(unittest.TestCase):
    """Tests the usage account id field function."""
    def test_usage_account_id(self):
        r = FakeReading()
        self.assertEquals(usage_account_id(None, None, r), 'project_id')


class TestLineItemType(unittest.TestCase):
    """Tests the line item type field function."""
    def test_line_item_type(self):
        item = {'line_item_type': 'line_item_type'}
        self.assertTrue(line_item_type(None, {}, None) is '')
        self.assertEquals(line_item_type(None, item, None), 'line_item_type')


class TestMeterName(unittest.TestCase):
    """Tests the meter name field function."""
    def test_meter_name(self):
        item = {}
        self.assertTrue(meter_name(None, item, None) is None)
        item['meter_name'] = 'test'
        self.assertEquals(meter_name(None, item, None), 'test')


class TestProductCode(unittest.TestCase):
    """Tests the product code field function."""
    def test_product_code(self):
        item = {'product_code': 'product_code'}
        self.assertTrue(product_code(None, {}, None) is '')
        self.assertEquals(product_code(None, item, None), 'product_code')


class TestProductName(unittest.TestCase):
    """Tests the product name field function."""
    def test_product_name(self):
        item = {'product_name': 'product_name'}
        self.assertTrue(product_name(None, {}, None) is '')
        self.assertEquals(product_name(None, item, None), 'product_name')


class TestUsageType(unittest.TestCase):
    """Tests the usage type field function."""
    def test_usage_type(self):
        item = {'usage_type': 'usage_type'}
        self.assertTrue(usage_type(None, {}, None) is '')
        self.assertEquals(usage_type(None, item, None), 'usage_type')


class TestOperation(unittest.TestCase):
    """Tests the operation field function."""
    def test_operation(self):
        item = {'operation': 'operation'}
        self.assertTrue(operation(None, {}, None) is '')
        self.assertEquals(operation(None, item, None), 'operation')


class TestUsageStartDate(unittest.TestCase):
    """Tests the usage start date field function."""
    def test_usage_start_date(self):
        start = datetime.datetime.utcnow()
        r = FakeReading(start=start)
        self.assertEquals(usage_start_date(None, None, r), start.isoformat())


class TestUsageEndDate(unittest.TestCase):
    """Tests the usage end date field function."""
    def test_usage_end_date(self):
        stop = datetime.datetime.utcnow()
        r = FakeReading(stop=stop)
        self.assertEquals(usage_end_date(None, None, r), stop.isoformat())


class TestAvailabilityZone(unittest.TestCase):
    """Tests the availability zone field function."""
    def test_availability_zone(self):
        metadata = {}
        r = FakeReading(metadata=metadata)
        self.assertTrue(availability_zone(None, None, r) is '')

        metadata = {'availability_zone': 'availability_zone'}
        r = FakeReading(metadata=metadata)
        self.assertEquals(
            availability_zone(None, None, r),
            'availability_zone'
        )


class TestUsageAmount(unittest.TestCase):
    """Tests the usage amount field function."""
    def test_usage_amount(self):
        r = FakeReading()
        self.assertEquals(usage_amount(None, None, r), 'value')


class TestCurrencyCode(unittest.TestCase):
    """Tests the currency code field function."""
    def test_currency_code(self):
        i = {'currency_code': 'from_item'}
        d = {'currency_code': 'from_definition'}
        self.assertTrue(currency_code({}, {}, None) is '')
        self.assertEquals(currency_code(d, i, None), 'from_item')
        self.assertEquals(currency_code(d, {}, None), 'from_definition')


class TestItemRate(unittest.TestCase):
    """Tests the item rate field function."""
    def test_item_rate(self):
        self.assertEquals(item_rate(None, {}, None), 0.0)
        i = {'item_rate': 'item_rate'}
        self.assertEquals(item_rate(None, i, None), 'item_rate')


class TestDescription(unittest.TestCase):
    """Tests the description field function."""
    def test_description(self):
        i = {'description': 'description'}
        self.assertTrue(description(None, {}, None) is '')
        self.assertEquals(description(None, i, None), 'description')


class TestVolumeType(unittest.TestCase):
    """Tests the volume_type field function."""

    @mock.patch(
        'usage.fields.reading.volume_types.name_from_id',
        return_value='test_volume_name'
    )
    def test_volume_type_none(self, mock_name_from_id):
        metadata = {}
        r = FakeReading(metadata=metadata)
        self.assertEquals('test_volume_name', volume_type(None, None, r))

        metadata = {'volume_type': 'some-id'}
        r = FakeReading(metadata=metadata)
        self.assertEquals('test_volume_name', volume_type(None, None, r))
