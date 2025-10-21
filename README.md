# Stemwijzer Analysis

An exploratory analysis of Dutch political party positions based on data from [Stemwijzer](https://www.stemwijzer.nl/), the official voting advice website for the 2025 parliamentary elections.

This project scrapes party positions on 30 political issues and uses dimensionality reduction techniques (t-SNE and PCA) to visualize ideological patterns and clusters. 

## What's Inside

- **`scraper.py`**: Python script that scrapes party positions and explanations from the Stemwijzer website
- **`stemwijzer.ipynb`**: Jupyter notebook with data exploration, visualizations, and dimensionality reduction analysis
- **`tweedekamer2025.json`**: Scraped data (party positions on 30 issues)
- **`parties.png`**: Party logos image used for visualizations
- **`environment.yml`**: Conda environment specification

## Getting Started

### Prerequisites

* [Anaconda](https://www.anaconda.com/distribution/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) must be installed on your machine.
* Basic knowledge of Python, Jupyter notebooks, and conda environments.

### Installation

1. Clone or download this repository:
```bash
git clone https://github.com/afvanwoudenberg/stemwijzer.git
```

2. Navigate into the project folder:
```bash
cd stemwijzer
```

3. Create the conda environment:
```bash
conda env create -f environment.yml
```

4. Activate the environment:
```bash
conda activate stemwijzer
```

### Running the Scraper

To fetch fresh data from Stemwijzer:

```bash
python scraper.py
```

This will create/update `tweedekamer2025.json` with the latest party positions.

### Exploring the Notebook

Start Jupyter:
```bash
jupyter notebook
```

Open `stemwijzer.ipynb` and run the cells. The notebook walks through:
- Loading and reshaping the scraped data
- Visualizing party agreement/disagreement patterns
- Word clouds of party explanations
- Dimensionality reduction (t-SNE, PCA)
- Interpretation of ideological axes

## Author

Aswin van Woudenberg ([afvanwoudenberg](https://github.com/afvanwoudenberg))

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

