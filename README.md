# Student Performance Analysis System

An Institutional Academic Intelligence Platform developed with **Python**, **Pandas**, **Streamlit**, **SQLite**, **Plotly**, and **Scikit-Learn**.

---

## 1. Project Overview

The Student Performance Analysis System is a comprehensive, data-driven academic intelligence platform engineered to manage, monitor, analyze, and forecast student educational outcomes. It addresses four foundational institutional questions:

1. **What is happening?** Executive dashboards, cohort KPIs, and 3D spatial performance projections.
2. **Why is it happening?** Subject-wise difficulty analysis, attendance compliance correlations, and multi-examination audits.
3. **What might happen next?** Supervised Machine Learning regression (Linear, Decision Tree, Random Forest) and What-If intervention simulators.
4. **What should be done?** Rule-based personalized remedial recommendations and academic risk categorization (Low, Medium, High).

---

## 2. System Architecture & Modules

The platform is organized into 10 dedicated functional modules:

| # | Module | Path | Description |
|---|---|---|---|
| 1 | **Executive Dashboard** | `pages/1_Dashboard.py` | Institutional KPIs, 3D spatial performance projection, cohort leaders, and macro distributions. |
| 2 | **Student Management System** | `pages/2_Student_Management.py` | Complete CRUD: enrollment, directory search, profile editing, and mark entry. |
| 3 | **Academic Performance Analysis** | `pages/3_Performance_Analysis.py` | Grade calculations, ranking, passing thresholds, and Pearson correlation matrices. |
| 4 | **Subject Diagnostics** | `pages/4_Subject_Analysis.py` | Course health diagnostics, 3D subject landscape, and score extremes. |
| 5 | **Reports & Data Export** | `pages/5_Reports.py` | Formatted PDF dossiers via ReportLab, CSV downloads, and multi-sheet Excel exports. |
| 6 | **Predictive Analytics & ML** | `pages/6_Predictive_Analytics.py` | Linear Regression, Decision Trees, Random Forest, holdout evaluation, and What-If simulator. |
| 7 | **Academic Progress Tracking** | `pages/7_Academic_Progress.py` | Longitudinal progression tracking across Internals, Mid-Terms, and Final Examinations. |
| 8 | **Attendance Management System** | `pages/8_Attendance_Management.py` | Daily attendance logging, compliance calculations, and non-compliance alerts (< 75%). |
| 9 | **Personalized Recommendations** | `pages/9_Recommendations.py` | Rule-based remedial strategies, strengths/weaknesses profiling, and risk tiering. |
| 10 | **Data Import & Cleaning Pipeline** | `pages/10_Data_Import.py` | CSV/Excel upload, interactive Pandas data-cleaning operations, and database commits. |

---

## 3. Technology Stack

- **Application Logic**: Python 3.10+
- **Data Engineering**: Pandas, NumPy
- **Database Storage**: SQLite 3 (relational schema with foreign keys and multi-exam support)
- **Machine Learning**: Scikit-Learn (Linear Regression, Decision Tree Regressor, Random Forest Regressor)
- **Frontend & UI**: Streamlit with custom 3D CSS design system
- **Interactive Visualizations**: Plotly Express & Plotly Graph Objects (2D and 3D)
- **Document Generation**: ReportLab (PDF), OpenPyXL (Excel XLSX)

---

## 4. Installation & Setup

### Verified Environment & Tested Dependencies
The application has been verified and tested under Python with the following libraries:
- `streamlit` (v1.64.0)
- `pandas` (v3.0.6)
- `numpy` (v2.5.3)
- `plotly` (v7.1.0)
- `matplotlib` (v3.11.2)
- `reportlab` (v5.1.0)
- `scikit-learn` (v1.9.1)
- `openpyxl` (v3.1.5)

### Installation Steps

1. Clone or navigate to the repository directory:
   ```bash
   cd StudentPerformanceSystem
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the application:
   ```bash
   streamlit run app.py
   ```

---

## 5. Grading Criteria & Business Rules

### Letter Grade Scale
- **A+**: 90% – 100%
- **A**: 80% – 89%
- **B**: 70% – 79%
- **C**: 60% – 69%
- **D**: 50% – 59%
- **F**: Below 50%

### Passing Threshold
- A student attains **Pass** status only if their score in **every subject** meets or exceeds the passing threshold of **40 marks**.

### Attendance Threshold
- Minimum standard compliance threshold is set to **75%**. Students below 75% trigger administrative intervention notices. Unrecorded attendance is strictly excluded from cohort averages.

---

## 6. Running Test Suite

All unit tests run in strictly isolated temporary SQLite databases (`tempfile`) and never modify the production demonstrator database (`data/students.db`).

Execute the automated test suite (21 unit tests across analysis, database, and validation):
```bash
python -m unittest discover -s tests
```

Or run individual test modules:
```bash
python -m unittest tests/test_database.py
python -m unittest tests/test_analysis.py
python -m unittest tests/test_validation.py
```

