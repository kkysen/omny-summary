#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pandas",
#     "typer",
# ]
# ///

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal
from pathlib import Path
from zipfile import ZipFile, is_zipfile
from zoneinfo import ZoneInfo
import pandas as pd
import typer
from pandas import DataFrame


FARE = Decimal("2.90")


def percent(fraction: Decimal, total: Decimal) -> Decimal:
    return ((fraction / total) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class FareCapResult:
    cap: "FareCap"
    uncapped_fare: Decimal
    capped_fare: Decimal
    caps_hit: int

    def fare_saved(self) -> Decimal:
        return self.uncapped_fare - self.capped_fare

    def fare_saved_percent(self) -> Decimal:
        return percent(self.fare_saved(), self.uncapped_fare)

    def __str__(self) -> str:
        return f"${self.uncapped_fare} capped to ${self.capped_fare} (${self.fare_saved()} saved, {self.fare_saved_percent()}%) with {self.caps_hit} caps using a fare cap of ${self.cap.cap} per {self.cap.days} days"


@dataclass(init=False)
class FareCap:
    days: int
    cap: Decimal
    trips: int
    last_fare: Decimal

    def __init__(self, days: int, cap: int):
        self.days = days
        self.cap = Decimal(cap)
        self.trips = int((self.cap / FARE).quantize(Decimal(1), rounding=ROUND_UP))
        trips_round_down = int(
            (self.cap / FARE).quantize(Decimal(1), rounding=ROUND_DOWN)
        )
        if trips_round_down == self.trips:
            self.last_fare = FARE
        else:
            self.last_fare = self.cap - FARE * trips_round_down

    def calculate_savings(self, df: DataFrame):
        first: datetime = datetime.min
        trips = 0

        total_uncapped_fare = Decimal(0)
        total_capped_fare = Decimal(0)
        caps_hit = 0

        for i, trip in df.iloc[::-1].iterrows():
            time: datetime = trip["Trip Time"]
            product_type = trip["Product Type"]
            fare = Decimal(str(trip["Fare Amount ($)"]).lstrip("$"))
            non_transfer = (
                product_type == "PAYGO" or product_type == "Free Trip – Weekly Fare Cap"
            )

            if not non_transfer:
                continue

            uncapped_fare = FARE

            days_since_first = (time.date() - first.date()).days
            if days_since_first >= self.days:
                first = time
                # print(first.date())
                trips = 1
            else:
                trips += 1
            if trips < self.trips:
                capped_fare = FARE
            elif trips == self.trips:
                capped_fare = self.last_fare
                caps_hit += 1
            else:
                capped_fare = Decimal(0)

            total_uncapped_fare += uncapped_fare
            total_capped_fare += capped_fare

            if self.days == 7:
                pass
                # print(
                #     f"time={time.strftime("%m/%d/%Y %I:%M %p")}, days={days_since_first}, trips={trips}, fare={fare}, capped_fare={capped_fare}, type={product_type}"
                # )

        return FareCapResult(
            cap=self,
            uncapped_fare=total_uncapped_fare,
            capped_fare=total_capped_fare,
            caps_hit=caps_hit,
        )


def omny_summary(df: DataFrame, future_card: bool):
    df["Trip Time"] = pd.to_datetime(df["Trip Time"]).dt.tz_convert(
        ZoneInfo("America/New_York")
    )

    weekly_cap = FareCap(days=7, cap=34)
    monthly_cap = FareCap(days=30, cap=132)

    print(f"{len(df)} Trips")
    print()

    trip_times = df["Trip Time"].apply(lambda dt: dt.strftime("%m/%d/%Y %I:%M %p")).iloc
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
    ) * FARE
    fare_saved = uncapped_fare - total_fare
    weeks_capped = fare_amount[f"${weekly_cap.last_fare}"]
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

    print(f"{weekly_cap.calculate_savings(df)}")
    print(f"{monthly_cap.calculate_savings(df)}")


def main(trip_history_path: Path, future_card: bool = False):
    if is_zipfile(trip_history_path):
        with ZipFile(trip_history_path) as zip:
            with zip.open("trip_history.csv") as f:
                df = pd.read_csv(f)
    else:
        df = pd.read_csv(trip_history_path)
    omny_summary(df, future_card=future_card)


if __name__ == "__main__":
    typer.run(main)
