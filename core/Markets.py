import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class Markets:
    def __init__(self, markets):
        self.url = 'https://financialmodelingprep.com/api/v3/quote/' + ','.join([markets[m] for m in markets])
        self.FLOAT_THRESHOLD = 0.0033
        self.markets = markets
        if os.getenv('VERSION') == 'local':
            self.conf_path = 'archive/markets_records.json'
        if os.getenv('VERSION') == 'production':
            self.conf_path = '/home/ec2-user/ASMAT/archive/markets_records.json'
        
    def get_quote(self):
        with requests.Session() as s:
            request = s.get(self.url, timeout = 15)
            quote_data = request.json()
        return quote_data
    
    def load_record(self):
        with open(self.conf_path) as json_file:
            quote_record = json.load(json_file)
        return quote_record
    
    def write_records(self, q):
        with open(self.conf_path, 'w') as json_file:
            json.dump(q, json_file, indent = 4)
    
    def ts_to_date(self, ts):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

    def real_time_check(self):
        new_quote = self.get_quote()
        records = self.load_record()
        alerts = []
        for i, idx in enumerate(self.markets):
            if self.ts_to_date(new_quote[i]['timestamp']) != self.ts_to_date(records[idx]['timestamp']):
                records[idx]['dayOpen'] = new_quote[i]['price']
                records[idx]['price'] = new_quote[i]['price']
                records[idx]['lastAlertPrice'] = new_quote[i]['price']
                records[idx]['last_max'] = new_quote[i]['price']
                records[idx]['last_min'] = new_quote[i]['price']
                records[idx]['timestamp'] = new_quote[i]['timestamp']
                records[idx]['lastAlertTimestamp'] = new_quote[i]['timestamp']
                time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f'[{time}] {idx} open price recorded')
                continue
            
            change_from_last_alert = (new_quote[i]['price'] - records[idx]['lastAlertPrice']) / records[idx]['dayOpen']
            change_from_last_max = (new_quote[i]['price'] - records[idx]['last_max']) / records[idx]['dayOpen']
            change_from_last_mim = (new_quote[i]['price'] - records[idx]['last_min']) / records[idx]['dayOpen']

            if change_from_last_alert >= self.FLOAT_THRESHOLD or change_from_last_mim >= self.FLOAT_THRESHOLD:
                float_rate = min(change_from_last_alert, change_from_last_mim)
                time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f'[{time}] {idx} Up {round(float_rate * 100, 2)}%')
                records[idx]['price'] = new_quote[i]['price']
                records[idx]['lastAlertPrice'] = new_quote[i]['price']
                records[idx]['last_max'] = new_quote[i]['price']
                records[idx]['last_min'] = new_quote[i]['price']
                records[idx]['timestamp'] = new_quote[i]['timestamp']
                records[idx]['lastAlertTimestamp'] = new_quote[i]['timestamp']
                alerts.append(f'{idx} Up {round(float_rate * 100, 2)}%')
                continue

            if change_from_last_alert <= -self.FLOAT_THRESHOLD or change_from_last_max <= -self.FLOAT_THRESHOLD:
                float_rate = min(change_from_last_alert, change_from_last_max)
                time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f'[{time}] {idx} Down {round(float_rate * 100, 2)}%')
                records[idx]['price'] = new_quote[i]['price']
                records[idx]['lastAlertPrice'] = new_quote[i]['price']
                records[idx]['last_max'] = new_quote[i]['price']
                records[idx]['last_min'] = new_quote[i]['price']
                records[idx]['timestamp'] = new_quote[i]['timestamp']
                records[idx]['lastAlertTimestamp'] = new_quote[i]['timestamp']
                alerts.append(f'{idx} Down {round(float_rate * 100, 2)}%')
                continue

            records[idx]['price'] = new_quote[i]['price']
            records[idx]['last_max'] = max(new_quote[i]['price'], records[idx]['last_max'])
            records[idx]['last_min'] = min(new_quote[i]['price'], records[idx]['last_min'])
            records[idx]['timestamp'] = new_quote[i]['timestamp']
            continue

        self.write_records(records)
        return alerts, new_quote

class GatherData:
    def __init__(self, tickers):
        self.tickers = tickers
        self.date = datetime.now().strftime('%Y-%m-%d')
        if os.getenv('VERSION') == 'local':
            self.path_base = 'archive/data/'
        if os.getenv('VERSION') == 'production':
            self.path_base = '/home/ec2-user/ASMAT/archive/data/'
            
    def gather_data(self):
        for t in self.tickers:
            url = 'https://financialmodelingprep.com/api/v3/historical-chart/1min/' + t
            raw_data = self.get_response(url)
            data = self.select_data(raw_data)
            self.write_records(t, data)
            time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f'[{time}] {t} {self.date} data recorded')

    def get_response(self, url):
        with requests.Session() as s:
            request = s.get(url, timeout = 15)
            quote_data = request.json()
        return quote_data
    
    def select_data(self, raw_data):
        rst = []
        for data in reversed(raw_data):
            if self.date != data['date'].strip().split()[0]:
                continue
            rst.append(data)
        return rst

    def write_records(self, ticker, data):
        path = self.path_base + f'{ticker}/{ticker}.' + self.date
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, 'w') as json_file:
            json.dump(data, json_file, indent = 4)
