"""RSI/MACD and local analytics helpers."""

from __future__ import annotations

from dataclasses import dataclass

from mcp_server.providers.models import NormalizedCandle, NormalizedMacdPoint, NormalizedRsiPoint


def ema(values: list[float], period: int) -> list[float | None]:
    if len(values) < period:
        return []
    multiplier = 2 / (period + 1)
    output: list[float | None] = [None] * len(values)
    previous = sum(values[:period]) / period
    output[period - 1] = previous
    for idx in range(period, len(values)):
        previous = (values[idx] - previous) * multiplier + previous
        output[idx] = previous
    return output


def calculate_rsi_from_candles(candles: list[NormalizedCandle], period: int = 14) -> list[NormalizedRsiPoint]:
    if len(candles) <= period:
        return []
    closes = [candle.close for candle in candles]
    gains: list[float] = []
    losses: list[float] = []
    for idx in range(1, len(closes)):
        delta = closes[idx] - closes[idx - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    points: list[NormalizedRsiPoint] = []
    for idx in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[idx]) / period
        avg_loss = (avg_loss * (period - 1) + losses[idx]) / period
        rs = 100.0 if avg_loss == 0 else avg_gain / avg_loss
        rsi = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + rs))
        points.append(NormalizedRsiPoint(timestamp=candles[idx + 1].timestamp, value=rsi))
    return points


