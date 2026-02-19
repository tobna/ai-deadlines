def update():
    """Entry point for the console script.
    Importing ``aideadlines.update_data`` triggers the data‑update pipeline,
    because the module executes its logic on import.
    """
    import importlib
    importlib.import_module('aideadlines.update_data')
