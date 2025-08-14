#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pandas",
#     "typer",
# ]
# ///

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import typer
from pandas import DataFrame


def percent(fraction: Decimal, total: Decimal) -> Decimal:
    return ((fraction / total) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def omny_summary(df: DataFrame, future_card: bool):
    print(f"{len(df)} Trips")
    print()

    trip_times = (
        pd.to_datetime(df["Trip Time"])
        .dt.tz_convert(ZoneInfo("America/New_York"))
        .apply(lambda dt: dt.strftime("%m/%d/%Y %I:%M %p"))
        .iloc
    )
    print(f"first: {trip_times[-1]}")
    print(f" last: {trip_times[0]}")
    print()

    mode = df["Mode"].value_counts()
    print(mode.to_string())
    print()

    product_type = df["Product Type"].value_counts()
    print(product_type.to_string())
    print()

    fare_amount = df["Fare Amount ($)"].value_counts()
    print(fare_amount.to_string())
    print()

    fare = df["Fare Amount ($)"].str.replace("$", "", regex=False).apply(Decimal)
    total_fare = fare.sum()
    uncapped_fare = (
        product_type["PAYGO"] + product_type["Free Trip – Weekly Fare Cap"]
    ) * Decimal("2.90")
    fare_saved = uncapped_fare - total_fare
    weeks_capped = fare_amount["$2.10"]
    print(f"    Total Fare: ${total_fare}")
    print(f"  Weeks Capped: {weeks_capped}")
    print(f"Fare Cap Saved: ${fare_saved}, {percent(fare_saved, uncapped_fare)}%")
    print(f" Uncapped Fare: ${uncapped_fare}")
    print()

    if future_card:
        future_fare_saved = (Decimal("0.05") * total_fare).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ) + 5 * weeks_capped
        print(
            f"Future Card Savings: ${future_fare_saved}, {percent(future_fare_saved, total_fare)}%"
        )
        print(
            f"   Combined Savings: ${future_fare_saved + fare_saved}, {percent(future_fare_saved + fare_saved, uncapped_fare)}%"
        )
        print()


def main(trip_history_path: Path, future_card: bool = False):
    df = pd.read_csv(trip_history_path)
    omny_summary(df, future_card=future_card)


if __name__ == "__main__":
    typer.run(main)
