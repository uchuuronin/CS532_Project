#!/usr/bin/env python3
"""
Stream Processor (consumer) for Milestone 3
- Consumes normalized trade JSON from Kafka topic (e.g. 'crypto-trades')
- Performs data cleaning and validation
- Aggregates 1-second OHLC per symbol
- Computes 10-second rolling volatility (std of log returns)
- Persists outputs to Parquet/CSV with periodic checkpointing

This updated version fixes a bug that could cause KeyError: 'timestamp' when
pandas reset_index produced a column named 'ts' (or similar) instead of
'index'. It explicitly normalizes the timestamp column after reset_index so
`flush_outputs()` can safely access `df_ohlc['timestamp']`.

Drop this file into src/consumer/ and run with the project's docker-compose or locally.

Dependencies (pip):
  kafka-python or confluent-kafka (this script uses kafka-python),
  pandas, pyarrow, fastparquet (or pyarrow for parquet),
  python-dateutil

"""

import os
import json
import time
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from kafka import KafkaConsumer

# ---------- Configuration ----------
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "crypto-trades")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "stream-processor-group")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./data/outputs")  # ensure writable
CHECKPOINT_FILE = os.getenv("CHECKPOINT_FILE", "checkpoint.json")
MAX_BUFFER_SECONDS = int(os.getenv("MAX_BUFFER_SECONDS", "5"))  # buffer for out-of-order
PARQUET_CHUNK_SECONDS = int(os.getenv("PARQUET_CHUNK_SECONDS", "10"))

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("stream_processor")

# ---------- Utilities ----------

def parse_timestamp(ts):
    """Accepts integer ms since epoch or ISO string. Returns pd.Timestamp (UTC)."""
    if ts is None:
        return None
    # ms integer
    try:
        if isinstance(ts, (int, float)):
            # assume ms
            return pd.to_datetime(int(ts), unit="ms", utc=True)
        if isinstance(ts, str) and ts.isdigit():
            return pd.to_datetime(int(ts), unit="ms", utc=True)
    except Exception:
        pass
    try:
        return pd.to_datetime(ts, utc=True)
    except Exception:
        return None


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


