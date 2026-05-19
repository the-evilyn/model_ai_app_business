# Google Trends CSV Files

This folder is used for optional Google Trends exports.

Google Trends does not provide a simple official free API for direct model training.
For the MVP, export a CSV manually:

1. Open https://trends.google.com
2. Search a keyword, for example `immobilier` or `business validation`
3. Select country and period
4. Download the interest-over-time chart as CSV
5. Save it here, for example `data/google_trends/immobilier_morocco.csv`

The collector can read this CSV and convert it into `search_trend_score`.
