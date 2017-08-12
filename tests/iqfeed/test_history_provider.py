import unittest
import shutil


from atpy.data.iqfeed.iqfeed_history_provider import *
from atpy.data.iqfeed.history_util import get_bar_mean_std


class TestIQFeedHistory(unittest.TestCase):
    """
    IQFeed history provider test, which checks whether the class works in basic terms
    """

    def test_ticks(self):
        filter_provider = DefaultFilterProvider()
        filter_provider += TicksFilter(ticker="IBM", max_ticks=20)

        try:
            with IQFeedHistoryListener(minibatch=4, fire_batches=True, fire_ticks=True, filter_provider=filter_provider, lmdb_path='/tmp/test_history_provider_test_ticks_column_mode') as listener, listener.minibatch_provider() as provider:
                listener.start()

                e1 = threading.Event()

                def process_tick(event):
                    try:
                        data = event['data']
                        self.assertEqual(len(list(data.keys())), 14)
                    finally:
                        e1.set()

                listener.process_datum += process_tick

                e2 = threading.Event()

                def process_batch_listener_column(event):
                    try:
                        batch = event['data']
                        self.assertEqual(batch.shape, (20, 14))
                    finally:
                        e2.set()

                listener.process_batch += process_batch_listener_column

                e3 = threading.Event()

                def process_minibatch_listener_column(event):
                    try:
                        batch = event['data']
                        self.assertEqual(batch.shape, (4, 14))
                    finally:
                        e3.set()

                listener.process_minibatch += process_minibatch_listener_column

                for i, d in enumerate(provider):
                    self.assertEqual(d.shape, (4, 14))

                    self.assertNotEqual(d['TickID'].iloc[0], d['TickID'].iloc[1])

                    if i == 1:
                        break

                e2.wait()
                e3.wait()
        finally:
            shutil.rmtree('/tmp/test_history_provider_test_ticks_column_mode')

    def test_multiple_ticks(self):
        filter_provider = DefaultFilterProvider()
        filter_provider += TicksFilter(ticker=["IBM", "AAPL"], max_ticks=100)

        with IQFeedHistoryListener(minibatch=4, fire_batches=True, fire_ticks=True, filter_provider=filter_provider) as listener, listener.minibatch_provider() as provider:
            listener.start()

            e1 = threading.Event()

            def process_tick(event):
                try:
                    data = event['data']
                    self.assertEqual(len(list(data.keys())), 2)
                    self.assertEqual(len(list(data['IBM'].keys())), 14)
                    self.assertEqual(len(list(data['AAPL'].keys())), 14)
                finally:
                    e1.set()

            listener.process_datum += process_tick

            e2 = threading.Event()

            def process_batch_listener_column(event):
                try:
                    batch = event['data']
                    self.assertEqual(batch['IBM'].shape[1], 14)
                    self.assertEqual(batch['AAPL'].shape[1], 14)
                finally:
                    e2.set()

            listener.process_batch += process_batch_listener_column

            e3 = threading.Event()

            def process_minibatch_listener_column(event):
                try:
                    batch = event['data']
                    self.assertEqual(batch['IBM'].shape, (4, 14))
                    self.assertEqual(batch['AAPL'].shape, (4, 14))
                finally:
                    e3.set()

            listener.process_minibatch += process_minibatch_listener_column

            for i, d in enumerate(provider):
                self.assertEqual(d['IBM'].shape, (4, 14))
                self.assertEqual(d['AAPL'].shape, (4, 14))

                self.assertEqual(d['IBM']['Time Stamp'].iloc[0], d['AAPL']['Time Stamp'].iloc[0])
                self.assertNotEqual(d['IBM']['Time Stamp'].iloc[0], d['AAPL']['Time Stamp'].iloc[1])

                if i == 1:
                    break

            e2.wait()
            e3.wait()

    def test_bar(self):
        filter_provider = DefaultFilterProvider()
        filter_provider += BarsFilter(ticker="IBM", interval_len=60, interval_type='s', max_bars=20)

        with IQFeedHistoryListener(minibatch=4, fire_batches=True, fire_ticks=True, filter_provider=filter_provider) as listener, listener.minibatch_provider() as provider:
            listener.start()

            e1 = threading.Event()

            def process_bar(event):
                data = event['data']
                self.assertEqual(len(list(data.keys())), 9)
                e1.set()

            listener.process_datum += process_bar

            e2 = threading.Event()

            def process_batch_listener_column(event):
                batch = event['data']
                self.assertEqual(batch.shape, (20, 9))
                e2.set()

            listener.process_batch += process_batch_listener_column

            e3 = threading.Event()

            def process_minibatch_listener_column(event):
                batch = event['data']
                self.assertEqual(batch.shape, (4, 9))
                e3.set()

            listener.process_minibatch += process_minibatch_listener_column

            for i, d in enumerate(provider):
                self.assertEqual(d.shape, (4, 9))
                self.assertNotEqual(d['Time Stamp'].iloc[0], d['Time Stamp'].iloc[1])

                if i == 1:
                    break

            e2.wait()
            e3.wait()

    def test_bars(self):
        batch_len = 20
        filter_provider = DefaultFilterProvider()
        filter_provider += BarsFilter(ticker=["IBM", "AAPL", "GOOG"], interval_len=60, interval_type='s', max_bars=batch_len)

        with IQFeedHistoryListener(minibatch=4, fire_batches=True, fire_ticks=True, filter_provider=filter_provider) as listener, listener.minibatch_provider() as provider:
            listener.start()

            e1 = threading.Event()

            def process_bar(event):
                data = event['data']
                self.assertEqual(data.shape, (3, 9))
                self.assertEqual(len(list(data.loc['IBM'].keys())), 9)
                self.assertEqual(len(list(data.loc['AAPL'].keys())), 9)
                e1.set()

            listener.process_datum += process_bar

            e2 = threading.Event()

            def process_batch_listener_column(event):
                batch = event['data']
                self.assertEqual(len(batch.index.levels), 2)
                self.assertEqual(len(batch.index.levels[0]), 3)

                self.assertGreaterEqual(len(batch.index.levels[1]), batch_len)

                self.assertEqual(batch.loc['AAPL'].shape[1], 9)
                self.assertEqual(batch.loc['IBM'].shape[1], 9)

                self.assertGreaterEqual(len(batch.loc['AAPL'][batch.loc['IBM'].columns[0]]), batch_len)
                e2.set()

            listener.process_batch += process_batch_listener_column

            e3 = threading.Event()

            def process_minibatch_listener_column(event):
                batch = event['data']
                self.assertEqual(len(batch.index.levels), 2)
                self.assertEqual(batch.loc['AAPL'].shape, (4, 9))
                self.assertEqual(batch.loc['IBM'].shape, (4, 9))
                self.assertEqual(len(batch.loc['AAPL'][batch.loc['IBM'].columns[0]]), 4)
                e3.set()

            listener.process_minibatch += process_minibatch_listener_column

            for i, d in enumerate(provider):
                self.assertEqual(len(d.index.levels), 2)
                self.assertEqual(d.loc['AAPL'].shape, (4, 9))
                self.assertEqual(d.loc['IBM'].shape, (4, 9))
                self.assertEqual(len(d.loc['AAPL'][d.loc['IBM'].columns[0]]), 4)

                self.assertEqual(d.loc['IBM'].index[0], d.loc['AAPL'].index[0])
                self.assertNotEqual(d.loc['IBM'].index[0], d.loc['AAPL'].index[1])

                if i == 1:
                    break

            e2.wait()
            e3.wait()

    def test_bars_2(self):
        filter_provider = DefaultFilterProvider()
        filter_provider += BarsInPeriodFilter(ticker=["IBM", "AAPL"], bgn_prd=datetime.datetime(2017, 3, 1), end_prd=datetime.datetime(2017, 3, 2), interval_len=60, ascend=True, interval_type='s', max_ticks=20)

        try:
            with IQFeedHistoryListener(minibatch=4, fire_batches=True, fire_ticks=True, num_connections=2, filter_provider=filter_provider, lmdb_path='/tmp/test_history_provider_test_bars_row_mode') as listener, listener.minibatch_provider() as provider:
                listener.start()

                e1 = threading.Event()

                def process_bar(event):
                    data = event['data']
                    self.assertEqual(data.shape, (2, 9))
                    self.assertEqual(len(list(data.loc['IBM'].keys())), 9)
                    self.assertEqual(len(list(data.loc['AAPL'].keys())), 9)
                    e1.set()

                listener.process_datum += process_bar

                e2 = threading.Event()

                def process_batch_listener_column(event):
                    batch = event['data']
                    self.assertEqual(len(batch.index.levels), 2)
                    self.assertEqual(batch.loc['AAPL'].shape[1], 9)
                    self.assertEqual(batch.loc['IBM'].shape[1], 9)
                    e2.set()

                listener.process_batch += process_batch_listener_column

                e3 = threading.Event()

                def process_minibatch_listener_column(event):
                    batch = event['data']
                    self.assertEqual(len(batch.index.levels), 2)
                    self.assertEqual(batch.loc['AAPL'].shape, (4, 9))
                    self.assertEqual(batch.loc['IBM'].shape, (4, 9))
                    self.assertEqual(len(list(batch.loc['AAPL'][batch.loc['IBM'].columns[0]])), 4)
                    e3.set()

                listener.process_minibatch += process_minibatch_listener_column

                for i, d in enumerate(provider):
                    self.assertEqual(len(d.index.levels), 2)
                    self.assertEqual(d.loc['AAPL'].shape, (4, 9))
                    self.assertEqual(d.loc['IBM'].shape, (4, 9))
                    self.assertEqual(len(list(d.loc['AAPL'][d.loc['IBM'].columns[0]])), 4)

                    self.assertEqual(d.loc['IBM'].index[0], d.loc['AAPL'].index[0])
                    self.assertNotEqual(d.loc['IBM'].index[0], d.loc['AAPL'].index[1])

                    if i == 1:
                        break

            e2.wait()
            e3.wait()
        finally:
            shutil.rmtree('/tmp/test_history_provider_test_bars_row_mode')

    def test_bar_adjust(self):
        filter_provider = DefaultFilterProvider()
        filter_provider += BarsInPeriodFilter(ticker="PLUS", bgn_prd=datetime.datetime(2017, 3, 31), end_prd=datetime.datetime(2017, 4, 5), interval_len=3600, ascend=True, interval_type='s', max_ticks=100)

        try:
            with IQFeedHistoryListener(fire_batches=True, fire_ticks=True, filter_provider=filter_provider, lmdb_path='/tmp/test_history_provider_test_bars_row_mode') as listener, listener.batch_provider() as provider:
                listener.start()

                e1 = threading.Event()

                def process_bar(event):
                    try:
                        self.assertLess(event['data']['Open'], 68)
                        self.assertGreater(event['data']['Open'], 65)
                    finally:
                        e1.set()

                listener.process_datum += process_bar

                e1.wait()

                for i, d in enumerate(provider):
                    self.assertLess(d['Open'].max(), 68)
                    self.assertGreater(d['Open'].min(), 65)

                    if i == 1:
                        break
        finally:
            shutil.rmtree('/tmp/test_history_provider_test_bars_row_mode')

    def test_daily(self):
        filter_provider = DefaultFilterProvider()
        filter_provider += BarsDailyFilter(ticker="IBM", num_days=20)

        with IQFeedHistoryListener(minibatch=4, fire_batches=True, fire_ticks=True, filter_provider=filter_provider) as listener, listener.minibatch_provider() as provider:
            listener.start()

            e1 = threading.Event()

            def process_tick(event):
                data = event['data']
                self.assertEqual(len(list(data.keys())), 8)
                e1.set()

            listener.process_datum += process_tick

            e2 = threading.Event()

            def process_batch_listener_column(event):
                batch = event['data']
                self.assertEqual(batch.shape, (20, 8))
                e2.set()

            listener.process_batch += process_batch_listener_column

            e3 = threading.Event()

            def process_minibatch_listener_column(event):
                batch = event['data']
                self.assertEqual(batch.shape, (4, 8))
                e3.set()

            listener.process_minibatch += process_minibatch_listener_column

            for i, d in enumerate(provider):
                self.assertEqual(d.shape, (4, 8))
                self.assertNotEqual(d['Date'].iloc[0], d['Date'].iloc[1])

                if i == 1:
                    break

            e2.wait()
            e3.wait()

    def test_continuous_bars(self):
        now = datetime.datetime.now()

        filter_provider = BarsInPeriodProvider(ticker=['AAPL', 'GOOG'], bgn_prd=datetime.date(now.year - 2, 1, 1), delta=datetime.timedelta(days=10), interval_len=3600, ascend=True, interval_type='s')

        try:
            with IQFeedHistoryListener(fire_batches=True, fire_ticks=True, minibatch=10, filter_provider=filter_provider, lmdb_path='/tmp/test_continuous_bars', exclude_nan_ratio=None) as listener:
                listener.start()

                events_count = {'bars': 0, 'batches': 0, 'minibatches': 0}

                e1 = threading.Event()

                def process_bar(event):
                    try:
                        self.assertTrue(len(event['data']) > 0)
                    finally:
                        events_count['bars'] += 1
                        if events_count['bars'] >= 2:
                            e1.set()

                listener.process_datum += process_bar

                e2 = threading.Event()

                def process_batch_listener(event):
                    try:
                        self.assertEqual(len(event['data'].index.levels[0]), 2)
                    finally:
                        events_count['batches'] += 1
                        if events_count['batches'] >= 2:
                            e2.set()

                listener.process_batch += process_batch_listener

                e3 = threading.Event()

                def process_minibatch_listener(event):
                    try:
                        self.assertTrue(len(event['data'].index.levels[0]) > 0)
                        self.assertEqual(event['data'].loc['AAPL'].shape, (10, 9))
                        self.assertEqual(event['data'].loc['GOOG'].shape, (10, 9))
                    finally:
                        events_count['minibatches'] += 1
                        if events_count['minibatches'] >= 2:
                            e3.set()

                listener.process_minibatch += process_minibatch_listener

                e1.wait()
                e2.wait()
                e3.wait()
        finally:
            shutil.rmtree('/tmp/test_continuous_bars')

    def test_continuous_ticks(self):
        filter_provider = TicksInPeriodProvider(ticker=['AAPL', 'GOOG'], bgn_prd=datetime.datetime.now() - datetime.timedelta(days=10), ascend=True, delta=datetime.timedelta(hours=1))

        try:
            with IQFeedHistoryListener(fire_batches=True, fire_ticks=True, minibatch=10, filter_provider=filter_provider, lmdb_path='/tmp/test_continuous_ticks') as listener:
                listener.start()

                events_count = {'ticks': 0, 'batches': 0, 'minibatches': 0}

                e1 = threading.Event()

                def process_tick(event):
                    try:
                        self.assertTrue(len(event['data']) > 0)
                    finally:
                        events_count['ticks'] += 1
                        if events_count['ticks'] >= 2:
                            e1.set()

                listener.process_datum += process_tick

                e2 = threading.Event()

                def process_batch_listener(event):
                    try:
                        self.assertTrue(len(event['data']) > 0)
                        self.assertEqual(len(event['data'].shape), 3)
                    finally:
                        events_count['batches'] += 1
                        if events_count['batches'] >= 2:
                            e2.set()

                listener.process_batch += process_batch_listener

                e3 = threading.Event()

                def process_minibatch_listener(event):
                    try:
                        self.assertTrue(len(event['data']) > 0)
                        self.assertEqual(event['data'].shape[1:], (10, 14))
                    finally:
                        events_count['minibatches'] += 1
                        if events_count['minibatches'] >= 2:
                            e3.set()

                listener.process_minibatch += process_minibatch_listener

                e1.wait()
                e2.wait()
                e3.wait()
        finally:
            shutil.rmtree('/tmp/test_continuous_ticks')

    def test_bars_performance(self):
        now = datetime.datetime.now()

        filter_provider = BarsInPeriodProvider(
            ticker=['MMM', 'AXP', 'AAPL', 'BA', 'CAT', 'CVX', 'CSCO', 'KO', 'DO', 'XOM', 'GE', 'GS', 'HD', 'IBM', 'INTC', 'JNJ', 'JPM', 'MCD', 'MRK', 'MSFT', 'NKE', 'PFE', 'PG', 'TRV', 'UNH', 'UTX', 'VZ', 'V', 'WMT', 'DIS'],
            bgn_prd=datetime.date(now.year - 1, 1, 1), delta=datetime.timedelta(days=100), interval_len=300, ascend=True, interval_type='s')

        with IQFeedHistoryListener(fire_batches=True, fire_ticks=False, minibatch=128, num_connections=10, filter_provider=filter_provider, run_async=False) as listener:
            def process_batch_listener(event):
                pass

            listener.process_batch += process_batch_listener

            def process_minibatch_listener(event):
                pass

            listener.process_minibatch += process_minibatch_listener

            listener.start()

            self.assertLess(datetime.datetime.now() - now, datetime.timedelta(seconds=90))

    def test_bar_mean_std(self):
        try:
            with IQFeedHistoryListener(run_async=False):
                mean_std_m = get_bar_mean_std(['AAPL', 'IBM'], interval_type='m', years_back=2, lmdb_path='/tmp/test_bar_mean_std')
                self.assertEqual(mean_std_m.shape, (2, 5))

                mean_std_w = get_bar_mean_std(['AAPL', 'IBM'], interval_type='w', years_back=2, lmdb_path='/tmp/test_bar_mean_std')
                self.assertEqual(mean_std_w.shape, (2, 5))

                mean_std_d = get_bar_mean_std(['AAPL', 'IBM'], interval_type='d', years_back=1, lmdb_path='/tmp/test_bar_mean_std')
                self.assertEqual(mean_std_d.shape, (2, 5))

                mean_std_s = get_bar_mean_std(['AAPL', 'IBM'], interval_type='s', interaval_len=300, years_back=1, lmdb_path='/tmp/test_bar_mean_std')
                self.assertEqual(mean_std_s.shape, (2, 5))
        finally:
            shutil.rmtree('/tmp/test_bar_mean_std')


if __name__ == '__main__':
    unittest.main()
