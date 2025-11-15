# dIAGNOSIS

Desktop application prototype for clinical data analysis. Version V1 provides a PySide6-based user interface with stubbed analytical logic and extensible architecture prepared for future FastAPI integration.

## Requirements

- Python 3.11+
- [PySide6](https://doc.qt.io/qtforpython/) (see `requirements.txt`)

## Project structure

```
project_root/
├── app.py
├── config.py
├── main.py
├── core/
├── services/
├── ui/
├── backend/
├── resources/
└── utils/
```

Refer to the in-code docstrings for current capabilities and upcoming extension points.

## Running the application

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
pip install -r requirements.txt
python main.py
```

> **Важно.** На текущем этапе проект не требует отдельной компиляции или сборки. Запускайте `main.py` напрямую (например, через конфигурацию Run/Debug в PyCharm), чтобы работать с приложением в режиме отладки.

The application opens the main window with a patient form and results view. Press the **Проанализировать** button to trigger the stub analysis executed in a background thread.

## Future development

- Implement FastAPI backend and HTTP analysis service.
- Expand patient data entry forms and validation.
- Integrate real mathematical/ML models.
- Provide persistent settings storage and local database support.
