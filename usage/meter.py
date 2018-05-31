import datetime
import itertools
import query
import utils

from exc import InvalidTimeRangeError
from exc import NoSamplesError
from log import logging
from reading import Reading

logger = logging.getLogger('usage.meter')

EXTRA_TIME = 7200


def _cmp_sample(a, b):
    """Compare two samples.

    First compare the resource ids. Compare the timestamps if the
    resource ids are the same.

    :param a: First sample
    :param b: Second sample
    :return: Result of cmp function.
    :rtype: Integer
    """
    result = cmp(a.resource_id, b.resource_id)
    if result == 0:
        result = cmp(a.timestamp, b.timestamp)
    return result


class Meter:
    """
    Class for interacting with a ceilometer meter.
    """
    def __init__(self, client, name, max_samples=15000):
        """Init the meter.

        :param client: Ceilometer client
        :type client: ceilometerclient.client
        :param name: Name of the meter
        :type name: String
        :param max_samples: Max number of samples per query.
        :type max_samples: Integer
        """
        self.client = client
        self.name = name
        self.max_samples = max_samples

        # Extra time is 4 hours. 4 * 60 * 60 = 14400
        self._extra_time = datetime.timedelta(seconds=EXTRA_TIME)

    def last_non_deleted_sample(self, group):
        """Get last sample that is not in deleted or deleting.

        Starts at the end of the group and looks backward for the first sample
        that is not in a deleted or deleting status.

        If a sample cannot be found, just return the last sample.

        :param group: List of samples that are already sorted by timestamp.
        :type group: List
        :returns: Last non deleted status sample.
        :rtype: sample
        """
        deleted_status = set(['deleted', 'deleting'])
        for i in xrange(len(group) - 1, -1, -1):
            if group[i].resource_metadata.get('status') not in deleted_status:
                return group[i]
        return group[-1]

    def _reading_generator(self, samples, start, stop):
        """Yields one reading at a time.

        Samples are grouped by resource id(already sorted by resource id)
        and then used to create a reading object.

        :param samples: List of samples sorted by resource_id and timestamp.
        :type samples: List
        :param start: Reading start time
        :type start: Datetime
        :param stop: Reading stop time
        :type stop: Datetime
        :yields: Reading objects
        """
        # Yield a reading for each resource/meter pair
        for _, g in itertools.groupby(samples, lambda x: x.resource_id):
            try:
                yield Reading(list(g), start, stop)
            except NoSamplesError:
                continue

    def read(self, start=None, stop=None, q=None):
        """Read a meter.

        :param start: Start date and time.
        :type start: datetime
        :param stop: Stop date and time.
        :type stop: datetime
        :param q: List of filters excluding timestamp filters
        :type q: List
        :return: Value of reading
        :rtype: Float
        """
        # Default times to month to date
        default_start, default_stop = utils.mtd_range()
        if not start:
            start = default_start
        if not stop:
            stop = default_stop
        logger.info("Start: {}".format(start))
        logger.info("Stop:  {}".format(stop))
        logger.info("Meter name: {}".format(self.name))
        if start > stop:
            raise InvalidTimeRangeError(start, stop)

        # Add times to query. times are +- the extra time.
        q = q or []
        q.append(query.query(
            'timestamp', 'gt', start - self._extra_time, 'datetime'
        ))
        q.append(query.query(
            'timestamp', 'le', stop + self._extra_time, 'datetime'
        ))

        schedule = query.Scheduler(
            self.client,
            self.name,
            start - self._extra_time,
            stop + self._extra_time,
            q=[],
            max_samples=self.max_samples
        )
        for s_start, s_stop, s_query, s_count in schedule:
            logger.debug("{} - {} - {}".format(s_start, s_stop, s_count))
        logger.debug("Count of scheduled samples {}".format(schedule.count()))

        # Get samples
        samples = schedule.list()
        logger.debug(
            "{} samples according to sample-list.".format(len(samples))
        )

        # Convert timestamps from strings to datetime objects
        for s in samples:
            s.timestamp = utils.normalize_time(
                utils.parse_datetime(s.timestamp)
            )

        # Sort by resource id and then timestamps in ascending order
        samples.sort(cmp=_cmp_sample)

        # Return generator
        return self._reading_generator(samples, start, stop)
