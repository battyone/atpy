import unittest

from influxdb import InfluxDBClient
from pandas.util.testing import assert_frame_equal

import atpy.data.cache.influxdb_cache_requests as inf_cache
from atpy.data.iqfeed.iqfeed_bar_data_provider import *
from atpy.data.iqfeed.iqfeed_influxdb_cache import *
from atpy.data.iqfeed.iqfeed_influxdb_cache_requests import get_cache_fundamentals
from pyevents.events import AsyncListeners


class TestInfluxDBCache(unittest.TestCase):
    """
    Test InfluxDBCache
    """

    def setUp(self):
        events.reset()
        events.use_global_event_bus()
        self._client_factory = ClientFactory(host='localhost', port=8086, username='root', password='root', database='test_cache')

        self._client = self._client_factory.new_df_client()

        self._client.drop_database('test_cache')
        self._client.create_database('test_cache')
        self._client.switch_database('test_cache')

    def tearDown(self):
        self._client.drop_database('test_cache')
        self._client.close()

    def test_streaming_cache(self):
        client = self._client
        _self = self

        e = threading.Event()

        class InfluxDBCacheTest(IQFeedInfluxDBCache):

            def on_event(self, event):
                super().on_event(event)
                if self._use_stream_events and event['type'] == 'bar':
                    with self._lock:
                        cached = client.query("select * from bars")
                        _self.assertTrue(isinstance(cached, dict))
                        _self.assertTrue(isinstance(cached['bars'], pd.DataFrame))
                        _self.assertFalse(cached['bars'].empty)

                        symbols = list(cached['bars']['symbol'])
                        _self.assertTrue('IBM' in symbols or 'GOOG' in symbols)
                        _self.assertEqual(cached['bars']['interval'][0], '3600_s')

                        e.set()

        listeners = AsyncListeners()
        with IQFeedBarDataListener(listeners=listeners, mkt_snapshot_depth=3, interval_len=3600), \
                IQFeedHistoryProvider(num_connections=2) as history, \
                InfluxDBCacheTest(client_factory=self._client_factory, history=history, listeners=listeners, use_stream_events=True, time_delta_back=relativedelta(days=3)):
            listeners({'type': 'watch_bars', 'data': {'symbol': ['GOOG', 'IBM'], 'update': 1}})

            e.wait()

    def test_update_to_latest(self):
        with IQFeedHistoryProvider(num_connections=2) as history, \
                IQFeedInfluxDBCache(client_factory=self._client_factory, use_stream_events=True, history=history, time_delta_back=relativedelta(days=30)) as cache:

            cache_requests = inf_cache.InfluxDBOHLCRequest(client=self._client, interval_len=3600, interval_type='s')

            end_prd = datetime.datetime(2017, 3, 2)
            filters = (BarsInPeriodFilter(ticker="IBM", bgn_prd=datetime.datetime(2017, 3, 1), end_prd=end_prd, interval_len=3600, ascend=True, interval_type='s'),
                       BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(2017, 3, 1), end_prd=end_prd, interval_len=3600, ascend=True, interval_type='s'),
                       BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(2017, 3, 1), end_prd=end_prd, interval_len=600, ascend=True, interval_type='s'))

            filters_no_limit = (BarsInPeriodFilter(ticker="IBM", bgn_prd=datetime.datetime(2017, 3, 1), end_prd=None, interval_len=3600, ascend=True, interval_type='s'),
                                BarsInPeriodFilter(ticker="AAPL", bgn_prd=datetime.datetime(2017, 3, 1), end_prd=None, interval_len=3600, ascend=True, interval_type='s'))

            data = [history.request_data(f, sync_timestamps=False, adjust_data=False) for f in filters]

            for datum, f in zip(data, filters):
                datum.drop('timestamp', axis=1, inplace=True)
                datum['interval'] = str(f.interval_len) + '_' + f.interval_type
                cache.client.write_points(datum, 'bars', protocol='line', tag_columns=['symbol', 'interval'], time_precision='s')

            latest_old = cache.ranges
            cache.update_to_latest({('AAPL', 3600, 's'), ('MSFT', 3600, 's'), ('MSFT', 600, 's')})

            latest_current = cache.ranges
            self.assertEqual(len(latest_current), len(latest_old) + 2)
            self.assertEqual(len([k for k in latest_current.keys() & latest_old.keys()]) + 2, len(latest_current))
            for k in latest_current.keys() & latest_old.keys():
                self.assertGreater(latest_current[k][1], latest_old[k][1])

            data_no_limit = [history.request_data(f, sync_timestamps=False, adjust_data=False) for f in filters_no_limit]
            cache_data_no_limit = [cache_requests.request(symbol=f.ticker, bgn_prd=f.bgn_prd)[0] for f in filters_no_limit]
            for df1, df2 in zip(data_no_limit, cache_data_no_limit):
                assert_frame_equal(df1, df2)

    def test_update_fundamentals(self):
        with IQFeedInfluxDBCache(client_factory=self._client_factory) as cache:
            funds = get_fundamentals({'IBM', 'AAPL', 'GOOG', 'MSFT'})
            cache.update_fundamentals(list(funds.values()))
            result = get_cache_fundamentals(cache.client, ['IBM', 'AAPL', 'GOOG', 'MSFT'])

        self.assertEqual(len(result), 4)
        self.assertEqual({k for k in result.keys()}, {'IBM', 'AAPL', 'GOOG', 'MSFT'})
        self.assertGreater(len(result['IBM']), 0)

    def test_update_adjustments(self):
        with IQFeedInfluxDBCache(client_factory=self._client_factory) as cache:
            funds = get_fundamentals({'IBM', 'AAPL', 'GOOG', 'MSFT'})
            cache.update_splits_dividends(list(funds.values()))
            result = list(InfluxDBClient.query(self._client, "SELECT * FROM splits_dividends").get_points())

            adjustments = inf_cache.get_adjustments(client=self._client, symbol=['IBM', 'AAPL'], data_provider='iqfeed')

        self.assertEqual(len(adjustments), 2)
        self.assertTrue(result[0]['symbol'] in {'IBM', 'AAPL'})
        self.assertTrue(isinstance(result[0]['value'], float))


if __name__ == '__main__':
    unittest.main()
