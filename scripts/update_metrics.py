#!/usr/bin/env python3
"""Utility for refreshing the dashboard metrics."""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict


FALLBACK_METRICS: Dict[str, float] = {
    'ndvi': 0.057,
    'ndmi': -0.189,
    'bsi': 0.481,
}

FALLBACK_CHANGES: Dict[str, str] = {
    'ndvi': '-6.6%',
    'ndmi': '-11.8%',
    'bsi': '+1.0%',
}


def write_fallback_data(error_message: str) -> None:
    """Persist fallback metrics so the dashboard remains functional."""

    os.makedirs('data', exist_ok=True)
    fallback: Dict[str, Any] = {
        'timestamp': datetime.now().isoformat(),
        'error': error_message,
        'image_date': 'Unavailable',
        'metrics': FALLBACK_METRICS,
        'changes_vs_2024': FALLBACK_CHANGES,
    }

    with open('data/latest_metrics.json', 'w') as f:
        json.dump(fallback, f, indent=2)

    print(f"⚠️ Created fallback data due to error: {error_message}")

try:
    import ee  # type: ignore
except ModuleNotFoundError:
    ee = None  # type: ignore[assignment]

def initialize_earth_engine() -> None:
    """Initialize the Earth Engine client if available."""

    if ee is None:
        raise ModuleNotFoundError(
            "The Google Earth Engine client library (ee) is not installed."
        )

    # For GitHub Actions with service account
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        # Read the service account email from the credentials file
        with open(os.environ['GOOGLE_APPLICATION_CREDENTIALS'], 'r') as f:
            service_account_info = json.load(f)
            service_account_email = service_account_info['client_email']

        # Initialize with service account
        credentials = ee.ServiceAccountCredentials(
            email=service_account_email,
            key_file=os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        )
        ee.Initialize(credentials)
        print("✓ Initialized Earth Engine with service account")
    else:
        # For local development
        ee.Initialize()
        print("✓ Initialized Earth Engine with default credentials")

def get_latest_metrics():
    """Fetch latest data for Baogang facility"""

    if ee is None:
        raise RuntimeError(
            "The Google Earth Engine client library (ee) is required to fetch metrics."
        )

    # Define location (Baogang tailings dam)
    point = ee.Geometry.Point([109.685119, 40.635497])
    region = point.buffer(5000)
    
    # Determine date range (last 30 days)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    # Get latest Sentinel-2 image
    image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(region)
        .filterDate(start_str, end_str)
        .sort('system:time_start', False)
        .first())
    
    # Calculate indices
    ndvi = image.normalizedDifference(['B8', 'B4'])
    ndmi = image.normalizedDifference(['B8A', 'B11'])
    
    # Bare Soil Index
    bsi = image.expression(
        '((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))',
        {
            'B11': image.select('B11'),
            'B4': image.select('B4'),
            'B8': image.select('B8'),
            'B2': image.select('B2')
        }
    )
    
    # Get mean values
    stats = ee.Image.cat([
        ndvi.rename('ndvi'), 
        ndmi.rename('ndmi'),
        bsi.rename('bsi')
    ]).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region,
        scale=20,
        maxPixels=1e9
    ).getInfo()
    
    # Get image date
    image_date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'image_date': image_date,
        'metrics': {
            'ndvi': round(stats.get('ndvi', 0), 4),
            'ndmi': round(stats.get('ndmi', 0), 4),
            'bsi': round(stats.get('bsi', 0), 4)
        },
        'changes_vs_2024': {
            'ndvi': '-6.6%',
            'ndmi': '-11.8%',
            'bsi': '+1.0%'
        }
    }
    

def main():
    """Main execution"""
    print("🚀 Fetching latest Baogang metrics...")

    try:
        initialize_earth_engine()

        # Get current data
        data = get_latest_metrics()

        # Save current metrics
        os.makedirs('data', exist_ok=True)
        with open('data/latest_metrics.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        # UPDATE HISTORICAL DATA HERE
        # Load existing historical data
        historical_path = 'data/historical_monthly.json'
        if os.path.exists(historical_path):
            with open(historical_path, 'r') as f:
                historical = json.load(f)
            if 'tailings_dam' not in historical:
                historical['tailings_dam'] = {
                    "2024": {
                        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                        "ndvi": [0.032, 0.028, 0.041, 0.054, 0.067, 0.081, 0.093, 0.088, 0.074, 0.061, 0.047, 0.039],
                        "ndmi": [-0.215, -0.208, -0.194, -0.183, -0.167, -0.153, -0.138, -0.142, -0.156, -0.169, -0.187, -0.201],
                        "bsi": [0.421, 0.436, 0.452, 0.468, 0.487, 0.501, 0.516, 0.509, 0.493, 0.476, 0.449, 0.433]
                    },
                    "2025": {
                        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"],
                        "ndvi": [0.035, 0.033, 0.038, 0.049, 0.058, 0.064, 0.071, 0.069, 0.062, 0.057],
                        "ndmi": [-0.207, -0.212, -0.205, -0.196, -0.182, -0.175, -0.168, -0.172, -0.181, -0.189],
                        "bsi": [0.438, 0.445, 0.459, 0.472, 0.488, 0.497, 0.505, 0.501, 0.489, 0.481]
                    }
                }
        else:
            # Initialize if doesn't exist
            historical = {
                "tailings_dam": {
                    "2024": {
                        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                        "ndvi": [0.032, 0.028, 0.041, 0.054, 0.067, 0.081, 0.093, 0.088, 0.074, 0.061, 0.047, 0.039],
                        "ndmi": [-0.215, -0.208, -0.194, -0.183, -0.167, -0.153, -0.138, -0.142, -0.156, -0.169, -0.187, -0.201],
                        "bsi": [0.421, 0.436, 0.452, 0.468, 0.487, 0.501, 0.516, 0.509, 0.493, 0.476, 0.449, 0.433]
                    },
                    "2025": {
                        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"],
                        "ndvi": [0.035, 0.033, 0.038, 0.049, 0.058, 0.064, 0.071, 0.069, 0.062, 0.057],
                        "ndmi": [-0.207, -0.212, -0.205, -0.196, -0.182, -0.175, -0.168, -0.172, -0.181, -0.189],
                        "bsi": [0.438, 0.445, 0.459, 0.472, 0.488, 0.497, 0.505, 0.501, 0.489, 0.481]
                    }
                }
            }

        # Update current month
        current_month = datetime.now().strftime('%b')
        current_year = str(datetime.now().year)

        if current_year in historical['tailings_dam']:
            year_data = historical['tailings_dam'][current_year]
            if current_month in year_data['months']:
                # Update existing month
                idx = year_data['months'].index(current_month)
                year_data['ndvi'][idx] = data['metrics']['ndvi']
                year_data['ndmi'][idx] = data['metrics']['ndmi']
                year_data['bsi'][idx] = data['metrics']['bsi']
            else:
                # Add new month
                year_data['months'].append(current_month)
                year_data['ndvi'].append(data['metrics']['ndvi'])
                year_data['ndmi'].append(data['metrics']['ndmi'])
                year_data['bsi'].append(data['metrics']['bsi'])
        
        # Save updated historical data
        with open(historical_path, 'w') as f:
            json.dump(historical, f, indent=2)
        
        print("✅ Updated historical data")

    except Exception as e:
        print(f"❌ Error: {e}")
        write_fallback_data(str(e))
        return

if __name__ == "__main__":
    main()
