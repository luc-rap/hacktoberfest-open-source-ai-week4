# hacktoberfest-open-source-ai-week4

## The House That Remembers

### Run the Streamlit app

Install Ollama and download the model before starting the app:

```powershell
ollama pull gemma4:e4b
```

Make sure the Ollama service is running. Then, from the repository root,
create and activate a virtual environment and install the project dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the app with:

```powershell
python -m streamlit run .\the-house-that-remembers\app.py
```

Streamlit prints a local URL in the terminal; open it in your browser to view
the app.
