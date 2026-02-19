from mcp_server.lib.indicators import calculate_macd_from_candles, calculate_rsi_from_candles
from mcp_server.providers.models import NormalizedCandle


def make_candles(count: int) -> list[NormalizedCandle]:
    base = 100.0
    candles: list[NormalizedCandle] = []
    for idx in range(count):
        close = base + idx * 0.5
        candles.append(
            NormalizedCandle(
                timestamp=1700000000 + idx * 86400,
                open=close - 1,
                high=close + 1,
                low=close - 2,
                close=close,
                volume=1000 + idx * 10,
            )
        )
    return candles


def test_rsi_from_candles_returns_points() -> None:
    points = calculate_rsi_from_candles(make_candles(60), period=14)
    assert points
    assert all(0 <= point.value <= 100 for point in points)


def test_macd_from_candles_returns_points() -> None:
    points = calculate_macd_from_candles(make_candles(80), 12, 26, 9)
    assert points
    assert isinstance(points[-1].histogram, float)


