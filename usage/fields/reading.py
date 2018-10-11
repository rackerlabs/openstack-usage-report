import ast
import volume_types

from usage import tag
from usage.conversions.time_units import seconds_to_hours
from usage.log import logging

_ALLOWED_RESOURCE_ATTRS = ['resource_id', 'project_id', 'metadata']

logger = logging.getLogger('usage.fields')


def _i_map(data):
    """Map lowercase insensitive keys to sensitive keys.

    :param data: Data to map
    :type data: Dict
    :returns: Map of insensitive to sensitive keys
    :rtype: Dict
    """
    return {key.lower(): key for key in data.iterkeys()}


def _i_get(data, i_map, key):
    """Get an item from data insensitively.

    :param data: Data with sensitive keys
    :type data: Dict
    :param i_map: Map of lowercase keys to real keys.
    :type i_map: Dict
    :param key: Sensitive key
    :type key: String
    :returns: Value
    :rtype: object
    """
    key = i_map.get(key.lower())
    return data.get(key) if key else None


def _get_reading_attr(reading, attr):
    """Get an attribute of a reading.

    :param reading: Meter reading.
    :type reading: usage.reading.Reading
    :param attr: Name of the attr
    :type attr: String
    :returns: Attribute if an allowed attribute or None
    :rtype: Object|None
    """
    if attr in _ALLOWED_RESOURCE_ATTRS:
        return getattr(reading, attr)
    return None


def metadata_field(key, r):
    """Get value of metadata field if present.

    Special field function that is not called like the others.
    Only accepts a key parameter and a reading.

    :param key: Metadata key. Looks like metadata:<real key>
    :type key: String
    :param reading: Meter reading.
    :type reading: usage.reading.Reading
    :return: Value of metadata key
    :rtype: String
    """
    value = None

    # Parse the actual key
    _, key = key.split(':', 1)

    metadata = _get_reading_attr(r, 'metadata')

    i_map = _i_map(metadata)

    # Try nova first nova metadata fields are metadata.<key>
    value = _i_get(metadata, i_map, 'metadata.{}'.format(key))

    # Try glance next. Glance metadata fields are properties.<key>
    if not value:
        value = _i_get(metadata, i_map, 'properties.{}'.format(key))

    # Try swift next.
    # Swift container metadata keys are in resource metadata
    # keyed by 'x-container-meta-<key>'
    if not value:
        value = _i_get(metadata, i_map, 'x-container-meta-{}'.format(key))

    # Try cinder next or glance snapshots next..
    # Cinder metadata fields are stored as a list of metadata objects.
    # Snapshot metadata fields are stored as a string repr of a dict
    if not value:
        data = metadata.get('metadata')
        if isinstance(data, unicode) or isinstance(data, str):
            try:
                data = ast.literal_eval(data)
                if isinstance(data, list):
                    for obj in data:
                        if obj.get('key').lower() == key.lower():
                            value = obj.get('value')
                            break
                elif isinstance(data, dict):
                    nested_i_map = _i_map(data)
                    value = _i_get(data, nested_i_map, key)
            except Exception:
                pass

    if value:
        tag.track(key, value)

    return value


def image_metadata_field(key, r):
    """Get value of image metadata field if present.

    Special field function that is not called like the others.
    Only accepts a key parameter and a reading.

    :param key: Image metadata key. Looks like image_metadata:<real key>
    :type key: String
    :param reading: Meter reading
    :type reading: usage.reading.Reading
    :return: Value of image metadata key
    :rtype: String
    """
    value = None
    # Parse out the key
    _, key = key.split(':', 1)
    metadata = _get_reading_attr(r, 'metadata')
    i_map = _i_map(metadata)

    value = _i_get(metadata, i_map, 'image_meta.{}'.format(key))
    return value


def availability_zone(d, i, r):
    """Get availability zone from reading metadata.

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: availability zone
    :rtype: String
    """
    return r.metadata.get('availability_zone', '')


def billing_period_end_date(d, i, r):
    """Get billing period start date

    Using the stop of the report

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: isoformatted stop date
    :rtype: String
    """
    return r.stop.isoformat()


def billing_period_start_date(d, i, r):
    """Get billing period start date

     Using the start of the reading.

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: isoformatted start date
    :rtype: String
    """
    return r.start.isoformat()


def cost(d, i, r):
    """Get cost as a combination of the item rate and reading value.

    The cost format comes from the report definition and will default to
    "{:.2f}",format(value)

    :param d: Report definition
    :type: d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter Reading.
    :type r: usage.reading.Reading
    """
    template = d.get('cost_format', '{:.2f}')
    value = float(r.value)
    cost = value * i.get('item_rate', 0)
    return template.format(cost)


def display_name(d, i, r):
    """Get the resource display name.

    :param d: Report definition.
    :type d: Dict
    :param i: Item definition.
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    """
    return r.metadata.get('display_name')


def hours(d, i, r):
    """Get the hours for the resource.

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    """
    return seconds_to_hours(
        float((r.usage_stop - r.usage_start).total_seconds())
    )


def instance_type(d, i, r):
    """get instance type.

    :param d: Report definition.
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    """
    return r.metadata.get('instance_type')


def payer_account_id(d, i, r):
    """Get payer account id

    Using the project id for now.

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: payer_account_id
    :rtype: String
    """
    return _get_reading_attr(r, 'project_id')


def project_id(d, i, r):
    """Get project_id

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: project_id
    :rtype: String
    """
    return _get_reading_attr(r, 'project_id')


def resource_id(d, i, r):
    """Get resource id from meter reading.

    :param d: Report definition
    :type: d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    """
    return _get_reading_attr(r, 'resource_id')


def timeinterval(d, i, r):
    """Get isoformatted time interval from reading.

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: Isoformatted date range
    :rtype: String
    """
    return '/'.join([r.start.isoformat(), r.stop.isoformat()])


def usage_account_id(d, i, r):
    """Get payer account id from reading.

    Using the project id for now

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: reading.project_id
    :rtype: String
    """
    return r.project_id


def usage_amount(d, i, r):
    """Get meter value

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: isoformatted usage_start_date
    :rtype: String
    """
    return r.value


def usage_end_date(d, i, r):
    """Get usage end date from reading.

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: isoformatted usage_start_date
    :rtype: String
    """
    return r.usage_stop.isoformat()


def usage_start_date(d, i, r):
    """Get usage start date from reading.

    :param d: Report definition
    :type d: Dict
    :param i: Item definition
    :type i: Dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: isoformatted usage_start_date
    :rtype: String
    """
    return r.usage_start.isoformat()


def volume_type(d, i, r):
    """Get volume type from reading.

    :param d: Report definition.
    :type d: Dict
    :param i: Item definition
    :type i: dict
    :param r: Meter reading
    :type r: usage.reading.Reading
    :return: Human readable name of volume type
    :rtype: str
    """
    volume_type_id = r.metadata.get('volume_type')
    return volume_types.name_from_id(volume_type_id)
