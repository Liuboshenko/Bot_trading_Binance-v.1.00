import json, time
import pprint
import config, numpy, talib, websocket
from binance.client import Client
from binance.enums import *
from tradingview_ta import TA_Handler, Interval

client = Client(config.API_KEY, config.API_SECRET)

SOCKET = 'wss://stream.binance.com:9443/ws/ethbusd@kline_1m'

RSI_PERIOD = 5
RSI_OVERBOUGHT = 55
RSI_OVERSOLD = 34

TRADE_SYMBOL = 'ETHBUSD'
TRADE_QUANTITY = 0.00350

closes = []
in_position = False
switch_ord = True
counter_message = 1


def order(side, symbol, quantity, order_type=Client.ORDER_TYPE_MARKET):
    try:
        print('SENDING ORDER >>> ... ')

        order = client.create_order(side=side, symbol=symbol, quantity=quantity, type=order_type)
        print(order)
    except Exception as e:
        return False

    return True


def on_open(ws):
    print('[!] OPEN CONNECTION >>> ...')


def on_close(ws):
    print('[!] CLOSED CONNECTION >>> ...')


def on_message(ws, message):
    global closes, switch_ord
    global in_position, counter_message

    print(
        f'[!] DATA RECEIVED >>> {time.strftime("%H:%M:%S, %d/%m/%Y", time.localtime(time.time()))} PACK: [{counter_message}]')  # "ПОЛУЧЕНО СООБЩЕНИЕ"
    json_message = json.loads(message)
    # pprint.pprint(json_message)
    counter_message += 1

    candle = json_message['k']
    is_candle_closed = candle['x']
    close = candle['c']

    if is_candle_closed:
        print(f"[INFO] ... CANDLE CLOSED AT: {close}")
        closes.append(float(close))
        # print(f'[INFO] LIST_CLOSES:  {closes}')
        handler = TA_Handler(symbol="ETHBUSD", screener="crypto", exchange="BINANCE",
                             interval=Interval.INTERVAL_1_MINUTE)
        analysis = handler.get_analysis()
        general_analysis = analysis.summary
        print(f"[INFO] GENERAL ANALYSIS 1 MINUTE, RECOMMENDATION: {general_analysis['RECOMMENDATION']}")

        if len(closes) > RSI_PERIOD:
            np_closes = numpy.array(closes)
            rsi = talib.RSI(np_closes, RSI_PERIOD)
            print(f'[INFO] TABLE ALL RSI CALCULATED: {rsi}')
            last_rsi = rsi[-1]
            print(f'[INFO] ***** LAST_RSI *****: {last_rsi}')

            handler = TA_Handler(symbol="ETHBUSD", screener="crypto", exchange="BINANCE",
                                 interval=Interval.INTERVAL_15_MINUTES)
            analysis = handler.get_analysis()
            general_analysis = analysis.summary
            print(f"GENERAL ANALYSIS 15 MINUTES: {general_analysis['RECOMMENDATION']}")

            if last_rsi > RSI_OVERBOUGHT:
                print(f"[INFO] GENERAL ANALYSIS 15 MINUTES RECOMMENDATION: {general_analysis['RECOMMENDATION']}\n"
                      f"[INFO] ***** *****      LAST_RSI      ***** *****: {last_rsi}")
                if in_position and general_analysis['RECOMMENDATION'] == 'SELL':

                    balance = client.get_asset_balance(asset='ETH')
                    balance_sell = round(float(balance["free"]) * 0.977, 4)

                    print(f'[!!! WARNING !!!] OVERBOUGHT ***** SELL NOW!!! {balance_sell} "ETH"  *****')
                    while switch_ord:
                        order_succeeded = order(Client.SIDE_SELL, TRADE_SYMBOL, balance_sell)
                        if order_succeeded:
                            print("[INFO] SALE ORDER ... COMPLETED")
                            in_position = False
                            switch_ord = False
                    switch_ord = True

                else:
                    print(
                        "[INFO] WE DIDN'T BUY ANYTHING STILL, NOTHING TO SELL")

            if last_rsi < RSI_OVERSOLD and general_analysis['RECOMMENDATION'] == 'BUY':

                print(f"[INFO] GENERAL ANALYSIS 15 MINUTES RECOMMENDATION: {general_analysis['RECOMMENDATION']}\n"
                      f"[INFO] ***** *****      LAST_RSI      ***** *****: {last_rsi}")

                if in_position:
                    print('[INFO]  WE ARE IN POSITION ! DO NOT BUY YET')
                else:
                    print("[!!! WARNING !!!] OVERSOLD! BUY NOW!!!, I'M BUYING !!!")
                    while switch_ord:
                        order_succeeded = order(Client.SIDE_BUY, TRADE_SYMBOL, TRADE_QUANTITY)
                        if order_succeeded:
                            print("[INFO] BUY ORDER ... COMPLETED")
                            in_position = True
                            switch_ord = False
                    switch_ord = True


ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()