# ---------- Processor class ----------
class StreamProcessor:
    def __init__(self,
                 kafka_bootstrap=KAFKA_BOOTSTRAP,
                 topic=KAFKA_TOPIC,
                 group_id=GROUP_ID,
                 output_dir=OUTPUT_DIR,
                 checkpoint_file=CHECKPOINT_FILE,
                 max_buffer_seconds=MAX_BUFFER_SECONDS):
        self.topic = topic
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=kafka_bootstrap,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            consumer_timeout_ms=1000,
        )
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.checkpoint_file = checkpoint_file
        self.max_buffer = timedelta(seconds=max_buffer_seconds)

        # per-symbol buffer of raw trades (deque of dicts)
        self.buffers = defaultdict(deque)
        # last emitted window end time
        self.last_emitted = {}
        # holding aggregated 1s OHLC frames before writing
        self.ohlc_out = []
        self.vol_out = []

    # ---------- Cleaning ----------
    def clean_trade(self, trade):
        """Validate and normalize incoming trade dict. Return None if invalid."""
        # required keys: timestamp, symbol, price, quantity
        ts = trade.get("timestamp") or trade.get("ts") or trade.get("time")
        symbol = trade.get("symbol") or trade.get("s")
        price = safe_float(trade.get("price") or trade.get("p"))
        qty = safe_float(trade.get("quantity") or trade.get("q") or trade.get("size"))
        trade_id = trade.get("trade_id") or trade.get("id")

        tstamp = parse_timestamp(ts)
        if not (tstamp and symbol and price and qty):
            return None
        if price <= 0 or qty <= 0:
            return None

        return {
            "timestamp": tstamp,  # pd.Timestamp UTC
            "symbol": str(symbol).upper(),
            "price": price,
            "quantity": qty,
            "trade_id": trade_id,
        }

    # ---------- Buffering & aggregation helpers ----------
    def add_to_buffer(self, t):
        """Add cleaned trade into per-symbol buffer (maintain sorted by timestamp)."""
        sym = t["symbol"]
        buf = self.buffers[sym]
        # append keeping approximate order; simple approach: append then prune on emit
        buf.append(t)

    def emit_ready_windows(self, watermark_time=None):
        """For each symbol, emit all complete 1s windows that end before watermark_time - max_buffer.
        watermark_time should be current max seen time.
        """
        if watermark_time is None:
            return
        cutoff = watermark_time - self.max_buffer
        for sym, buf in list(self.buffers.items()):
            if not buf:
                continue
            # move buffered trades into DataFrame
            df = pd.DataFrame([{
                "ts": x["timestamp"],
                "price": x["price"],
                "qty": x["quantity"],
            } for x in buf])
            df = df.sort_values("ts")
            df = df.set_index("ts")
            # determine windows that fully end before cutoff
            df = df[~df.index.duplicated(keep='first')]
            if df.empty:
                continue
            # rows up to cutoff are ready to aggregate
            df_ready = df[df.index <= cutoff]
            if df_ready.empty:
                continue

            # resample to 1s OHLC (tumbling)
            ohlc = df_ready['price'].resample('1s').agg(['first','max','min','last'])
            ohlc.rename(columns={'first':'open','max':'high','min':'low','last':'close'}, inplace=True)
            ohlc = ohlc.dropna(subset=['open'])
            # volume per second
            volume = df_ready['qty'].resample('1s').sum().reindex(ohlc.index).fillna(0)
            ohlc['symbol'] = sym
            ohlc['volume'] = volume.values

            # reset index and ensure a column named 'timestamp' exists
            ohlc = ohlc.reset_index()
            # the first column after reset_index is the timestamp column (its name may vary)
            if len(ohlc.columns) >= 1:
                ts_col = ohlc.columns[0]
                if ts_col != 'timestamp':
                    ohlc.rename(columns={ts_col: 'timestamp'}, inplace=True)
            # ensure dtype is datetime (UTC)
            ohlc['timestamp'] = pd.to_datetime(ohlc['timestamp'], utc=True)

            # volatility per second (std of log returns) -> we compute per-second series
            # Use a rolling window approach: calculate volatility from log returns within each 1s window
            def calc_volatility(price_series):
                """Calculate volatility from price series"""
                if len(price_series) < 2:
                    # Need at least 2 points to calculate returns
                    return np.nan
                log_prices = np.log(price_series)
                log_returns = log_prices.diff().dropna()
                if len(log_returns) == 0:
                    return np.nan
                vol = log_returns.std()
                # Return 0 if vol is NaN or inf, otherwise return the value
                if pd.isna(vol) or np.isinf(vol):
                    return 0.0
                return vol
            
            vol_series = df_ready['price'].resample('1s').apply(calc_volatility)
            vol_df = vol_series.reindex(ohlc['timestamp'].values).reset_index()
            # normalize column names: reset_index yields [timestamp_col, value_col]
            if len(vol_df.columns) >= 2:
                vol_df.columns = ['timestamp', 'volatility']
            else:
                # fallback: create empty volatility frame matching ohlc timestamps
                vol_df = pd.DataFrame({'timestamp': ohlc['timestamp'].values, 'volatility': np.nan})
            
            # Fill NaN values with 0 or forward fill for better visualization
            vol_df['volatility'] = vol_df['volatility'].fillna(0.0)
            vol_df['symbol'] = sym
            vol_df['timestamp'] = pd.to_datetime(vol_df['timestamp'], utc=True)

            # append to output lists
            self.ohlc_out.append(ohlc)
            self.vol_out.append(vol_df)

            # remove consumed rows from buffer (keep only > cutoff)
            remaining = df[df.index > cutoff]
            new_deque = deque()
            for _, row in remaining.reset_index().iterrows():
                new_deque.append({
                    'timestamp': row['ts'],
                    'price': row['price'],
                    'quantity': row.get('qty', 0)
                })
            self.buffers[sym] = new_deque

    # ---------- Persistence ----------
    def flush_outputs(self):
        """Write accumulated ohlc_out and vol_out to parquet files partitioned by date/symbol.
        After writing, clear buffers and update checkpoint.
        """
        if not self.ohlc_out and not self.vol_out:
            return
        # concat
        if self.ohlc_out:
            df_ohlc = pd.concat(self.ohlc_out, ignore_index=True)
            # ensure timestamp column exists and is datetime
            if 'timestamp' not in df_ohlc.columns:
                # try to find a likely timestamp column
                for c in df_ohlc.columns:
                    if 'time' in c.lower() or c.lower() in ('ts','index'):
                        df_ohlc.rename(columns={c: 'timestamp'}, inplace=True)
                        break
            df_ohlc['timestamp'] = pd.to_datetime(df_ohlc['timestamp'], utc=True)
            df_ohlc['date'] = df_ohlc['timestamp'].dt.strftime('%Y-%m-%d')
            # write parquet per-symbol-date
            for (sym,date), grp in df_ohlc.groupby(['symbol','date']):
                outdir = os.path.join(self.output_dir, 'ohlc', f'symbol={sym}', f'date={date}')
                os.makedirs(outdir, exist_ok=True)
                path = os.path.join(outdir, f'ohlc_{sym}_{date}_{int(time.time())}.parquet')
                grp.to_parquet(path, index=False)
                logger.info(f'Wrote {len(grp)} ohlc rows to {path}')
            self.ohlc_out = []
        if self.vol_out:
            df_vol = pd.concat(self.vol_out, ignore_index=True)
            if 'timestamp' not in df_vol.columns:
                for c in df_vol.columns:
                    if 'time' in c.lower() or c.lower() in ('ts','index'):
                        df_vol.rename(columns={c: 'timestamp'}, inplace=True)
                        break
            df_vol['timestamp'] = pd.to_datetime(df_vol['timestamp'], utc=True)
            df_vol['date'] = df_vol['timestamp'].dt.strftime('%Y-%m-%d')
            for (sym,date), grp in df_vol.groupby(['symbol','date']):
                outdir = os.path.join(self.output_dir, 'volatility', f'symbol={sym}', f'date={date}')
                os.makedirs(outdir, exist_ok=True)
                path = os.path.join(outdir, f'vol_{sym}_{date}_{int(time.time())}.parquet')
                grp.to_parquet(path, index=False)
                logger.info(f'Wrote {len(grp)} vol rows to {path}')
            self.vol_out = []
        # checkpoint: store latest processed time per symbol
        chk = {sym: (self.buffers[sym][-1]['timestamp'].isoformat() if self.buffers[sym] else None) for sym in self.buffers}
        tmp = self.checkpoint_file + '.tmp'
        with open(tmp,'w',encoding='utf-8') as f:
            json.dump({'last_seen': chk, 'written_at': datetime.utcnow().isoformat()}, f)
        os.replace(tmp, self.checkpoint_file)
        logger.info('Checkpoint updated')

    # ---------- Main loop ----------
    def start(self):
        logger.info('Starting StreamProcessor')
        max_seen_time = None
        last_flush = time.time()
        try:
            for msg in self.consumer:
                # message value already deserialized to dict
                raw = msg.value
                cleaned = self.clean_trade(raw)
                if cleaned is None:
                    logger.debug('Dropped invalid trade: %s', raw)
                    # commit offset and continue
                    self.consumer.commit()
                    continue
                self.add_to_buffer(cleaned)
                t = cleaned['timestamp']
                if max_seen_time is None or t > max_seen_time:
                    max_seen_time = t
                # try emit windows using watermark = max_seen_time
                self.emit_ready_windows(watermark_time=max_seen_time)

                # periodic flush
                if time.time() - last_flush >= PARQUET_CHUNK_SECONDS:
                    self.flush_outputs()
                    # commit consumer offsets after successful flush
                    try:
                        self.consumer.commit()
                    except Exception as e:
                        logger.exception('Failed to commit offsets: %s', e)
                    last_flush = time.time()
        except KeyboardInterrupt:
            logger.info('Interrupted, flushing outputs')
            self.flush_outputs()
        except Exception:
            logger.exception('Unhandled error')
            self.flush_outputs()
        finally:
            try:
                self.consumer.close()
            except Exception:
                pass


# ---------- CLI ----------
if __name__ == '__main__':
    sp = StreamProcessor()
    sp.start()
