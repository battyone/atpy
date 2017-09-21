import pyevents.events as events
from atpy.data.iqfeed.util import *
from atpy.data.iqfeed.iqfeed_level_1_provider import Fundamentals
import pandas as pd
import threading


class IQFeedBarDataListener(iq.SilentBarListener, metaclass=events.GlobalRegister):

    def __init__(self, interval_len, interval_type='s', fire_bars=True, mkt_snapshot_depth=0, key_suffix=''):
        """
        :param fire_bars: raise event for each individual bar if True
        :param mkt_snapshot_depth: construct and maintain dataframe representing the current market snapshot with depth. If 0, then don't construct, otherwise construct for the past periods
        :param key_suffix: suffix to the fieldnames
        """
        super().__init__(name="Bar data listener")

        self.fire_bars = fire_bars
        self.key_suffix = key_suffix
        self.conn = None
        self.streaming_conn = None
        self.current_batch = None
        self.interval_len = interval_len
        self.interval_type = interval_type
        self.watched_symbols = set()
        self._lock = threading.RLock()

        self.mkt_snapshot_depth = mkt_snapshot_depth

        if mkt_snapshot_depth > 0:
            self._mkt_snapshot = None

        pd.set_option('mode.chained_assignment', 'warn')

    def __enter__(self):
        launch_service()

        self.conn = iq.BarConn()
        self.conn.add_listener(self)
        self.conn.connect()

        # streaming conn for fundamental data
        self.streaming_conn = iq.QuoteConn()
        self.streaming_conn.connect()

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Disconnect connection etc"""
        self.conn.remove_listener(self)
        self.conn.disconnect()

        self.streaming_conn.disconnect()
        self.streaming_conn = None

        self.conn = None

    def __del__(self):
        if self.conn is not None:
            self.conn.remove_listener(self)
            self.conn.disconnect()

        if self.streaming_conn is not None:
            self.streaming_conn.disconnect()

    def __getattr__(self, name):
        if self.conn is not None:
            return getattr(self.conn, name)
        else:
            raise AttributeError

    def process_invalid_symbol(self, bad_symbol: str) -> None:
        if bad_symbol in self.watched_symbols and bad_symbol in self.watched_symbols:
            self.watched_symbols.remove(bad_symbol)

    def process_latest_bar_update(self, bar_data: np.array) -> None:
        data = None

        if self.fire_bars:
            data = self._process_data(iqfeed_to_dict(bar_data, key_suffix=self.key_suffix))
            self.on_latest_bar_update(self._process_data(iqfeed_to_dict(np.copy(bar_data), key_suffix=self.key_suffix)))

        if self.mkt_snapshot_depth > 0:
            data = data if data is not None else self._process_data(iqfeed_to_dict(bar_data, key_suffix=self.key_suffix))
            self._update_mkt_snapshot(data)

    def process_live_bar(self, bar_data: np.array) -> None:
        data = None

        if self.fire_bars:
            data = self._process_data(iqfeed_to_dict(bar_data, key_suffix=self.key_suffix))
            self.on_bar(data)
        if self.mkt_snapshot_depth > 0:
            data = data if data is not None else self._process_data(iqfeed_to_dict(bar_data, key_suffix=self.key_suffix))
            self._update_mkt_snapshot(data)

    def process_history_bar(self, bar_data: np.array) -> None:
        bar_data = np.copy(bar_data)
        bd = bar_data[0] if len(bar_data) == 1 else bar_data
        adjust(bd, Fundamentals.get(bd['symbol'].decode('ascii'), self.streaming_conn))

        data = None
        if self.fire_bars:
            data = self._process_data(iqfeed_to_dict(bar_data, key_suffix=self.key_suffix))
            self.on_bar(data)
        if self.mkt_snapshot_depth > 0 is not None:
            data = data if data is not None else self._process_data(iqfeed_to_dict(bar_data, key_suffix=self.key_suffix))
            self._update_mkt_snapshot(data)

    @events.listener
    def on_event(self, event):
        if event['type'] == 'watch_bars':
            self.watch_bars(event['data']['symbol'] if isinstance(event['data'], dict) else event['data'])
        elif event['type'] == 'request_market_snapshot_bars':
            snapshot = self.request_market_snapshot_bars('normalize' in event and event['normalize'] is True)
            self.on_market_snapshot(snapshot)

    def watch_bars(self, symbol):
        if isinstance(symbol, str) and symbol not in self.watched_symbols:
            data_copy = {'symbol': symbol, 'interval_type': self.interval_type, 'interval_len': self.interval_len}
            if self.mkt_snapshot_depth > 0:
                data_copy['lookback_bars'] = self.mkt_snapshot_depth

            self.conn.watch(**data_copy)
            self.watched_symbols.add(symbol)
        elif isinstance(symbol, list):
            data_copy = dict(symbol=symbol)
            data_copy['interval_type'] = self.interval_type
            data_copy['interval_len'] = self.interval_len

            if self.mkt_snapshot_depth > 0:
                data_copy['lookback_bars'] = self.mkt_snapshot_depth

            for s in [s for s in data_copy['symbol'] if s not in self.watched_symbols]:
                data_copy['symbol'] = s
                self.conn.watch(**data_copy)
                self.watched_symbols.add(s)

        with self._lock:
            if self._mkt_snapshot is not None:
                symbol = list(self.watched_symbols)
                symbol.sort()

                multi_index = pd.MultiIndex.from_product([symbol, self._mkt_snapshot.index.levels[1].unique()], names=['symbol', 'time_stamp']).sort_values()
                self._mkt_snapshot = self._reindex_and_fill(self._mkt_snapshot, multi_index)

    def request_market_snapshot_bars(self, normalize=False):
        with self._lock:
            snapshot = self._mkt_snapshot.dropna()
            snapshot.set_index(['symbol', 'time_stamp'], inplace=True)
            snapshot.reset_index(inplace=True)
            snapshot.set_index(['symbol', 'time_stamp'], drop=False, inplace=True)

            if normalize:
                multi_index = pd.MultiIndex.from_product([snapshot.index.levels[0].unique(), snapshot.index.levels[1].unique()], names=['symbol', 'time_stamp']).sort_values()
                snapshot = IQFeedBarDataListener._reindex_and_fill(snapshot, multi_index)

            return snapshot.groupby(level=0).tail(self.mkt_snapshot_depth)

    def _update_mkt_snapshot(self, data):
        if self.mkt_snapshot_depth is not None:
            with self._lock:
                if self._mkt_snapshot is None:
                    self._mkt_snapshot = pd.Series(data).to_frame().T
                    self._mkt_snapshot.set_index(['symbol', 'time_stamp'], append=False, inplace=True, drop=False)

                    symbols = list(self.watched_symbols)
                    symbols.sort()

                    multi_index = pd.MultiIndex.from_product([symbols, self._mkt_snapshot.index.levels[1].unique()], names=['symbol', 'time_stamp']).sort_values()
                    self._mkt_snapshot = self._reindex_and_fill(self._mkt_snapshot, multi_index)
                elif isinstance(data, dict) and (data['symbol'], data['time_stamp']) in self._mkt_snapshot.index:
                    self._mkt_snapshot.loc[data['symbol'], data['time_stamp']] = pd.Series(data)
                else:
                    expand = data['time_stamp'] > self._mkt_snapshot.index.levels[1][len(self._mkt_snapshot.index.levels[1]) - 1]

                    to_concat = pd.Series(data).to_frame().T
                    to_concat.set_index(['symbol', 'time_stamp'], append=False, inplace=True, drop=False)

                    self._mkt_snapshot.update(to_concat)
                    to_concat = to_concat[~to_concat.index.isin(self._mkt_snapshot.index)]

                    self._mkt_snapshot = self._merge_snapshots(self._mkt_snapshot, to_concat)

                    if expand:
                        self._mkt_snapshot = self._expand(self._mkt_snapshot, min(1000, self.mkt_snapshot_depth * 10), self.mkt_snapshot_depth)

    @staticmethod
    def _merge_snapshots(s1, s2):
        if s1.empty and not s2.empty:
            return s2
        elif s2.empty and not s1.empty:
            return s1
        elif s1.empty and s2.empty:
            return

        return pd.concat([s1, s2]).sort_index()

    @staticmethod
    def _reindex_and_fill(df, index):
        df = df.reindex(index)
        df.drop(['symbol', 'time_stamp'], axis=1, inplace=True)
        df.reset_index(inplace=True)
        df.set_index(index, inplace=True)

        for c in [c for c in ['period_volume', 'number_of_trades'] if c in df.columns]:
            df[c].fillna(0, inplace=True)

        if 'open' in df.columns:
            df['open'] = df.groupby(level=0)['open'].fillna(method='ffill')
            op = df['open']

            for c in [c for c in ['close', 'high', 'low'] if c in df.columns]:
                df[c].fillna(op, inplace=True)

        df = df.groupby(level=0).fillna(method='ffill')

        df = df.groupby(level=0).fillna(method='backfill')

        return df

    @staticmethod
    def _expand(df, steps, max_length=None):
        if len(df.index.levels[1]) < 2:
            return df

        diff = df.index.levels[1][1] - df.index.levels[1][0]
        new_index = df.index.levels[1].append(pd.date_range(df.index.levels[1][len(df.index.levels[1]) - 1] + diff, periods=steps, freq=diff))

        multi_index = pd.MultiIndex.from_product([df.index.levels[0], new_index], names=['symbol', 'time_stamp']).sort_values()

        result = df.reindex(multi_index)

        if max_length is not None:
            result = df.groupby(level=0).tail(max_length)

        return result

    def _process_data(self, data):
        if isinstance(data, dict):
            result = dict()

            sf = self.key_suffix

            result['symbol' + sf] = data.pop('symbol')
            result['time_stamp' + sf] = data.pop('date') + data.pop('time')
            result['high' + sf] = data.pop('high_p')
            result['low' + sf] = data.pop('low_p')
            result['open' + sf] = data.pop('open_p')
            result['close' + sf] = data.pop('close_p')
            result['total_volume' + sf] = data.pop('tot_vlm')
            result['period_volume' + sf] = data.pop('prd_vlm')
            result['number_of_trades' + sf] = data.pop('num_trds')
        else:
            result = pd.DataFrame(data)
            result['symbol'] = result['symbol'].str.decode('ascii')
            sf = self.key_suffix
            result['time_stamp' + sf] = data['date'] + data['time']

            result.set_index('time_stamp' + sf, inplace=True, drop=False)

            result.drop(['date', 'time'], axis=1, inplace=True)
            result.rename_axis({"symbol": "symbol" + sf, "high_p": "high" + sf, "low_p": "low" + sf, "open_p": "open" + sf, "close_p": "close" + sf, "tot_vlm": "total_volume" + sf, "prd_vlm": "period_volume" + sf, "num_trds": "number_of_trades" + sf}, axis="columns", copy=False, inplace=True)

        return result

    @events.after
    def on_latest_bar_update(self, bar_data):
        return {'type': 'latest_bar_update', 'data': bar_data, 'interval_type': self.interval_type, 'interval_len': self.interval_len}

    @events.after
    def on_bar(self, bar_data):
        return {'type': 'bar', 'data': bar_data, 'interval_type': self.interval_type, 'interval_len': self.interval_len}

    def bar_provider(self):
        return IQFeedDataProvider(self.on_bar)

    @events.after
    def on_market_snapshot(self, snapshot):
        return {'type': 'bar_market_snapshot', 'data': snapshot, 'interval_type': self.interval_type, 'interval_len': self.interval_len}
