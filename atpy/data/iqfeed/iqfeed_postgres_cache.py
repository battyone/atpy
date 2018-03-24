import datetime
import functools
import json
import typing

import pandas as pd
import sqlalchemy
from dateutil import tz

from atpy.data.iqfeed.iqfeed_history_provider import IQFeedHistoryProvider, BarsInPeriodFilter, BarsDailyForDatesFilter


def noncache_provider(history: IQFeedHistoryProvider):
    def _request_noncache_data(filters: dict, q, h: IQFeedHistoryProvider):
        """
        :return: request data from data provider (has to be UTC localized)
        """
        new_filters = list()
        filters_copy = filters.copy()

        for f in filters_copy:
            if f.interval_type == 's':
                new_f = BarsInPeriodFilter(ticker=f.ticker, bgn_prd=f.bgn_prd.astimezone(tz.gettz('US/Eastern')) if f.bgn_prd is not None else None, end_prd=None, interval_len=f.interval_len, interval_type=f.interval_type)
            elif f.interval_type == 'd':
                new_f = BarsDailyForDatesFilter(ticker=f.ticker, bgn_dt=f.bgn_prd.date() if f.bgn_prd is not None else None, end_dt=None)

            filters[new_f] = f

            new_filters.append(new_f)

        h.request_data_by_filters(new_filters, q)

    return functools.partial(_request_noncache_data, h=history)


def update_fundamentals(sqlalchemy_conn, fundamentals: dict, table_name: str = 'iqfeed_fundamentals'):
    cur = sqlalchemy_conn.execute("SELECT to_regclass('public.{0}')".format(table_name))

    exists = [t for t in cur][0][0] is not None

    if exists:
        sqlalchemy_conn.execute("DROP TABLE IF EXISTS {0};".format(table_name))

    for f in fundamentals:
        fundamentals[f] = json.dumps(fundamentals[f], default=lambda x: x.isoformat() if isinstance(x, datetime.datetime) else str(x))

    df = pd.DataFrame(list(fundamentals.items()), columns=['symbol', 'fundamentals']).set_index('symbol', drop=True)

    df.to_sql(table_name, sqlalchemy_conn, index_label='symbol', dtype={'fundamentals': sqlalchemy.types.JSON})


def request_fundamentals(sqlalchemy_conn, symbol: typing.Union[list, str], table_name: str = 'iqfeed_fundamentals'):
    query = "select * from {0}".format(table_name)
    params = list()

    if isinstance(symbol, list):
        query += " WHERE symbol IN (%s)" % ','.join(['%s'] * len(symbol))
        params += symbol
    elif isinstance(symbol, str):
        query += " WHERE symbol = %s"
        params.append(symbol)

    return pd.read_sql(query, con=sqlalchemy_conn, index_col=['symbol'], params=params)