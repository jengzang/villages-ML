# Documentation Index

This directory contains all project documentation organized by category.

## 📁 Directory Structure

```
docs/
├── README.md                    # This file - documentation index
├── frontend/                    # Frontend & API documentation
├── phases/                      # Phase implementation summaries
├── guides/                      # Implementation guides
├── reports/                     # Analysis & status reports
└── analysis_results_data.json  # Raw analysis data
```

---

## 🚀 Quick Start

**New to this project?** Start here:

1. **Project Overview**: `../README.md` (root directory)
2. **Project Instructions**: `../CLAUDE.md` (development guidelines)
3. **Preprocessing Guide**: `reports/PREPROCESSING_QUICK_START.md`
4. **API Quick Start**: `frontend/API_QUICK_REFERENCE.md`

---

## 📚 Documentation by Category

### Frontend & API Documentation (`frontend/`)

Complete API documentation for the FastAPI backend:

- **`API_REFERENCE.md`** - Complete API endpoint reference (30+ endpoints)
- **`API_QUICK_REFERENCE.md`** - Quick reference guide (one-page)
- **`FRONTEND_INTEGRATION_GUIDE.md`** - Vue 3 integration guide with examples
- **`API_DEPLOYMENT_GUIDE.md`** - Deployment instructions (Docker, Nginx)
- **`API_FINAL_GUIDE.md`** - Comprehensive API guide

**Use Case**: Building a frontend application or deploying the API

---

### Phase Summaries (`phases/`)

Detailed implementation summaries for each analysis phase:

- **`PHASE_0_PREPROCESSING_SUMMARY.md`** - Data preprocessing (prefix cleaning)
- **`PHASE_01_IMPLEMENTATION_SUMMARY.md`** - Character embeddings (Word2Vec)
- **`PHASE_02_IMPLEMENTATION_SUMMARY.md`** - LLM semantic labeling
- **`PHASE_03_IMPLEMENTATION_SUMMARY.md`** - Semantic co-occurrence analysis
- **`PHASE_11_SUMMARY.md`** - Query policy framework
- **`PHASE_12_SUMMARY.md`** - N-gram analysis
- **`PHASE_13_SUMMARY.md`** - Spatial hotspots
- **`PHASE_14_SUMMARY.md`** - Semantic composition

**Use Case**: Understanding how each analysis phase was implemented

---

### Implementation Guides (`guides/`)

Step-by-step guides for specific features:

- **`CHAR_EMBEDDINGS_GUIDE.md`** - Character embedding generation
- **`LLM_LABELING_GUIDE.md`** - LLM-assisted semantic labeling
- **`LLM_SETUP_GUIDE.md`** - LLM API setup instructions
- **`PHASE_03_SEMANTIC_COOCCURRENCE_GUIDE.md`** - Semantic co-occurrence
- **`SPATIAL_ANALYSIS_GUIDE.md`** - Spatial analysis (k-NN, DBSCAN, KDE)
- **`SPATIAL_TENDENCY_INTEGRATION_GUIDE.md`** - Spatial-tendency integration
- **`TENDENCY_SIGNIFICANCE_GUIDE.md`** - Statistical significance testing
- **`ZSCORE_NORMALIZATION_GUIDE.md`** - Z-score normalization

**Use Case**: Implementing or modifying specific analysis features

---

### Analysis & Status Reports (`reports/`)

#### Analysis Results

- **`COMPREHENSIVE_ANALYSIS_REPORT.md`** - Complete analysis report (8000 words, Chinese)
- **`ANALYSIS_RESULTS_SHOWCASE.md`** - Analysis results showcase (English)
- **`分析结果展示_中文版.md`** - Analysis results showcase (Chinese)
- **`COVERAGE_ANALYSIS_REPORT.md`** - Data coverage analysis

#### Database & Implementation Status

- **`PROJECT_STATUS.md`** - Overall project status
- **`DATABASE_STATUS_REPORT.md`** - Database verification (45 tables)
- **`DATABASE_VERIFICATION_SUMMARY.md`** - Data quality metrics
- **`API_IMPLEMENTATION_SUMMARY.md`** - API implementation status
- **`API_AUDIT_ACTUAL_STATUS.md`** - API audit report
- **`FASTAPI_PROJECT_STRUCTURE.md`** - FastAPI project structure

#### Recent Updates (2026-02-21)

