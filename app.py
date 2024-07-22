from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache

app = Flask(__name__)

# Load API keys from environment variables
api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
news_api_key = os.getenv("NEWS_API_KEY")

# Configure caching
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stocks.db'
db = SQLAlchemy(app)

# Database model for stock data
class StockData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    relative_volume = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=pd.Timestamp.now)

# Initialize database
db.create_all()

# Fetch stock data from API
def fetch_stock_data():
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "FB", "TSLA", "NFLX", "NVDA", "ADBE", "PYPL"]
    stock_data = []
    for symbol in symbols:
        try:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={api_key}"
            response = requests.get(url)
            data = response.json()
            if "Time Series (5min)" in data:
                df = pd.DataFrame(data['Time Series (5min)']).T
                df = df.apply(pd.to_numeric)
                df['Volume'] = df['5. volume']
                avg_volume = df['Volume'].rolling(window=20).mean()
                relative_volume = df['Volume'] / avg_volume
                latest_relative_volume = relative_volume.iloc[-1]
                stock_data.append({
                    "symbol": symbol,
                    "relative_volume": latest_relative_volume,
                    "price": df['4. close'].iloc[-1]
                })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    stock_data.sort(key=lambda x: x['relative_volume'], reverse=True)
    return stock_data[:10]

# Cache stock data for 5 minutes
@cache.cached(timeout=300, key_prefix='stock_data')
def get_stock_data():
    return fetch_stock_data()

@app.route('/')
def index():
    stocks = get_stock_data()
    return render_template('index.html', stocks=stocks)

@app.route('/update')
def update_data():
    stocks = get_stock_data()
    return jsonify(stocks)

def fetch_stock_news(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={news_api_key}"
    response = requests.get(url)
    news_data = response.json()
    return news_data['articles']

@app.route('/news/<symbol>')
def news(symbol):
    news_data = fetch_stock_news(symbol)
    return render_template('news.html', symbol=symbol, news=news_data)

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=fetch_stock_data, trigger="interval", seconds=300)
    scheduler.start()
    app.run(debug=True)
