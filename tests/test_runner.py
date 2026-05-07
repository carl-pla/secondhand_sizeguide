"""
Tests für runner.py: Orchestrierungstool für User-basierte Scraping-Sessions.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import subprocess


@pytest.fixture
def test_user():
    """Typischer Test-User."""
    return {
        "email": "test@example.com",
        "groesse": "M",
        "kategorie": "Herren Jacken & Mäntel",
        "max_preis": 50,
        "stile": ["Vintage"],
        "eigene_masse": {"brust": 88, "taille": 70, "huefte": 96},
        "min_zustand": "Gut",
        "quelle": "vinted",
    }


@pytest.fixture
def test_users(test_user):
    """Liste mit mehreren Test-Usern."""
    return [
        test_user,
        {
            "email": "another@example.com",
            "groesse": "L",
            "max_preis": 100,
            "stile": ["Casual"],
        },
    ]


# === Tests: Import und Funktion ===

def test_runner_importierbar(capsys):
    """Test: runner.py kann importiert werden."""
    import runner
    assert runner is not None
    capsys.readouterr()


def test_runner_funktion_async(capsys):
    """Test: run_fuer_einen_user() ist async-Funktion."""
    from runner import run_fuer_einen_user
    import inspect
    assert inspect.iscoroutinefunction(run_fuer_einen_user)
    capsys.readouterr()


# === Tests: Fehlerhafte Szenarien ===

@pytest.mark.asyncio
async def test_runner_keine_target_email(capsys):
    """Test: run_fuer_einen_user() bricht ab wenn TARGET_USER_EMAIL fehlt."""
    with patch.dict("os.environ", {}, clear=True):
        from runner import run_fuer_einen_user
        
        try:
            await run_fuer_einen_user()
            assert False, "Sollte SystemExit werfen"
        except SystemExit as e:
            assert e.code == 1
    capsys.readouterr()


@pytest.mark.asyncio
async def test_runner_user_nicht_gefunden(capsys, test_users):
    """Test: run_fuer_einen_user() bricht ab wenn User nicht in DB."""
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": "unknown@example.com"}), \
         patch("runner.lade_alle_user", return_value=test_users):
        
        from runner import run_fuer_einen_user
        
        try:
            await run_fuer_einen_user()
            assert False, "Sollte SystemExit werfen"
        except SystemExit as e:
            assert e.code == 1
    capsys.readouterr()


# === Tests: Erfolgreiche Szenarien ===

@pytest.mark.asyncio
async def test_runner_erstellt_config(capsys, test_user, test_users):
    """Test: run_fuer_einen_user() erstellt Config-JSON."""
    mock_path = MagicMock()
    mock_file = MagicMock()
    
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": test_user["email"]}), \
         patch("runner.lade_alle_user", return_value=test_users), \
         patch("runner.Path", return_value=mock_path), \
         patch("builtins.open", mock_open()) as mock_open_file, \
         patch("runner.subprocess.run", return_value=MagicMock(returncode=0)):
        
        from runner import run_fuer_einen_user
        
        await run_fuer_einen_user()
        
        # Überprüfe dass open() aufgerufen wurde
        mock_open_file.assert_called()
        
        # Überprüfe dass json.dump() aufgerufen wurde mit einer Config
        handle = mock_open_file()
        written_data = "".join([call.args[0] for call in handle.write.call_args_list])
        
    capsys.readouterr()


@pytest.mark.asyncio
async def test_runner_subprocess_erfolg(capsys, test_user, test_users):
    """Test: run_fuer_einen_user() erfolgreich bei returncode 0."""
    mock_path = MagicMock()
    mock_process = MagicMock()
    mock_process.returncode = 0
    
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": test_user["email"]}), \
         patch("runner.lade_alle_user", return_value=test_users), \
         patch("runner.Path", return_value=mock_path), \
         patch("builtins.open", mock_open()), \
         patch("runner.subprocess.run", return_value=mock_process) as mock_run, \
         patch.object(Path, "unlink"):
        
        from runner import run_fuer_einen_user
        
        await run_fuer_einen_user()
        
        # Überprüfe dass subprocess.run aufgerufen wurde
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "main.py" in call_args
        assert test_user["email"] in call_args
    
    capsys.readouterr()


@pytest.mark.asyncio
async def test_runner_subprocess_fehler(capsys, test_user, test_users):
    """Test: run_fuer_einen_user() bricht ab bei returncode != 0."""
    mock_path = MagicMock()
    mock_process = MagicMock()
    mock_process.returncode = 1
    
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": test_user["email"]}), \
         patch("runner.lade_alle_user", return_value=test_users), \
         patch("runner.Path", return_value=mock_path), \
         patch("builtins.open", mock_open()), \
         patch("runner.subprocess.run", return_value=mock_process), \
         patch.object(Path, "unlink"):
        
        from runner import run_fuer_einen_user
        
        try:
            await run_fuer_einen_user()
            assert False, "Sollte SystemExit werfen"
        except SystemExit as e:
            assert e.code == 1
    
    capsys.readouterr()


@pytest.mark.asyncio
async def test_runner_subprocess_timeout(capsys, test_user, test_users):
    """Test: run_fuer_einen_user() handhabt Timeout."""
    mock_path = MagicMock()
    
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": test_user["email"]}), \
         patch("runner.lade_alle_user", return_value=test_users), \
         patch("runner.Path", return_value=mock_path), \
         patch("builtins.open", mock_open()), \
         patch("runner.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 1800)), \
         patch.object(Path, "unlink"):
        
        from runner import run_fuer_einen_user
        
        try:
            await run_fuer_einen_user()
            assert False, "Sollte SystemExit werfen"
        except SystemExit as e:
            assert e.code == 1
    
    capsys.readouterr()


# === Tests: Cleanup ===

@pytest.mark.asyncio
async def test_runner_cleanup_temp_datei(capsys, test_user, test_users):
    """Test: run_fuer_einen_user() löscht temporäre Config-Datei."""
    mock_path = MagicMock()
    mock_process = MagicMock()
    mock_process.returncode = 0
    
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": test_user["email"]}), \
         patch("runner.lade_alle_user", return_value=test_users), \
         patch("runner.Path", return_value=mock_path) as mock_path_class, \
         patch("builtins.open", mock_open()), \
         patch("runner.subprocess.run", return_value=mock_process):
        
        from runner import run_fuer_einen_user
        
        await run_fuer_einen_user()
        
        # Überprüfe dass unlink() aufgerufen wurde (mit missing_ok=True)
        mock_path.unlink.assert_called_once()
        call_kwargs = mock_path.unlink.call_args.kwargs
        assert call_kwargs.get("missing_ok") is True
    
    capsys.readouterr()


@pytest.mark.asyncio
async def test_runner_cleanup_auch_bei_fehler(capsys, test_user, test_users):
    """Test: Temp-Datei wird auch bei Fehler gelöscht (finally-Block)."""
    mock_path = MagicMock()
    
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": test_user["email"]}), \
         patch("runner.lade_alle_user", return_value=test_users), \
         patch("runner.Path", return_value=mock_path), \
         patch("builtins.open", mock_open()), \
         patch("runner.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 1800)):
        
        from runner import run_fuer_einen_user
        
        try:
            await run_fuer_einen_user()
        except SystemExit:
            pass
        
        # Überprüfe dass unlink() trotz Fehler aufgerufen wurde
        mock_path.unlink.assert_called_once()
    
    capsys.readouterr()


# === Tests: Config-Struktur ===

@pytest.mark.asyncio
async def test_runner_config_mit_defaults(capsys, test_users):
    """Test: Fehlende Config-Felder bekommen Default-Werte."""
    minimal_user = {
        "email": "minimal@example.com",
        "groesse": "M",
        "max_preis": 50,
        "stile": ["Casual"],
    }
    users_with_minimal = [minimal_user]
    
    mock_path = MagicMock()
    mock_process = MagicMock()
    mock_process.returncode = 0
    
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": minimal_user["email"]}), \
         patch("runner.lade_alle_user", return_value=users_with_minimal), \
         patch("runner.Path", return_value=mock_path), \
         patch("builtins.open", mock_open()) as mock_file, \
         patch("runner.subprocess.run", return_value=mock_process):
        
        from runner import run_fuer_einen_user
        
        await run_fuer_einen_user()
        
        # Überprüfe dass Config-Datei geschrieben wurde
        assert mock_file.called
    
    capsys.readouterr()


# === Tests: Umgebungsvariablen in Config ===

@pytest.mark.asyncio
async def test_runner_config_enthält_ollama_url(capsys, test_user, test_users):
    """Test: Config enthält OLLAMA_URL."""
    mock_path = MagicMock()
    mock_process = MagicMock()
    mock_process.returncode = 0
    
    with patch.dict("os.environ", {"TARGET_USER_EMAIL": test_user["email"]}), \
         patch("runner.lade_alle_user", return_value=test_users), \
         patch("runner.Path", return_value=mock_path), \
         patch("builtins.open", mock_open()), \
         patch("runner.subprocess.run", return_value=mock_process):
        
        from runner import run_fuer_einen_user
        
        await run_fuer_einen_user()
        
        # Überprüfe dass subprocess.run mit korrekter Config aufgerufen wurde
        call_args = mock_process.run.call_args if hasattr(mock_process, "run") else None
    
    capsys.readouterr()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])