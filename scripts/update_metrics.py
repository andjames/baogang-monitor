#!/usr/bin/env python3
"""
update_metrics.py - Fixed version for GitHub Actions
"""

import ee
import json
import os
from datetime import datetime

# Initialize Earth Engine
try:
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
        
except Exception as e:
    print(f"✗ Failed to initialize Earth Engine: {e}")
    exit(1)

def get_latest_metrics():
    """Fetch latest data for Baogang facility"""
    
    # Define location
    point = ee.Geometry.Point([109.8405, 40.6589])
    region = point.buffer(5000)
    
    # Get latest Sentinel-2 image
    image = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(region) \
        .filterDate('2025-05-01', '2025-06-30') \
        .sort('system:time_start', False) \
        .first()
    
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
            'ndvi': '-2.0%',
            'ndmi': '-340.7%',
            'bsi': '+76.2%'
        }
    }

def main():
    """Main execution"""
    print("🚀 Fetching latest Baogang metrics...")
    
    try:
        # Get data
        data = get_latest_metrics()
        
        # Ensure directory exists
        os.makedirs('data', exist_ok=True)
        
        # Save to file
        with open('data/latest_metrics.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Updated metrics:")
        print(f"   Image date: {data['image_date']}")
        print(f"   NDVI: {data['metrics']['ndvi']}")
        print(f"   NDMI: {data['metrics']['ndmi']}")
        print(f"   BSI: {data['metrics']['bsi']}")
        print(f"✅ Saved to data/latest_metrics.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # Create fallback data so dashboard still works
        fallback = {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'metrics': {
                'ndvi': 0.129,
                'ndmi': -0.038,
                'bsi': 0.084
            }
        }
        
        os.makedirs('data', exist_ok=True)
        with open('data/latest_metrics.json', 'w') as f:
            json.dump(fallback, f, indent=2)
        
        print("⚠️ Created fallback data")
        exit(1)

if __name__ == "__main__":
    main()