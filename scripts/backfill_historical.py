#!/usr/bin/env python3
"""Backfill historical metrics for Baogang tailings dam using open Sentinel-2 imagery."""

import json
import os
from datetime import date
from typing import Dict, List, Optional, Tuple

import numpy as np
import requests
import rasterio
from rasterio.enums import Resampling
from rasterio.mask import mask
from rasterio.warp import reproject
from shapely.geometry import Point, mapping
from shapely.ops import transform
import pyproj

S2_COLLECTION = "sentinel-2-l2a"
STAC_URL = "https://earth-search.aws.element84.com/v1/search"
POINT_LON = 109.685119
POINT_LAT = 40.635497
BUFFER_METERS = 5000

BANDS_10M = {
    "B02": "blue",
    "B04": "red",
    "B08": "nir"
}
BANDS_20M = {
    "B8A": "narrow_nir",
    "B11": "swir"
}

ALL_BANDS = list(BANDS_10M.keys()) + list(BANDS_20M.keys())


def make_buffer_geometry() -> Dict:
    point = Point(POINT_LON, POINT_LAT)
    utm_crs = pyproj.CRS.from_epsg(32649)
    to_utm = pyproj.Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True).transform
    to_wgs = pyproj.Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True).transform
    buffered = transform(to_utm, point).buffer(BUFFER_METERS)
    buffered_wgs = transform(to_wgs, buffered)
    return mapping(buffered_wgs)


BUFFER_GEOM = make_buffer_geometry()


class SentinelFetcher:
    def __init__(self):
        self.session = requests.Session()

    def search(self, start: date, end: date) -> Optional[Dict]:
        payload = {
            "collections": [S2_COLLECTION],
            "datetime": f"{start.isoformat()}/{end.isoformat()}",
            "limit": 50,
            "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
            "intersects": BUFFER_GEOM,
            "query": {
                "eo:cloud_cover": {"lt": 30}
            }
        }
        resp = self.session.post(STAC_URL, json=payload, timeout=60)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            return None
        return features[0]


fetcher = SentinelFetcher()

def compute_metrics(feature: Dict) -> Optional[Tuple[Dict[str, float], str]]:
    assets = feature.get("assets", {})
    missing = [b for b in ALL_BANDS if b not in assets]
    if missing:
        return None

    b11_href = assets["B11"]["href"]
    with rasterio.Env(AWS_NO_SIGN_REQUEST="YES"):
        with rasterio.open(b11_href) as base_src:
            base_data, base_transform = mask(
                base_src,
                [BUFFER_GEOM],
                crop=True,
                filled=False
            )
            base_arr = np.ma.filled(base_data[0], np.nan).astype("float32")
            base_arr[base_arr == 0] = np.nan
            base_crs = base_src.crs

    out_shape = base_arr.shape
    band_arrays = {"B11": base_arr}

    for band in ["B02", "B04", "B08", "B8A"]:
        href = assets[band]["href"]
        with rasterio.Env(AWS_NO_SIGN_REQUEST="YES"):
            with rasterio.open(href) as src:
                data, transform = mask(
                    src,
                    [BUFFER_GEOM],
                    crop=True,
                    filled=False
                )
                arr = np.ma.filled(data[0], np.nan).astype("float32")
                arr[arr == 0] = np.nan
                if arr.shape != out_shape or transform != base_transform:
                    dest = np.empty(out_shape, dtype="float32")
                    dest.fill(np.nan)
                    reproject(
                        arr,
                        dest,
                        src_transform=transform,
                        src_crs=src.crs,
                        dst_transform=base_transform,
                        dst_crs=base_crs,
                        resampling=Resampling.bilinear,
                        src_nodata=0,
                        dst_nodata=np.nan
                    )
                    arr = dest
                band_arrays[band] = arr

    red = band_arrays["B04"]
    nir = band_arrays["B08"]
    narrow_nir = band_arrays["B8A"]
    swir = band_arrays["B11"]
    blue = band_arrays["B02"]

    ndvi = safe_index(nir, red)
    ndmi = safe_index(narrow_nir, swir)
    bsi = safe_ratio((swir + red) - (nir + blue), (swir + red) + (nir + blue))

    scale_factor = 10000.0
    red /= scale_factor
    nir /= scale_factor
    narrow_nir /= scale_factor
    swir /= scale_factor
    blue = band_arrays["B02"] / scale_factor

    ndvi = safe_index(nir, red)
    ndmi = safe_index(narrow_nir, swir)
    bsi = safe_ratio((swir + red) - (nir + blue), (swir + red) + (nir + blue))

    metrics = {
        "ndvi": float(np.nanmean(ndvi)),
        "ndmi": float(np.nanmean(ndmi)),
        "bsi": float(np.nanmean(bsi))
    }

    image_date = feature["properties"].get("datetime", "")
    return metrics, image_date


def safe_index(numerator_a: np.ndarray, numerator_b: np.ndarray) -> np.ndarray:
    numerator = numerator_a - numerator_b
    denominator = numerator_a + numerator_b
    return safe_ratio(numerator, denominator)


def safe_ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.true_divide(numerator, denominator)
        result[~np.isfinite(result)] = np.nan
        return result


def month_range(start_year: int, start_month: int, end_year: int, end_month: int) -> List[Tuple[int, int]]:
    months = []
    current = date(start_year, start_month, 1)
    end = date(end_year, end_month, 1)
    while current <= end:
        months.append((current.year, current.month))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def backfill(start_year: int = 2024, start_month: int = 1) -> Dict:
    today = date.today()
    months = month_range(start_year, start_month, today.year, today.month)
    historical: Dict[str, Dict] = {}
    for year, month in months:
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)
        feature = fetcher.search(start, end)
        if not feature:
            print(f"No Sentinel-2 item found for {year}-{month:02d}")
            continue
        result = compute_metrics(feature)
        if not result:
            print(f"Skipping {year}-{month:02d} due to missing bands")
            continue
        metrics, image_date = result
        print(f"{year}-{month:02d}: NDVI={metrics['ndvi']:.4f} NDMI={metrics['ndmi']:.4f} BSI={metrics['bsi']:.4f} from {image_date}")
        year_key = str(year)
        if year_key not in historical:
            historical[year_key] = {
                "months": [],
                "ndvi": [],
                "ndmi": [],
                "bsi": [],
                "image_dates": []
            }
        historical[year_key]["months"].append(start.strftime("%b"))
        historical[year_key]["ndvi"].append(round(metrics["ndvi"], 4))
        historical[year_key]["ndmi"].append(round(metrics["ndmi"], 4))
        historical[year_key]["bsi"].append(round(metrics["bsi"], 4))
        historical[year_key]["image_dates"].append(image_date)
    return historical


def main():
    data = backfill()
    wrapped = {"tailings_dam": data}
    os.makedirs("data", exist_ok=True)
    with open("data/historical_monthly.json", "w") as f:
        json.dump(wrapped, f, indent=2)
    print("Saved data/historical_monthly.json")


if __name__ == "__main__":
    main()
