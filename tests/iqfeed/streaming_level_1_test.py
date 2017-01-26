import unittest
from atpy.data.iqfeed.iqfeed_level_1_provider import *


class TestIQFeedLevel1(unittest.TestCase):
    """
    IQFeed streaming news test, which checks whether the class works in basic terms
    """

    def test_news_column_mode(self):
        with IQFeedLevel1Listener(minibatch=2) as listener:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.news_on()

            def process_news_item(*args, **kwargs):
                news_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(news_item), 6)
                self.assertGreater(len(news_item['headline']), 0)

            listener.process_news += process_news_item

            def process_news_mb(*args, **kwargs):
                news_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(news_item), 6)
                self.assertEqual(len(news_item['headline']), 2)
                self.assertGreater(len(news_item['headline'][0]), 0)
                self.assertNotEqual(news_item['story_id'][0], news_item['story_id'][1])

            listener.process_news_mb += process_news_mb

            for i, news_item in enumerate(listener.news_provider()):
                self.assertEqual(len(news_item), 6)
                self.assertEqual(len(news_item['headline']), 2)
                self.assertGreater(len(news_item['headline'][0]), 0)
                self.assertNotEqual(news_item['story_id'][0], news_item['story_id'][1])

                if i == 1:
                    break

    def test_fundamentals_column_mode(self):
        with IQFeedLevel1Listener(minibatch=2, column_mode=True) as listener:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')

            def process_fund_item(*args, **kwargs):
                fund_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(fund_item), 50)

            listener.process_fundamentals += process_fund_item

            def process_fund_mb(*args, **kwargs):
                fund_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(fund_item), 50)
                self.assertEqual(len(fund_item['Symbol']), 2)
                self.assertTrue('AAPL'.encode() in fund_item['Symbol'] or 'IBM'.encode() in fund_item['Symbol'] or 'GOOG'.encode() in fund_item['Symbol'] or 'MSFT'.encode() in fund_item['Symbol'])

            listener.process_fundamentals_mb += process_fund_mb

            for i, fund_item in enumerate(listener.fundamentals_provider()):
                self.assertEqual(len(fund_item), 50)
                self.assertEqual(len(fund_item['Symbol']), 2)
                self.assertTrue('AAPL'.encode() in fund_item['Symbol'] or 'IBM'.encode() in fund_item['Symbol'] or 'GOOG'.encode() in fund_item['Symbol'] or 'MSFT'.encode() in fund_item['Symbol'])

                if i == 1:
                    break

    def test_fundamentals_row_mode(self):
        with IQFeedLevel1Listener(minibatch=2, column_mode=False) as listener:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')

            def process_fund_item(*args, **kwargs):
                fund_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(fund_item), 50)

            listener.process_fundamentals += process_fund_item

            def process_fund_mb(*args, **kwargs):
                fund_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(fund_item), 2)
                self.assertEqual(len(fund_item[0]), 50)

                symbols = [fund_item[0]['Symbol'], fund_item[1]['Symbol']]
                self.assertTrue('AAPL'.encode() in symbols or 'IBM'.encode() in symbols or 'GOOG'.encode() in symbols or 'MSFT'.encode() in symbols)

            listener.process_fundamentals_mb += process_fund_mb

            for i, fund_item in enumerate(listener.fundamentals_provider()):
                self.assertEqual(len(fund_item), 2)
                self.assertEqual(len(fund_item[0]), 50)
                symbols = [fund_item[0]['Symbol'], fund_item[1]['Symbol']]
                self.assertTrue('AAPL'.encode() in symbols or 'IBM'.encode() in symbols or 'GOOG'.encode() in symbols or 'MSFT'.encode() in symbols)

                if i == 1:
                    break

    def test_summary_column_mode(self):
        with IQFeedLevel1Listener(minibatch=2, column_mode=True) as listener:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')

            def process_summary_item(*args, **kwargs):
                summary_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(summary_item), 16)

            listener.process_summary += process_summary_item

            def process_summary_mb(*args, **kwargs):
                summary_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(summary_item), 16)
                self.assertEqual(len(summary_item['Symbol']), 2)
                self.assertTrue('AAPL'.encode() in summary_item['Symbol'] or 'IBM'.encode() in summary_item['Symbol'] or 'GOOG'.encode() in summary_item['Symbol'] or 'MSFT'.encode() in summary_item['Symbol'])

            listener.process_summary_mb += process_summary_mb

            for i, summary_item in enumerate(listener.summary_provider()):
                self.assertEqual(len(summary_item), 16)
                self.assertEqual(len(summary_item['Symbol']), 2)
                self.assertTrue('AAPL'.encode() in summary_item['Symbol'] or 'IBM'.encode() in summary_item['Symbol'] or 'GOOG'.encode() in summary_item['Symbol'] or 'MSFT'.encode() in summary_item['Symbol'])

                if i == 1:
                    break

    def test_summary_row_mode(self):
        with IQFeedLevel1Listener(minibatch=2, column_mode=False) as listener:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')

            def process_summary_item(*args, **kwargs):
                summary_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(summary_item), 16)

            listener.process_summary += process_summary_item

            def process_summary_mb(*args, **kwargs):
                summary_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(summary_item), 2)
                self.assertEqual(len(summary_item[0]), 16)

                symbols = [summary_item[0]['Symbol'], summary_item[1]['Symbol']]
                self.assertTrue('AAPL'.encode() in symbols or 'IBM'.encode() in symbols or 'GOOG'.encode() in symbols or 'MSFT'.encode() in symbols)

            listener.process_summary_mb += process_summary_mb

            for i, summary_item in enumerate(listener.summary_provider()):
                self.assertEqual(len(summary_item), 2)
                self.assertEqual(len(summary_item[0]), 16)
                symbols = [summary_item[0]['Symbol'], summary_item[1]['Symbol']]
                self.assertTrue('AAPL'.encode() in symbols or 'IBM'.encode() in symbols or 'GOOG'.encode() in symbols or 'MSFT'.encode() in symbols)

                if i == 1:
                    break

    def test_update_column_mode(self):
        with IQFeedLevel1Listener(minibatch=2, column_mode=True) as listener:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')

            def process_update_item(*args, **kwargs):
                update_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(update_item), 16)

            listener.process_update += process_update_item

            def process_update_mb(*args, **kwargs):
                update_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(update_item), 16)
                self.assertEqual(len(update_item['Symbol']), 2)
                self.assertTrue('AAPL'.encode() in update_item['Symbol'] or 'IBM'.encode() in update_item['Symbol'] or 'GOOG'.encode() in update_item['Symbol'] or 'MSFT'.encode() in update_item['Symbol'])

            listener.process_update_mb += process_update_mb

            for i, update_item in enumerate(listener.update_provider()):
                self.assertEqual(len(update_item), 16)
                self.assertEqual(len(update_item['Symbol']), 2)
                self.assertTrue('AAPL'.encode() in update_item['Symbol'] or 'IBM'.encode() in update_item['Symbol'] or 'GOOG'.encode() in update_item['Symbol'] or 'MSFT'.encode() in update_item['Symbol'])

                if i == 1:
                    break

    def test_update_row_mode(self):
        with IQFeedLevel1Listener(minibatch=2, column_mode=False) as listener:
            listener.watch('IBM')
            listener.watch('AAPL')
            listener.watch('GOOG')
            listener.watch('MSFT')

            def process_update_item(*args, **kwargs):
                update_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(update_item), 16)

            listener.process_update += process_update_item

            def process_update_mb(*args, **kwargs):
                update_item = kwargs[FUNCTION_OUTPUT].data
                self.assertEqual(len(update_item), 2)
                self.assertEqual(len(update_item[0]), 16)

                symbols = [update_item[0]['Symbol'], update_item[1]['Symbol']]
                self.assertTrue('AAPL'.encode() in symbols or 'IBM'.encode() in symbols or 'GOOG'.encode() in symbols or 'MSFT'.encode() in symbols)

            listener.process_update_mb += process_update_mb

            for i, update_item in enumerate(listener.update_provider()):
                self.assertEqual(len(update_item), 2)
                self.assertEqual(len(update_item[0]), 16)
                symbols = [update_item[0]['Symbol'], update_item[1]['Symbol']]
                self.assertTrue('AAPL'.encode() in symbols or 'IBM'.encode() in symbols or 'GOOG'.encode() in symbols or 'MSFT'.encode() in symbols)

                if i == 1:
                    break

if __name__ == '__main__':
    unittest.main()
