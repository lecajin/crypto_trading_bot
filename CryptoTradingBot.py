import pybithumb
import time
import datetime
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

#코인 리스트 불러오기
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

bithumb = pybithumb.Bithumb(con_key, sec_key)

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
                        before_trading_dic[ticker]['current_price'] = pybithumb.get_current_price(ticker)
                        before_trading_dic[ticker]['target_price'] = 0
                        before_trading_dic[ticker]['check_target_price'] = False
                        before_trading_dic[ticker]['buy_end'] = False
                    time.sleep(0.5)
                    self.update_table(before_trading_dic)
                now = datetime.datetime.now() # 2019-12-09 00:02
                if mid + datetime.timedelta(seconds=10) < now:
                    if not ready_trading: #트레이딩 준비 전인가?
                        coin_list_dic = {}
                        trading_amt = {}
                        for ticker in coin_list:
                            coin_list_dic[ticker] = {}

                            coin_list_dic[ticker]['current_price'] = 0
                            coin_list_dic[ticker]['target_price'] = 0
                            coin_list_dic[ticker]['check_target_price'] = False
                            coin_list_dic[ticker]['buy_end'] = False

                        mid = datetime.datetime(now.year, now.month, now.day) + datetime.timedelta(1)

                        balance = bithumb.get_balance("BTC")  # 잔고
                        print("잔고 : " + str(balance[2]))
                        print("=================================================")
                        devided_invest_price = float(format(balance[2], 'f')) / len(coin_list)
                        # 코인별 얼마를 투자할 것이냐.
                        for ticker in coin_list: #매수 트래이딩 전
                            trading_amt[ticker] = devided_invest_price * self.get_market_timing(ticker)
                            if trading_amt[ticker] > 0:
                                coin_list_dic[ticker]['target_price'] = self.get_target_price(ticker)
                                try:
                                    coin_list_dic[ticker]['final_invest_price'] = target_volatility / self.get_volatility(ticker) * trading_amt[ticker]
                                except Exception as e:
                                    print(e)
                                    coin_list_dic[ticker]['final_invest_price'] = 0
                                    pass
                                print(str(ticker) + " 투자금액 : " + str(coin_list_dic[ticker]['final_invest_price']))
                                print(str(ticker) + " 타겟 금액 : " + str(coin_list_dic[ticker]['target_price']))
                                print("=================================================")
                                time.sleep(0.5)
                            else:
                                coin_list_dic[ticker]['final_invest_price'] = 0
                        ready_trading = True
                        self.update_table(coin_list_dic)

                    # 트레이딩 준비 끝!
                if ready_trading:
                    curr_price = ''
                    for ticker in coin_list:
                        if coin_list_dic[ticker]['final_invest_price'] > 0.0:
                            coin_list_dic[ticker]['current_price'] = pybithumb.get_current_price(ticker)
                            curr_price += ticker + " 현재가 : " + str(coin_list_dic[ticker]['current_price']) + ' '
                            if coin_list_dic[ticker]['target_price'] < coin_list_dic[ticker]['current_price'] and not coin_list_dic[ticker]['check_target_price']:
                                try:
                                    print(ticker + " 타겟가격 돌파!! / 현재가 : " + str(coin_list_dic[ticker]['current_price']) + " 타겟가 : "+ str(coin_list_dic[ticker]['target_price']))
                                    # 해당 ticker에 돌파했다라고 체크
                                    coin_list_dic[ticker]['check_target_price'] = True
                                    if not coin_list_dic[ticker]['buy_end']: #해당 티커를 아직 구매 안했으면..
                                        buy_order = self.buy_crypto_currency(ticker, coin_list_dic[ticker]['final_invest_price'])
                                        print(ticker + "매수 거래번호 : "+ str(buy_order))
                                        ticker_amt = bithumb.get_balance(ticker)[0]
                                        if ticker_amt > 0:
                                            coin_list_dic[ticker]['buy_end'] = True
                                except Exception as e:
                                    print(e)
                                    pass
                    self.update_table(coin_list_dic)
                if mid <= now < mid + datetime.timedelta(seconds=5):
                    for ticker in coin_list:
                        unit = bithumb.get_balance(ticker)[0]
                        if unit > 0:
                            sell_order = self.sell_crypto_currency(ticker, unit)
                            print(ticker + "매도 거래번호 : " + str(sell_order))
                    ready_trading = False
                time.sleep(0.5)
            except Exception as e:
                print(e)
                pass

    def get_market_timing(self, ticker):
        try:
            ma_score = 0
            df = pybithumb.get_candlestick(ticker)
            ma3 = df.close.rolling(3).mean()
            ma5 = df.close.rolling(5).mean()
            ma10 = df.close.rolling(10).mean()
            ma20 = df.close.rolling(20).mean()

            yesterday = df.iloc[-2]
            close_price = yesterday['close']

            if close_price > ma3[-2]:
                ma_score += 1
            if close_price > ma5[-2]:
                ma_score += 1
            if close_price > ma10[-2]:
                ma_score += 1
            if close_price > ma20[-2]:
                ma_score += 1

            result_score = round(ma_score / 4, 2)
            return result_score
        except Exception as e:
            print(e)
            return 0.0

    def get_target_price(self, ticker):
        def get_noise(_ticker):
            noise = 0
            df = pybithumb.get_candlestick(_ticker)
            for num in range(2, 22):
                noise += 1 - abs(df.iloc[num * -1]['open'] - df.iloc[num * -1]['close']) / (
                        df.iloc[num * -1]['high'] - df.iloc[num * -1]['low'])
            return round(noise / 20, 1)

        df = pybithumb.get_candlestick(ticker)
        yesterday = df.iloc[-2]
        today_open = yesterday['close']  # 오늘은 어제의 종가 = 오늘의 시가
        yesterday_high = yesterday['high']  # 어제의 고가
        yesterday_low = yesterday['low'] # 어제의 저가
        _range = yesterday_high - yesterday_low
        k = get_noise(ticker)
        target = today_open + _range * k
        return target

    def get_volatility(self, ticker):
        df = pybithumb.get_candlestick(ticker)
        yesterday = df.iloc[-2]

        today_open = yesterday['close']  # 오늘은 어제의 종가 = 오늘의 시가
        yesterday_high = yesterday['high']  # 어제의 고가
        yesterday_low = yesterday['low']  # 어제의 저가
        volatility = ((yesterday_high - yesterday_low) / today_open) * 100
        return round(volatility)

    def buy_crypto_currency(self, ticker, invest_price):
        krw = invest_price
        orderbook = bithumb.get_orderbook(ticker)
        sell_price = orderbook['asks'][0]['price']
        unit = krw / float(sell_price)
        buy_order = bithumb.buy_market_order(ticker, unit)  # 매수
        return buy_order

    def sell_crypto_currency(self, ticker, unit):
        sell_order = bithumb.sell_market_order(ticker, unit)
        return sell_order

    def update_table(self, dict):
        self.finished.emit(dict)
        self.msleep(500)

class My_window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget(self)
        self.setWindowTitle('가상화폐 트레이딩 봇')
        self.setFixedWidth(430)
        self.table.resize(500, 60 * len(coin_list))
        self.table.setColumnCount(4)
        self.table.setRowCount(len(coin_list))
        self.table.setHorizontalHeaderLabels(['가상화폐', '현재가', '타켓가', '매수 여부'])

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
                if ticker_info[1]['buy_end'] == True:
                    self.table.setItem(int(num), 3, QTableWidgetItem('매수완료'))
                else:
                    self.table.setItem(int(num), 3, QTableWidgetItem('매수전'))
        except :
            pass
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = My_window()
    window.show()
    app.exec_()


