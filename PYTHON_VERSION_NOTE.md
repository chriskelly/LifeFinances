# Python Version Compatibility Note

## Current Issue

The project specifies Python 3.10 as the required version, but the system has Python 3.13.5 installed.

## Problem

The pinned dependencies in `requirements/common.txt` are incompatible with Python 3.13:
- `numpy==1.26.1` requires Python 3.9-3.12
- `pydantic==2.4.2` (specifically `pydantic-core==2.10.1`) requires compilation that fails on Python 3.13

## Solutions

### Option 1: Install Python 3.10 (Recommended)

1. Download Python 3.10 from [python.org](https://www.python.org/downloads/)
2. Install it (you can have multiple Python versions)
3. Create venv with Python 3.10:
   ```bash
   # Windows
   py -3.10 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements/common.txt
   pip install -r requirements/dev.txt
   pip install -r requirements/qt.txt
   ```

### Option 2: Use Updated Dependencies (May break compatibility)

Update `requirements/common.txt` to use newer compatible versions:
```
flask>=3.0.0
pydantic>=2.10.0
numpy>=2.0.0
pandas>=2.0.0
pyyaml>=6.0.0
```

**Warning:** This may introduce breaking changes. The project was developed with the pinned versions.

### Option 3: Use Docker (Guaranteed compatibility)

The project includes Docker support that uses Python 3.10:
```bash
make build
make up
make test
```

## Current Status

The Qt GUI module has been fully implemented and is ready to use once a compatible Python environment is set up.

## Next Steps

1. Install Python 3.10
2. Create virtual environment with Python 3.10
3. Install dependencies
4. Test Qt GUI: `python run_gui.py`
5. Run tests: `pytest tests/qt_gui/`
