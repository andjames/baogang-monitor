import ee
import json
from datetime import datetime

# Initialize Earth Engine
ee.Initialize()

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
    
    # Get mean values
    stats = ee.Image.cat([ndvi, ndmi]).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region,
        scale=20,
        maxPixels=1e9
    ).getInfo()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'ndvi': round(stats.get('nd', 0), 4),
        'ndmi': round(stats.get('nd_1', 0), 4),
        'last_image': ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
    }

# Get data and save
data = get_latest_metrics()

# Save to file
with open('data/latest_metrics.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"✅ Updated metrics: NDVI={data['ndvi']}, NDMI={data['ndmi']}")