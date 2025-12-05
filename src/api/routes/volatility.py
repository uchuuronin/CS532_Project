"""
Volatility data endpoints
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.data_loader import DataLoader
from api.models import VolatilityResponse, VolatilityData

router = APIRouter(prefix="/api/volatility", tags=["Volatility"])

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./data/outputs")
loader = DataLoader(OUTPUT_DIR)


def calculate_volatility_from_ohlc(df_ohlc):
    """Calculate volatility from OHLC data using log returns"""
    if df_ohlc.empty or len(df_ohlc) < 2:
        return df_ohlc.copy()
    
    df_ohlc = df_ohlc.sort_values('timestamp').copy()
    
    # Calculate log returns from close prices
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
    
    return df_ohlc


@router.get("/", response_model=VolatilityResponse)
async def get_volatility(
    symbol: Optional[str] = Query(None, description="Cryptocurrency symbol"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(1000, description="Maximum number of records")
):
    """Get volatility data"""
    try:
        # Try to load volatility data first
        df = loader.load_volatility(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # If volatility data is empty or all NaN, calculate from OHLC data
        if df.empty or df['volatility'].isna().all() or (df['volatility'] == 0).all():
            # Fallback: calculate volatility from OHLC data
            df_ohlc = loader.load_ohlc(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            if df_ohlc.empty:
                return VolatilityResponse(data=[], count=0, symbol=symbol)
            
            # Calculate volatility from OHLC
            df_ohlc = calculate_volatility_from_ohlc(df_ohlc)
            df = df_ohlc[['timestamp', 'volatility', 'symbol']].copy()
        else:
            # Filter out NaN values and replace with 0
            df = df.dropna(subset=['volatility'])
            df['volatility'] = df['volatility'].fillna(0.0)
        
        if df.empty:
            return VolatilityResponse(data=[], count=0, symbol=symbol)
        
        # Ensure volatility values are non-negative
        df['volatility'] = df['volatility'].abs()
        
        data = []
        for _, row in df.iterrows():
            data.append(VolatilityData(
                timestamp=row['timestamp'],
                volatility=float(row['volatility']),
                symbol=row['symbol']
            ))
        
        return VolatilityResponse(data=data, count=len(data), symbol=symbol)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

