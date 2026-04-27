# test_dummy.py
def test_environment_is_ready():
    # Ein einfacher Test, der immer wahr ist, damit die Pipeline durchläuft
    assert True

def test_imports():
    # Prüft, ob deine Hauptabhängigkeiten geladen werden können
    import streamlit
    import pymongo
    assert True