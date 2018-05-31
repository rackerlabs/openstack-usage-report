import copy
import time

from log import logging

logger = logging.getLogger('usage.query')

MIN_TIME_DELTA = 0.010

_OPS = {
    "gt": ">",
    "ge": ">=",
    "lt": "<",
    "le": "<="
}


def query(field, op, value, type=''):
    """Assemble a dict representing a query filter.

    :param field: Field to query
    :type field: String
    :param op: Query operator
    :type op: String
    :param value: Value to query
    :type value: String
    :param type: Type of the value
    :type type: String
    :return: Query filter dict
    :rtype: Dict
    """
    return {
        'field': field,
        'op': op,
        'value': value,
        'type': type
    }


def _query_string(q):
    """Creates query string as it would be used from the cli.

    :param q: List of query filters
    :type q: List
    :returns: Cli query string
    :rtype: string
    """
    filters = []
    template = "{}{}{}"
    for f in q:
        value = f.get('value')
        if f.get("type") == 'datetime':
            value = value.isoformat()
        filters.append(
            template.format(f.get('field'), _OPS.get(f.get('op')), value)
        )
    return ";".join(filters)


def _sample_list_to_cli(meter_name, q, limit):
    """Creates a sample list command as it would be used from cli.

    :param meter_name: Name of the meter
    :type meter_name: String
    :param q: List of query filters
    :type q: List
    :param limit: Number of samples to return
    :type limit: Integer
    :returns: Cli string.
    :rtype: String
    """
    return 'ceilometer sample-list -m {} -q "{}" --limit {}'.format(
        meter_name,
        _query_string(q),
        limit
    )


def _count_to_cli(meter_name, q):
    """Creates a count command as it would be used from cli.

    :param meter_name: Name of the meter
    :type meter_name: String
    :param q: List of query filters
    :type q: List
    :returns: Cli string.
    :rtype: String
    """
    return 'ceilometer statistics -m {} -q "{}" -a count'.format(
        meter_name,
        _query_string(q)
    )


class Scheduler(object):

    def __init__(self,
                 client,
                 meter_name,
                 start,
                 stop,
                 q=None,
                 max_samples=500):
        """Inits the schedule

        :param client: Ceilometer client
        :type client: Ceilometer client
        :param meter_name: Name of the meter to read
        :type meter_name: String
        :param start: Start time
        :type start: datetime.datetime
        :param stop: Stop time
        :type stop: datetime.datetime
        :param q: List of query filters excluding time
        :type q: List
        :param max_samples: Number of maximum samples per time chunk.
        :type max_samples: Integer
        """
        self.client = client
        self.meter_name = meter_name
        self.schedule = []
        self.max_samples = max_samples
        self.base_q = q or []
        self._schedule(start, stop)

    def _count(self, q):
        """Get a count of samples matching q.

        Since ceilometer does not support sample paging and a default limit of
        100 samples, we need to use stats to count the samples and change the
        limit from 100 the actual number of samples.

        :param q: Listg of filters.
        :type q: List
        :return: Count of samples
        :rtype: Integer
        """
        # Get count of samples
        logger.debug(_count_to_cli(self.meter_name, q))
        p_start = time.time()
        stats = self.client.statistics.list(
            meter_name=self.meter_name,
            q=q,
            aggregates=[{'func': 'count'}]
        )
        logger.debug(
            "Count finished in {} seconds.".format(time.time() - p_start)
        )
        if not stats:
            return 0
        return stats[0].count

    def _schedule(self, start, stop):
        """Creates a schedule of queries.

        Appends a query tuple to this objects schedule list.

        Queries the count of samples over a chunk of time. If the count
        exceeds max samples, the time is halved and then each half is
        recuriively examined until we have chunks of time with less than
        the max number of samples.

        :param start: Start datetime
        :type start: datetime.datetime
        :param stop: Stop datetime
        :type stop: datetime.datetime
        """
        # Copy base query. Each query will be the same aside from times.
        this_q = copy.copy(self.base_q)
        this_q.append(query('timestamp', 'gt', start, 'datetime'))
        this_q.append(query('timestamp', 'le', stop, 'datetime'))
        count = self._count(this_q)
        d = (stop - start) / 2
        logger.debug("Checking {} - {} - {}".format(start, stop, count))
        if count > self.max_samples and d.total_seconds() > MIN_TIME_DELTA:
            self._schedule(start, start + d)
            self._schedule(start + d, stop)
        else:
            self.schedule.append((start, stop, this_q, count))

    def __iter__(self):
        """Generator for iterating over the schedule."""
        for item in self.schedule:
            yield item

    def count(self):
        """Returns the total number of samples expected by the schedule.

        :returns: Number of total samples
        :rtype: Integer
        """
        total = 0
        for _, _, _, count in self:
            total += count
        return total

    def list(self):
        """Gets a list of all samples.

        :returns: All samples
        :rtype: List
        """
        total_queries = len(self.schedule)
        samples = []
        for i, item in enumerate(self):
            logger.info(
                "Performing query {} of {}".format(i + 1, total_queries)
            )
            _, _, q, limit = item
            logger.debug(_sample_list_to_cli(self.meter_name, q, limit))
            p_start = time.time()
            samples.extend(
                self.client.samples.list(
                    meter_name=self.meter_name,
                    q=q,
                    limit=limit
                )
            )
            logger.debug(
                "sample-list finished in {} seconds."
                .format(time.time() - p_start)
            )
        return samples