def calculate_macd_from_candles(
    candles: list[NormalizedCandle],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> list[NormalizedMacdPoint]:
    if len(candles) < slow_period + signal_period:
        return []
    closes = [candle.close for candle in candles]
    fast = ema(closes, fast_period)
    slow = ema(closes, slow_period)
    macd_line: list[float | None] = []
    for idx in range(len(closes)):
        if fast[idx] is None or slow[idx] is None:
            macd_line.append(None)
        else:
            macd_line.append(float(fast[idx] - slow[idx]))  # type: ignore[operator]
    clean_macd = [value for value in macd_line if value is not None]
    signal_raw = ema([float(value) for value in clean_macd], signal_period)
    if not signal_raw:
        return []
    output: list[NormalizedMacdPoint] = []
    signal_cursor = 0
    for idx, macd in enumerate(macd_line):
        if macd is None:
            continue
        signal = signal_raw[signal_cursor]
        signal_cursor += 1
        if signal is None:
            continue
        output.append(
            NormalizedMacdPoint(
                timestamp=candles[idx].timestamp,
                macd=float(macd),
                signal=float(signal),
                histogram=float(macd - signal),
            )
        )
    return output


def calc_sma(values: list[float], period: int) -> list[float | None]:
    output: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return output
    window_sum = sum(values[:period])
    output[period - 1] = window_sum / period
    for idx in range(period, len(values)):
        window_sum += values[idx] - values[idx - period]
        output[idx] = window_sum / period
    return output


def calc_ema(values: list[float], period: int) -> list[float | None]:
    output: list[float | None] = [None] * len(values)
    if period <= 0 or len(values) < period:
        return output
    previous = sum(values[:period]) / period
    output[period - 1] = previous
    multiplier = 2 / (period + 1)
    for idx in range(period, len(values)):
        previous = (values[idx] - previous) * multiplier + previous
        output[idx] = previous
    return output


def latest_series_value(
    candles: list[NormalizedCandle], values: list[float | None]
) -> tuple[int, float] | None:
    for idx in range(len(values) - 1, -1, -1):
        value = values[idx]
        if value is not None:
            return candles[idx].timestamp, float(value)
    return None


def calc_atr(candles: list[NormalizedCandle], period: int) -> list[float | None]:
    output: list[float | None] = [None] * len(candles)
    if len(candles) <= period:
        return output
    true_ranges: list[float] = []
    for idx in range(1, len(candles)):
        high_low = candles[idx].high - candles[idx].low
        high_prev_close = abs(candles[idx].high - candles[idx - 1].close)
        low_prev_close = abs(candles[idx].low - candles[idx - 1].close)
        true_ranges.append(max(high_low, high_prev_close, low_prev_close))
    atr = sum(true_ranges[:period]) / period
    output[period] = atr
    for idx in range(period, len(true_ranges)):
        atr = (atr * (period - 1) + true_ranges[idx]) / period
        output[idx + 1] = atr
    return output


@dataclass
class AdxPoint:
    adx: float
    plus_di: float
    minus_di: float


def calc_adx(candles: list[NormalizedCandle], period: int) -> list[AdxPoint | None]:
    output: list[AdxPoint | None] = [None] * len(candles)
    if len(candles) <= period * 2:
        return output
    tr: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for idx in range(1, len(candles)):
        up_move = candles[idx].high - candles[idx - 1].high
        down_move = candles[idx - 1].low - candles[idx].low
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        high_low = candles[idx].high - candles[idx].low
        high_prev_close = abs(candles[idx].high - candles[idx - 1].close)
        low_prev_close = abs(candles[idx].low - candles[idx - 1].close)
        tr.append(max(high_low, high_prev_close, low_prev_close))
    smooth_tr = sum(tr[:period])
    smooth_plus_dm = sum(plus_dm[:period])
    smooth_minus_dm = sum(minus_dm[:period])
    dx_values: list[float] = []
    for idx in range(period, len(tr)):
        smooth_tr = smooth_tr - (smooth_tr / period) + tr[idx]
        smooth_plus_dm = smooth_plus_dm - (smooth_plus_dm / period) + plus_dm[idx]
        smooth_minus_dm = smooth_minus_dm - (smooth_minus_dm / period) + minus_dm[idx]
        plus_di = 0.0 if smooth_tr == 0 else (100 * smooth_plus_dm) / smooth_tr
        minus_di = 0.0 if smooth_tr == 0 else (100 * smooth_minus_dm) / smooth_tr
        sum_di = plus_di + minus_di
        dx = 0.0 if sum_di == 0 else (100 * abs(plus_di - minus_di)) / sum_di
        dx_values.append(dx)
        if len(dx_values) == period:
            adx = sum(dx_values) / period
            output[idx + 1] = AdxPoint(adx=adx, plus_di=plus_di, minus_di=minus_di)
        elif len(dx_values) > period:
            previous = output[idx] or output[idx - 1]
            prior_adx = previous.adx if previous else dx_values[-2]
            adx = (prior_adx * (period - 1) + dx) / period
            output[idx + 1] = AdxPoint(adx=adx, plus_di=plus_di, minus_di=minus_di)
    return output


@dataclass
class StochasticPoint:
    k: float
    d: float | None


def calc_stochastic(candles: list[NormalizedCandle], k_period: int, d_period: int) -> list[StochasticPoint | None]:
    output: list[StochasticPoint | None] = [None] * len(candles)
    if len(candles) < k_period:
        return output
    k_values: list[float | None] = [None] * len(candles)
    for idx in range(k_period - 1, len(candles)):
        window = candles[idx - k_period + 1 : idx + 1]
        highest_high = max(item.high for item in window)
        lowest_low = min(item.low for item in window)
        denominator = highest_high - lowest_low
        k_value = 50.0 if denominator == 0 else (100 * (candles[idx].close - lowest_low)) / denominator
        k_values[idx] = k_value
    d_values = calc_sma([0.0 if value is None else value for value in k_values], d_period)
    for idx in range(len(candles)):
        if k_values[idx] is None:
            continue
        output[idx] = StochasticPoint(k=float(k_values[idx]), d=d_values[idx])
    return output


def calc_obv(candles: list[NormalizedCandle]) -> list[float]:
    if not candles:
        return []
    output: list[float] = [0.0]
    for idx in range(1, len(candles)):
        prev = output[idx - 1]
        if candles[idx].close > candles[idx - 1].close:
            output.append(prev + candles[idx].volume)
        elif candles[idx].close < candles[idx - 1].close:
            output.append(prev - candles[idx].volume)
        else:
            output.append(prev)
    return output


def calc_vwap(candles: list[NormalizedCandle]) -> list[float | None]:
    output: list[float | None] = []
    cumulative_tp_volume = 0.0
    cumulative_volume = 0.0
    for candle in candles:
        typical_price = (candle.high + candle.low + candle.close) / 3
        cumulative_tp_volume += typical_price * candle.volume
        cumulative_volume += candle.volume
        output.append((cumulative_tp_volume / cumulative_volume) if cumulative_volume > 0 else None)
    return output


def find_support_resistance_levels(
    candles: list[NormalizedCandle], lookback: int, levels_count: int
) -> tuple[list[float], list[float]]:
    recent = candles[-lookback:]
    if not recent:
        return ([], [])
    lows = sorted(candle.low for candle in recent)
    highs = sorted((candle.high for candle in recent), reverse=True)
    supports: list[float] = []
    resistances: list[float] = []
    min_gap = 0.005
    for value in lows:
        if len(supports) >= levels_count:
            break
        if not any(abs(level - value) / max(level, 1) < min_gap for level in supports):
            supports.append(value)
    for value in highs:
        if len(resistances) >= levels_count:
            break
        if not any(abs(level - value) / max(level, 1) < min_gap for level in resistances):
            resistances.append(value)
    return (sorted(supports), sorted(resistances))


def detect_chart_patterns_from_candles(candles: list[NormalizedCandle]) -> list[str]:
    recent = candles[-140:]
    if len(recent) < 40:
        return ["Insufficient data for pattern detection."]
    closes = [candle.close for candle in recent]
    patterns: list[str] = []
    peaks: list[tuple[int, float]] = []
    troughs: list[tuple[int, float]] = []
    for idx in range(2, len(closes) - 2):
        if closes[idx] > closes[idx - 1] > closes[idx - 2] and closes[idx] > closes[idx + 1] > closes[idx + 2]:
            peaks.append((idx, closes[idx]))
        if closes[idx] < closes[idx - 1] < closes[idx - 2] and closes[idx] < closes[idx + 1] < closes[idx + 2]:
            troughs.append((idx, closes[idx]))
    for i in range(len(peaks)):
        for j in range(i + 1, len(peaks)):
            p1_idx, p1_value = peaks[i]
            p2_idx, p2_value = peaks[j]
            if p2_idx - p1_idx < 6:
                continue
            top_distance = abs(p1_value - p2_value) / max((p1_value + p2_value) / 2, 1)
            if top_distance > 0.03:
                continue
            between = closes[p1_idx : p2_idx + 1]
            min_between = min(between)
            drawdown = ((min(p1_value, p2_value) - min_between) / min(p1_value, p2_value)) * 100
            if drawdown >= 3:
                patterns.append("Double Top")
                i = len(peaks)
                break
    for i in range(len(troughs)):
        for j in range(i + 1, len(troughs)):
            t1_idx, t1_value = troughs[i]
            t2_idx, t2_value = troughs[j]
            if t2_idx - t1_idx < 6:
                continue
            bottom_distance = abs(t1_value - t2_value) / max((t1_value + t2_value) / 2, 1)
            if bottom_distance > 0.03:
                continue
            between = closes[t1_idx : t2_idx + 1]
            max_between = max(between)
            rally = ((max_between - max(t1_value, t2_value)) / max(t1_value, t2_value)) * 100
            if rally >= 3:
                patterns.append("Double Bottom")
                i = len(troughs)
                break
    if len(peaks) >= 3:
        for idx in range(1, len(peaks) - 1):
            left = peaks[idx - 1]
            head = peaks[idx]
            right = peaks[idx + 1]
            shoulders_close = abs(left[1] - right[1]) / max((left[1] + right[1]) / 2, 1) <= 0.04
            head_higher = head[1] > left[1] * 1.02 and head[1] > right[1] * 1.02
            if shoulders_close and head_higher and right[0] - left[0] >= 8:
                patterns.append("Head and Shoulders")
                break
    return patterns if patterns else ["No major pattern detected with current heuristic."]


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def calc_returns_from_candles(candles: list[NormalizedCandle]) -> list[float]:
    returns: list[float] = []
    for idx in range(1, len(candles)):
        if candles[idx - 1].close <= 0:
            continue
        returns.append((candles[idx].close - candles[idx - 1].close) / candles[idx - 1].close)
    return returns


