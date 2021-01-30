import ccxt
import time
import datetime
import sys
import logging
import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
file_handler = logging.FileHandler(filename="error.log")
logger.addHandler(file_handler)

# 코인 리스트 불러오기
coin_list = []
file = open('coin_list.txt', 'r')
while (1):
    line = file.readline()
    try:
        escape = line.index('\n')
    except:
        escape = len(line)

    if line:
        coin_list.append(line[0:escape])
    else:
        break
file.close

# 접근키와 개인키 불러오기
key_list = []
file = open('key.txt', 'r', encoding="UTF8")
while (1):
    line = file.readline()
    try:
        escape = line.index('\n')
    except:
        escape = len(line)

    if line:
        key_list.append(line[0:escape].split(':')[1].strip())
    else:
        break
file.close

con_key = key_list[0]
sec_key = key_list[1]
target_volatility = float(key_list[2])  # 수용가능한 변동성은 2%


exchange = ccxt.bithumb({'apiKey':con_key,
                    'secret':sec_key,
                    'enableRateLimit': False, #변동성 돌파는 시장가로 매매, 시장가가 싫으면 True로.
                    })

ready_trading = False


class CryptoTrader(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        now = datetime.datetime.now()  # 2019-12-09 00:02
        mid = datetime.datetime(now.year, now.month, now.day) + datetime.timedelta(1)

        global ready_trading
        while True:
            try:
                if not ready_trading:
                    before_trading_dic = {}
                    for ticker in coin_list:
                        before_trading_dic[ticker] = {}
                        before_trading_dic[ticker]['final_invest_price'] = 0
                        before_trading_dic[ticker]['current_price'] = self.getCurrentPrice(ticker)
                        before_trading_dic[ticker]['target_price'] = 0
                        before_trading_dic[ticker]['check_target_price'] = False
                        before_trading_dic[ticker]['buy_end'] = False
                    time.sleep(0.5)
                    self.update_table(before_trading_dic)
                now = datetime.datetime.now()  # 2019-12-09 00:02
                if mid + datetime.timedelta(seconds=10) < now:
                    if not ready_trading:  # 트레이딩 준비 전인가?
                        coin_list_dic = {}
                        trading_amt = {}
                        for ticker in coin_list:
                            coin_list_dic[ticker] = {}
                            coin_list_dic[ticker]['final_invest_price'] = 0
                            coin_list_dic[ticker]['current_price'] = 0
                            coin_list_dic[ticker]['target_price'] = 0
                            coin_list_dic[ticker]['check_target_price'] = False
                            coin_list_dic[ticker]['buy_end'] = False

                        mid = datetime.datetime(now.year, now.month, now.day) + datetime.timedelta(1)


                        balance = self.getBalance()
                        print("잔고 : " + str(balance))
                        print("=================================================")
                        devided_invest_price = float(balance) / len(coin_list)
                        # 코인별 얼마를 투자할 것이냐.
                        for ticker in coin_list:  # 매수 트래이딩 전
                            trading_amt[ticker] = devided_invest_price * self.get_market_timing(ticker)
                            if trading_amt[ticker] > 0:
                                coin_list_dic[ticker]['target_price'] = self.get_target_price(ticker)
                                try:
                                    invest_price = target_volatility / self.get_volatility(ticker) * trading_amt[ticker]
                                    if invest_price < 5000 : #최소 구매금액은 5천원으로 한다. (비트코인이 4천만원이 넘기 때문에)
                                        invest_price = 5000
                                    coin_list_dic[ticker]['final_invest_price'] = invest_price
                                except Exception as e:
                                    self.writeError(e)
                                    coin_list_dic[ticker]['final_invest_price'] = 0
                                    pass
                                print(str(ticker) + " 투자금액 : " + str(coin_list_dic[ticker]['final_invest_price']))
                                print(str(ticker) + " 타겟 금액 : " + str(coin_list_dic[ticker]['target_price']))
                                print("=================================================")
                                time.sleep(0.5)
                            else:
                                coin_list_dic[ticker]['final_invest_price'] = 0
                                coin_list_dic[ticker]['target_price'] = '트레이딩 부적합'
                        ready_trading = True
                        self.update_table(coin_list_dic)

                    # 트레이딩 준비 끝!
                if ready_trading:
                    for ticker in coin_list:
                        coin_list_dic[ticker]['current_price'] = self.getCurrentPrice(ticker)
                        if coin_list_dic[ticker]['final_invest_price'] > 0.0:
                            coin_list_dic[ticker]['current_price'] = self.getCurrentPrice(ticker)
                            if coin_list_dic[ticker]['target_price'] < coin_list_dic[ticker]['current_price'] and not coin_list_dic[ticker]['check_target_price']:
                                try:
                                    print(ticker + " 타겟가격 돌파!! / 현재가 : " + str(
                                        coin_list_dic[ticker]['current_price']) + " 타겟가 : " + str(
                                        coin_list_dic[ticker]['target_price']))
                                    # 해당 ticker에 돌파했다라고 체크
                                    coin_list_dic[ticker]['check_target_price'] = True
                                    if not coin_list_dic[ticker]['buy_end']:  # 해당 티커를 아직 구매 안했으면..
                                        buy_order = self.buy_crypto_currency(ticker, coin_list_dic[ticker]['final_invest_price'])
                                        print(ticker + "매수 거래번호 : " + str(buy_order))
                                        ticker_amt = self.getTickerAmt(ticker)
                                        if ticker_amt > 0:
                                            coin_list_dic[ticker]['buy_end'] = True
                                except Exception as e:
                                    logger.error(e)
                                    pass
                    self.update_table(coin_list_dic)
                if mid <= now < mid + datetime.timedelta(seconds=5):
                    for ticker in coin_list:
                        unit = self.getTickerAmt(ticker)
                        if unit > 0:
                            sell_order = self.sell_crypto_currency(ticker, unit)
                            print(ticker + "매도 거래번호 : " + str(sell_order))
                    ready_trading = False
                time.sleep(0.5)
            except Exception as e:
                logger.error(e)
                pass

    def getCurrentPrice(self, ticker):
        currPrice = 0
        while currPrice == 0:
            currPrice = exchange.fetch_ticker(ticker)['close']
            time.sleep(0.5)
        return currPrice

    def getBalance(self):
        bal = exchange.fetch_balance()
        return bal['info']['data']['available_krw']

    def getTickerAmt(self, ticker):
        tickerAmt = exchange.fetch_balance()
        charPosition = ticker.find('/') # ETH/KRW라고 되었을때 '/'의 위치를 찾는다. 이때 charPosition은 3이된다.
        return tickerAmt[ticker[0:charPosition]]['free'] #ETH라는 글자만 빼오기 위해 ticker[0:5]를 사용한다.

    def getCandleStick(self, ticker):
        ohlcv = exchange.fetch_ohlcv(ticker,'1d')

        while ohlcv is None:
            time.sleep(0.5)
            ohlcv = exchange.fetch_ohlcv(ticker, '1d')

        dataframe = pd.DataFrame(ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume'])

        return dataframe

    def get_market_timing(self, ticker):
        try:
            ma_score = 0
            df = self.getCandleStick(ticker)

            ma3 = df.close.rolling(3).mean()
            ma5 = df.close.rolling(5).mean()
            ma10 = df.close.rolling(10).mean()
            ma20 = df.close.rolling(20).mean()

            yesterday = df.iloc[-2]
            close_price = yesterday['close']

            if close_price > ma3.iloc[-2]:
                ma_score += 1
            if close_price > ma5.iloc[-2]:
                ma_score += 1
            if close_price > ma10.iloc[-2]:
                ma_score += 1
            if close_price > ma20.iloc[-2]:
                ma_score += 1

            result_score = round(ma_score / 4, 2)
            return result_score
        except Exception as e:
            logger.error(e)
            return 0.0

    def get_target_price(self, ticker):
        def get_noise(_ticker, _df):
            noise = 0

            for num in range(2, 22):
                noise += 1 - abs(_df.iloc[num * -1]['open'] - _df.iloc[num * -1]['close']) / (
                        _df.iloc[num * -1]['high'] - _df.iloc[num * -1]['low'])
            return round(noise / 20, 1)

        df = self.getCandleStick(ticker)

        yesterday = df.iloc[-2]
        today_open = yesterday['close']  # 오늘은 어제의 종가 = 오늘의 시가
        yesterday_high = yesterday['high']  # 어제의 고가
        yesterday_low = yesterday['low']  # 어제의 저가
        _range = yesterday_high - yesterday_low

        k = get_noise(ticker, df)
        target = today_open + _range * k
        return target

    def get_volatility(self, ticker):
        df = self.getCandleStick(ticker)
        yesterday = df.iloc[-2]
        today_open = yesterday['close']  # 오늘은 어제의 종가 = 오늘의 시가
        yesterday_high = yesterday['high']  # 어제의 고가
        yesterday_low = yesterday['low']  # 어제의 저가
        volatility = ((yesterday_high - yesterday_low) / today_open) * 100
        return round(volatility)

    def buy_crypto_currency(self, ticker, invest_price):
        try:
            krw = invest_price
            orderbook = exchange.fetch_order_book(ticker)
            sell_price = orderbook['asks'][0][0]
            unit = round(krw / sell_price,4)
            buy_order = exchange.create_market_buy_order(ticker, unit)  # 시장가 매수
            return buy_order
        except Exception as e:
            logger.error(e)
            pass

    def sell_crypto_currency(self, ticker, unit):
        try:
            sell_order = exchange.create_market_sell_order(ticker, unit)
            return sell_order
        except Exception as e:
            logger.error(e)

    def update_table(self, dict):
        self.finished.emit(dict)
        self.msleep(500)

class My_window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget(self)
        self.setWindowTitle('가상화폐 트레이딩 봇')

        self.setFixedWidth(510)
        self.table.resize(500, 80 * len(coin_list))
        self.table.setColumnCount(5)
        self.table.setRowCount(len(coin_list) + 1)
        self.table.setHorizontalHeaderLabels(['가상화폐', '현재가', '타켓가', '투자금액', '매수 여부'])
        self.table.setSpan(len(coin_list), 1, 1, 4)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.table.resizeRowsToContents()

        self.crypto_trader = CryptoTrader()
        self.crypto_trader.finished.connect(self.update_value)
        self.crypto_trader.start()

    @pyqtSlot(dict)
    def update_value(self, data):
        try:
            for num, ticker_info in enumerate(data.items()):
                self.table.setItem(int(num), 0, QTableWidgetItem(ticker_info[0]))
                self.table.setItem(int(num), 1, QTableWidgetItem(str(ticker_info[1]['current_price'])))
                self.table.setItem(int(num), 2, QTableWidgetItem(str(ticker_info[1]['target_price'])))
                self.table.setItem(int(num), 3, QTableWidgetItem(str(ticker_info[1]['final_invest_price'])))
                if ticker_info[1]['buy_end'] == True:
                    self.table.setItem(int(num), 4, QTableWidgetItem('매수완료'))
                else:
                    self.table.setItem(int(num), 4, QTableWidgetItem('매수전'))
            self.table.setItem(len(coin_list), 0, QTableWidgetItem('잔고'))
            self.table.setItem(len(coin_list), 1, QTableWidgetItem(str(exchange.fetch_balance()['info']['data']['available_krw'])))
        except Exception as e:
            logger.error(e)
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = My_window()
    window.show()
    app.exec_()