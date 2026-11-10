# 📊 DocMetric — Document Similarity & Dimensionality Analyzer

**Turn documents into data. Discover similarities through mathematics.**

DocMetric is an interactive web application that uses Linear Algebra and Vector Calculus concepts to analyze text documents, calculate their similarity, and visualize them in a lower-dimensional space using Principal Component Analysis (PCA).

The project demonstrates how mathematical concepts can be connected to build a complete document analysis pipeline.

 **Live Demo:** [Try DocMetric](https://doc-metric.streamlit.app)

---

## ✨ Features

- **Multiple Document Inputs:** Upload multiple `.txt` files or enter your own documents manually.
- **Text Preprocessing:** Clean, tokenize and process text, with an option to remove common stop words.
- **Feature Matrix:** Convert documents into numerical representations using word frequencies.
- **Matrix Rank Analysis:** Calculate the rank of the document feature matrix.
- **Document Vectors:** Represent each document as a numerical vector.
- **Cosine Similarity:** Calculate similarity between documents using vector norms and inner products.
- **Similarity Heatmap:** Visualize relationships between documents.
- **Principal Component Analysis (PCA):** Reduce high-dimensional document vectors into two dimensions.
- **Interactive Visualizations:** Explore mathematical results through interactive charts.
- **PDF Report Generation:** Export analysis results, tables, charts and interpretations.
- **Pixel Cat Assistant:** An interactive assistant that helps explain the computed results.
- **Custom UI:** A pixel-art inspired interface with light and dark modes.

## 🧮 Mathematical Pipeline

The project connects multiple mathematical concepts through a sequential pipeline, where the output of one stage becomes the input for the next.

**Documents → Feature Matrix → Rank → Document Vectors → Norm & Inner Product → Similarity Matrix → PCA → 2D Projection**

| Stage | Mathematical Concept | Purpose |
|---|---|---|
| 1 | Feature Representation | Convert text into numerical vectors |
| 2 | Matrix Rank | Determine the independent dimensions of the feature matrix |
| 3 | Vector Representation | Represent each document as a vector |
| 4 | Norm & Inner Product | Measure vector magnitude and relationships |
| 5 | Cosine Similarity | Calculate similarity between documents |
| 6 | Covariance Matrix | Understand relationships between features |
| 7 | Eigenvalues & Eigenvectors | Identify principal directions |
| 8 | PCA Projection | Represent documents in 2D space |

## 🛠️ Tech Stack

- **Language:** Python
- **Frontend & Application:** Streamlit
- **Numerical Computing:** NumPy
- **Data Handling:** Pandas
- **Visualizations:** Plotly
- **PDF Generation:** ReportLab
- **Version Control:** Git & GitHub

## 📁 Project Structure

```text
document-similarity-checker/
│
├── .streamlit/
│   └── config.toml
│
├── assets/
│   ├── background.jpg
│   ├── heart.png
│   ├── mascot.png
│   └── shark.png
│
├── results/
│   ├── documents.py
│   ├── pca.py
│   ├── rank.py
│   ├── similarity.py
│   └── text_processor.py
│
├── ui/
│   ├── __init__.py
│   ├── assistant.py
│   ├── panel.py
│   ├── pdf_report.py
│   ├── pixel_cat.py
│   └── theme.py
│
├── app.py
├── requirements.txt
├── verify.py
└── README.md
```

## How to Use

## 📖 How to Use

1. Open DocMetric and upload `.txt` files or enter documents manually.
2. Select preprocessing options and start the analysis.
3. Explore the feature matrix, matrix rank and document vectors.
4. Analyze document similarities using the heatmap.
5. Visualize document relationships through PCA.
6. Download the generated PDF report.

## Important Notes

- The application currently supports plain-text `.txt` document uploads.
- Each uploaded text file is treated as one document.
- Manually entered documents should be separated by new lines.
- At least two usable documents and two distinct words are required for analysis.
- Large document collections are subject to computational and visualization limits.

## Project Objective

The primary objective of this project is to demonstrate the practical application of mathematical concepts in computer science.

It connects Linear Algebra concepts such as matrices, rank, vector operations, inner products, eigenvalues, eigenvectors and PCA to a real-world problem: understanding relationships between text documents.

Rather than treating mathematics as isolated formulas, DocMetric demonstrates how multiple mathematical operations work together in a complete computational system.

---

