
# PaySim Fraud Transactions
<p>
    <a href="LICENSE" target="_blank"><img src="https://img.shields.io/badge/license-MIT-green" alt="Package License" /></a>
    <a href="https://python.org/" target="_blank"><img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" alt="Flutter" /></a>
  </p>

A data mining project that analyzes the PaySim mobile money transaction dataset to identify fraudulent transaction patterns through data preprocessing, clustering, association rule mining, and anomaly detection. This project was developed to fulfill the final project requirements for the Data Mining course.

## Features

- **Phase 1: Data Understanding and Data Preprocessing**
  - Data cleaning and validation
  - Feature engineering
  - Data transformation
  - One-Hot Encoding
  - Log Transformation
  - RobustScaler normalization

- **Phase 2: Segmentation via Clustering**  
  Transaction segmentation using:
  - K-Means
  - HDBSCAN
  - BIRCH
  - BIRCH + HDBSCAN

  Evaluation using:
  - Silhouette Score
  - Davies-Bouldin Index
  - Calinski-Harabasz Index

- **Phase 3: Association Rule Mining**  
  Discover hidden relationships between transaction attributes using:
  - Apriori Algorithm
  - Frequent Itemsets
  - Association Rules
  - Fraud-specific Rules

- **Phase 4: Anomaly and Outlier Detection**  
  Risk analysis using multiple methods:
  - IQR
  - Z-Score
  - Isolation Forest
  - BIRCH + HDBSCAN Outliers

- **Phase 5: Visualization and Knowledge Presentation**  
  Visualize:
  - Fraud distribution
  - Transaction segments
  - Risk categories
  - Fraud indicators
  - Business insights

## Dataset
Dataset : PaySim Fraud Transactions  
Records : 6.300.000+  
Feature : 11  
Link : https://www.kaggle.com/datasets/ealaxi/paysim1

## Tech Stack
| Category | Technology |
|----------|------------|
| Programming Language | Python |
| Environment | Conda |
| Pipeline | Prefect |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn |
| Clustering | K-Means, HDBSCAN, BIRCH |
| Association Rules | Mlxtend (Apriori) |
| Visualization | Matplotlib, Seaborn, Plotly |
| Dashboard | Python Dash |
| Notebook | Jupyter Notebook |

## Run Locally
Clone the project

```bash
git clone https://github.com/darrentimotius/data-mining
```

Go to the project directory

```bash
cd data-mining
```

Create a virtual environment (optional):

```bash
conda create -n data-mining python=3.10
```

Activate the environment:

```bash
conda activate data-mining
```


Install dependencies

```bash
pip install -r requirement.txt
```

Start the server

```bash
prefect server start
```

Start the dashboard

```bash
cd phase_5 && python app.py
```

## License

PaySim Fraud Transactions is licensed under [MIT](LICENSE)

## Contributing

Contributions are always welcome!


Feel free to fork this repository, create a new branch, and submit a pull request.

## Authors

| Name                         | GitHub Username |
|------------------------------|-----------------|
| Darren Timotius Raphael      | [@darrentimotius](https://github.com/darrentimotius) |
| Fance Satria Nusantara           | [@fancesatria](https://github.com/fancesatria) |
| Helen Febriyanto       | [@helenfebriyanto](https://github.com/helenfebriyanto) |
| Syarifana Amalia Putri  | [@syarifanaamalia](https://github.com/syarifanaamalia) |
| Adriel Bernhard Tanuhariono | [@AdrielBernhardT](https://github.com/AdrielBernhardT) |