- **`API_IMPLEMENTATION_UPDATE_20260221.md`** - Latest API updates
- **`IMPLEMENTATION_COMPLETE_SPATIAL_INTEGRATION.md`** - Spatial integration completion
- **`SPATIAL_TENDENCY_INTEGRATION_API.md`** - Spatial-tendency API documentation
- **`SPATIAL_TENDENCY_INTEGRATION_FIX.md`** - Performance fix details
- **`NEW_ENDPOINTS_QUICK_REFERENCE.md`** - New endpoints reference

#### Preprocessing Reports

- **`PREPROCESSING_QUICK_START.md`** - Preprocessing quick start
- **`PREFIX_CLEANING_AUDIT_REPORT.md`** - Prefix cleaning audit (5,782 prefixes)

**Use Case**: Understanding project status, data quality, and recent changes

---

## 🔍 Finding Documentation

### By Task

| Task | Documentation |
|------|---------------|
| **Start using the API** | `frontend/API_QUICK_REFERENCE.md` |
| **Build a frontend** | `frontend/FRONTEND_INTEGRATION_GUIDE.md` |
| **Deploy the API** | `frontend/API_DEPLOYMENT_GUIDE.md` |
| **Understand analysis results** | `reports/COMPREHENSIVE_ANALYSIS_REPORT.md` |
| **Check project status** | `reports/PROJECT_STATUS.md` |
| **Implement new features** | `guides/` (relevant guide) |
| **Understand a phase** | `phases/` (relevant phase summary) |

### By Topic

| Topic | Documentation |
|-------|---------------|
| **Character Analysis** | `phases/PHASE_01_IMPLEMENTATION_SUMMARY.md` |
| **Semantic Analysis** | `phases/PHASE_02_IMPLEMENTATION_SUMMARY.md` |
| **Spatial Analysis** | `guides/SPATIAL_ANALYSIS_GUIDE.md` |
| **N-gram Analysis** | `phases/PHASE_12_SUMMARY.md` |
| **API Endpoints** | `frontend/API_REFERENCE.md` |
| **Database Schema** | `reports/DATABASE_STATUS_REPORT.md` |
| **Data Preprocessing** | `reports/PREPROCESSING_QUICK_START.md` |

---

## 📊 Project Statistics

- **Total Villages**: 285,860 (Guangdong Province)
- **Database Tables**: 45 (all populated)
- **API Endpoints**: 30-34 endpoints (~90% coverage)
- **Analysis Phases**: 15 phases (all completed)
- **Documentation Files**: 40+ markdown files
- **Code Lines**: ~31,000 lines (60+ modules)

---

## 🔗 External Resources

- **GitHub Repository**: [villages-ML](https://github.com/jengzang/villages-ML)
- **API Documentation**: http://localhost:8000/docs (when server is running)
- **Project Root**: `../README.md`
- **Development Guide**: `../CLAUDE.md`

---

## 📝 Documentation Standards

All documentation follows these standards:

- **Format**: Markdown (.md)
- **Language**: English (with Chinese translations where appropriate)
- **Structure**: Clear headings, table of contents, code examples
- **Updates**: Documentation is updated with each major feature addition
- **Location**: All docs in `docs/` directory (organized by category)

---

## 🆕 Recent Updates

**2026-02-21**: Major documentation reorganization
- Created organized directory structure (frontend/, phases/, guides/, reports/)
- Added comprehensive documentation index (this file)
- Moved 40+ documentation files to appropriate categories
- Updated CLAUDE.md with new documentation structure

**2026-02-21**: Spatial-Tendency Integration API
- Added 4 new API endpoints
- Complete API documentation
- Performance optimization (7.49s execution time)
- 643 integration records created

---

## 💡 Contributing

When adding new documentation:

1. **Choose the right directory**:
   - `frontend/` - API and frontend-related docs
   - `phases/` - Phase implementation summaries
   - `guides/` - Step-by-step implementation guides
   - `reports/` - Analysis results and status reports

2. **Follow naming conventions**:
   - Phase summaries: `PHASE_XX_SUMMARY.md`
   - Guides: `FEATURE_NAME_GUIDE.md`
   - Reports: `REPORT_TYPE_REPORT.md`

3. **Update this index** when adding new documentation

4. **Keep documentation up-to-date** with code changes

---

**Last Updated**: 2026-02-21
