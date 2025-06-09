# Baogang Environmental Impact Dashboard

This is a lightweight demo dashboard that uses **Google Earth Engine (GEE)** data to visualize environmental changes around the **Baogang Rare Earth Processing Plant** in Inner Mongolia, China. The dashboard includes reference plots from a nearby, comparatively undisturbed area for baseline comparison.


Demo link: [Baogang Monitor](https://andjames.github.io/baogang-monitor/)

## 🌍 Features

- **Real Earth Engine Data**  
  Pulls NDVI, NDMI, BSI, and other spectral indices directly from GEE for both the Baogang area and a reference site.

- **Automated Updates via GitHub Actions**  
  The dataset and charts are automatically refreshed on a regular schedule (e.g. weekly or monthly) using GitHub Actions.

- **Publicly Accessible**  
  Hosted as a static site (e.g. via GitHub Pages or another frontend host) for open access and sharing.

- **Interactive Map + Charts**  
  Uses **Leaflet** for geographic overlays and **Chart.js** for dynamic visualizations.

## 📊 Why Baogang?

Baogang is home to one of the world’s largest rare earth processing facilities, and its environmental footprint is widely cited in discussions around green energy and sustainability. This demo explores the landscape changes using satellite-derived indices.

## 🛠️ Stack

- [Google Earth Engine](https://earthengine.google.com/) – for data access and processing  
- [GitHub Actions](https://github.com/features/actions) – for automated data updates  
- [Leaflet](https://leafletjs.com/) – for interactive mapping  
- [Chart.js](https://www.chartjs.org/) – for plotting time-series trends  
- HTML, CSS, JavaScript – frontend

## 📁 Project Structure

/
├── data/               # JSON or CSV exports from Earth Engine
├── scripts/            # GEE export scripts and GitHub Actions
├── public/             # HTML/CSS/JS files for the dashboard
│   ├── index.html
├── .github/workflows/  # CI scripts for automated updates
└── README.md #you're here!

## 🔄 How It Works
GEE scripts export environmental index data for Baogang and a reference region.

GitHub Actions runs on a schedule, fetching and updating the dataset.

The dashboard loads the latest dataset and displays it via Leaflet and Chart.js.

## 🚧 Future Ideas
Add more historical imagery comparisons

Expand to include other sites with known environmental degradation

Enable user-defined AOI comparisons (interactive drawing + fetch)

## 📬 Contact
For questions, collaboration, or feedback, feel free to open an issue or reach out.

This project is for demonstration purposes only and does not represent any official environmental assessment.
