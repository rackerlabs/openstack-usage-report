import datetime
import mock
import unittest

from fakes import FakeReportArgs
from fakes import FakeSummaryArgs
from usage import output
from usage.console import console_report
from usage.console import console_summary


class TestConsoleSummary(unittest.TestCase):
    """Tests the Console Summary function."""
    @mock.patch('usage.console.logger')
    @mock.patch('usage.console.config')
    #@mock.patch('usage.console.ClientManager')
    @mock.patch('usage.console.create_client_manager')
    @mock.patch('usage.console.summary_parser.parse_args')
    @mock.patch('usage.console.Summary')
    def test_console_summary(self,
                             m_summary,
                             m_args,
                             m_clients,
                             m_config,
                             m_logger):
        m_args.return_value = FakeSummaryArgs()
        console_summary()
        self.assertEquals('csv_file', m_summary.call_args[1]['input_file'])
        self.assertEquals('project_id_field',
                          m_summary.call_args[1]['project_id_column'])
        self.assertEquals('cost_field', m_summary.call_args[1]['cost_column'])
        self.assertEquals('group_by', m_summary.call_args[1]['group_by'])


class TestConsoleReport(unittest.TestCase):
    """Tests the Console Report function."""

    @mock.patch('usage.console.tag.all', return_value='all')
    @mock.patch('usage.console.logger')
    @mock.patch('usage.console.config')
    #@mock.patch('usage.console.ClientManager')
    @mock.patch('usage.console.create_client_manager')
    @mock.patch('usage.console.utils')
    @mock.patch('usage.console.Report')
    @mock.patch('usage.console.report_parser.parse_args')
    def test_console_report(self,
                            m_args,
                            m_report,
                            m_utils,
                            m_clients,
                            m_config,
                            m_logger,
                            m_all):

        month_stop = datetime.datetime.utcnow()
        month_start = month_stop - datetime.timedelta(days=30)

        day_stop = datetime.datetime.utcnow()
        day_start = day_stop - datetime.timedelta(days=1)

        last_hour_stop = datetime.datetime.utcnow()
        last_hour_start = last_hour_stop - datetime.timedelta(hours=1)

        arb_stop = datetime.datetime.utcnow()
        arb_start = arb_stop - datetime.timedelta(days=10, hours=10)

        m_utils.mtd_range = \
            mock.Mock(return_value=(month_start, month_stop))
        m_utils.today_range = \
            mock.Mock(return_value=(day_start, day_stop))
        m_utils.last_hour_range = \
            mock.Mock(return_value=(last_hour_start, last_hour_stop))

        # Test that mtd is used with no time args
        m_args.return_value = FakeReportArgs()
        console_report()
        self.assertEquals(month_start, m_report.call_args[1]['start'])
        self.assertEquals(month_stop, m_report.call_args[1]['stop'])
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Mtd))

        # Test that stdout putput is used
        m_args.return_value = FakeReportArgs(use_stdout=True)
        console_report()
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Stream))

        # Test that mtd is used with mtd set to true
        m_args.return_value = FakeReportArgs(
            mtd=True, last_hour=True, today=True, start=True, stop=True
        )
        console_report()
        self.assertEquals(month_start, m_report.call_args[1]['start'])
        self.assertEquals(month_stop, m_report.call_args[1]['stop'])
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Mtd))

        # Test that stdout putput is used
        m_args.return_value = FakeReportArgs(
            mtd=True,
            last_hour=True,
            today=True,
            start=True,
            stop=True,
            use_stdout=True
        )
        console_report()
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Stream))

        # Test that today is used with day set to true and mtd false.
        m_args.return_value = FakeReportArgs(last_hour=True, today=True)
        console_report()
        self.assertEquals(day_start, m_report.call_args[1]['start'])
        self.assertEquals(day_stop, m_report.call_args[1]['stop'])
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Daily))

        # Test that stdout is used
        m_args.return_value = FakeReportArgs(
            last_hour=True,
            today=True,
            use_stdout=True
        )
        console_report()
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Stream))

        # Test that last hour is used when set to true
        m_args.return_value = FakeReportArgs(last_hour=True)
        console_report()
        self.assertEquals(last_hour_start, m_report.call_args[1]['start'])
        self.assertEquals(last_hour_stop, m_report.call_args[1]['stop'])
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Hourly))

        # Test that stdout is used
        m_args.return_value = FakeReportArgs(last_hour=True, use_stdout=True)
        console_report()
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Stream))

        # Test that exception is raised when stop is provided without start
        m_args.return_value = FakeReportArgs(start=None, stop='stop')
        with self.assertRaises(Exception):
            console_report()

        # Test that start and stop are used when provided
        m_args.return_value = FakeReportArgs(start=arb_start, stop=arb_stop)
        console_report()
        self.assertEquals(arb_start, m_report.call_args[1]['start'])
        self.assertEquals(arb_stop, m_report.call_args[1]['stop'])
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Other))

        # Test that stdout is used
        m_args.return_value = FakeReportArgs(
            start=arb_start,
            stop=arb_stop,
            use_stdout=True
        )
        console_report()
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Stream))

        # Test that stop is defaulted correctly when start is provided
        # without a stop
        m_args.return_value = FakeReportArgs(start=arb_start, stop=None)
        console_report()
        self.assertEquals(arb_start, m_report.call_args[1]['start'])
        self.assertEquals(month_stop, m_report.call_args[1]['stop'])
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Other))

        # Test that stdout is used
        m_args.return_value = FakeReportArgs(
            start=arb_start,
            stop=None,
            use_stdout=True
        )
        console_report()
        self.assertTrue(isinstance(m_report.call_args[0][2], output.Stream))

        # Assert that tag.all() has not been called
        self.assertEquals(m_all.call_count, 0)

        # Test that tags.all() is called when show_tags is provided
        m_args.return_value = FakeReportArgs(show_tags=True)
        console_report()
        self.assertEquals(m_all.call_count, 1)
