from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

api_key = "YOUR_ALPHA_VANTAGE_API_KEY"

def fetch_stock_data():
    # Mock data function, replace with actual API calls
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "FB", "TSLA", "NFLX", "NVDA", "ADBE", "PYPL"]
    stock_data = []
    for symbol in symbols:
        # Fetch data from API
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
    stock_data.sort(key=lambda x: x['relative_volume'], reverse=True)
    return stock_data[:10]

stock_data = fetch_stock_data()

@app.route('/')
def index():
    return render_template('index.html', stocks=stock_data)

@app.route('/update')
def update_data():
    global stock_data
    stock_data = fetch_stock_data()
    return jsonify(stock_data)

def fetch_stock_news(symbol):
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey=YOUR_NEWS_API_KEY"
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
