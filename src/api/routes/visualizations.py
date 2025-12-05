"""
Plotly visualization endpoints
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.data_loader import DataLoader

router = APIRouter(prefix="/api/viz", tags=["Visualizations"])

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./data/outputs")
loader = DataLoader(OUTPUT_DIR)


@router.get("/candlestick")
async def candlestick_chart(
    symbol: str = Query(..., description="Cryptocurrency symbol"),
    limit: int = Query(500, description="Number of data points")
):
    """Generate candlestick chart for OHLC data"""
    try:
        df = loader.load_ohlc(symbol=symbol, limit=limit)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
        
        # Create candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol
        )])
        
        fig.update_layout(
            title=f"{symbol} Price Chart (Candlestick)",
            xaxis_title="Time",
            yaxis_title="Price (USD)",
            template="plotly_dark",
            height=600
        )
        
        return json.loads(json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-line")
async def price_line_chart(
    symbol: str = Query(..., description="Cryptocurrency symbol"),
    limit: int = Query(500, description="Number of data points")
):
    """Generate line chart for closing prices"""
    try:
        df = loader.load_ohlc(symbol=symbol, limit=limit)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['close'],
            mode='lines',
            name='Close Price',
            line=dict(color='#00d4ff', width=2)
        ))
        
        fig.update_layout(
            title=f"{symbol} Closing Price Over Time",
            xaxis_title="Time",
            yaxis_title="Price (USD)",
            template="plotly_dark",
            height=500
        )
        
        return json.loads(json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volatility")
async def volatility_chart(
    symbol: str = Query(..., description="Cryptocurrency symbol"),
    limit: int = Query(500, description="Number of data points")
):
    """Generate volatility chart"""
    try:
        import numpy as np
        
        # Try to load volatility data first
        df_vol = loader.load_volatility(symbol=symbol, limit=limit)
        
        # If volatility data is empty or all NaN, calculate from OHLC data
        if df_vol.empty or df_vol['volatility'].isna().all() or (df_vol['volatility'] == 0).all():
            # Fallback: calculate volatility from OHLC data
            df_ohlc = loader.load_ohlc(symbol=symbol, limit=limit)
            
            if df_ohlc.empty:
                raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
            
            # Calculate volatility from OHLC using log returns of close prices
            df_ohlc = df_ohlc.sort_values('timestamp')
            df_ohlc['log_price'] = np.log(df_ohlc['close'])
            df_ohlc['log_returns'] = df_ohlc['log_price'].diff()
            
            # Calculate rolling volatility (10-second window, or use available data)
            window_size = min(10, len(df_ohlc))
            if window_size > 1:
                df_ohlc['volatility'] = df_ohlc['log_returns'].rolling(window=window_size, min_periods=2).std()
            else:
                df_ohlc['volatility'] = 0.0
            
            # Fill NaN values with 0
            df_ohlc['volatility'] = df_ohlc['volatility'].fillna(0.0)
            
            # Use OHLC data for plotting
            df = df_ohlc[['timestamp', 'volatility', 'symbol']].copy()
        else:
            # Use loaded volatility data, but filter out NaN values
            df = df_vol[['timestamp', 'volatility', 'symbol']].copy()
            df = df.dropna(subset=['volatility'])
            # Replace any remaining NaN with 0
            df['volatility'] = df['volatility'].fillna(0.0)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No volatility data found for symbol {symbol}")
        
        # Ensure volatility values are non-negative
        df['volatility'] = df['volatility'].abs()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['volatility'],
            mode='lines',
            name='Volatility',
            fill='tozeroy',
            line=dict(color='#ff6b6b', width=2),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Time: %{x}<br>' +
                          'Volatility: %{y:.6f}<br>' +
                          '<extra></extra>'
        ))
        
        fig.update_layout(
            title=f"{symbol} Volatility Over Time",
            xaxis_title="Time",
            yaxis_title="Volatility (Std of Log Returns)",
            template="plotly_dark",
            height=500,
            hovermode='x unified'
        )
        
        return json.loads(json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/multi-symbol")
async def multi_symbol_chart(
    symbols: str = Query(..., description="Comma-separated symbols (e.g., BTCUSD,ETHUSD)"),
    limit: int = Query(500, description="Number of data points per symbol")
):
    """Compare multiple symbols on one chart"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        fig = go.Figure()
        
        colors = ['#00d4ff', '#ff6b6b', '#4ecdc4', '#ffe66d', '#a8e6cf']
        
        for i, symbol in enumerate(symbol_list):
            df = loader.load_ohlc(symbol=symbol, limit=limit)
            if not df.empty:
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['close'],
                    mode='lines',
                    name=symbol,
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
        
        fig.update_layout(
            title="Multi-Symbol Price Comparison",
            xaxis_title="Time",
            yaxis_title="Price (USD)",
            template="plotly_dark",
            height=600
        )
        
        return json.loads(json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volume")
async def volume_chart(
    symbol: str = Query(..., description="Cryptocurrency symbol"),
    limit: int = Query(500, description="Number of data points")
):
    """Generate volume chart"""
    try:
        df = loader.load_ohlc(symbol=symbol, limit=limit)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volume',
            marker_color='#4ecdc4'
        ))
        
        fig.update_layout(
            title=f"{symbol} Trading Volume",
            xaxis_title="Time",
            yaxis_title="Volume",
            template="plotly_dark",
            height=400
        )
        
        return json.loads(json.dumps(fig.to_dict(), cls=PlotlyJSONEncoder))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

