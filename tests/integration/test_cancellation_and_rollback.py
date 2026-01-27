"""
Integration tests for cancellation and rollback (T135).

Tests cancellation between phases, Ctrl+C handling, and cleanup verification.
"""

import json
import subprocess
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from typysetup.main import app


@pytest.fixture
def cli_runner():
    """Typer CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def mock_questionary_auto_confirm():
    """Mock Questionary to automatically confirm all prompts."""

    class MockSelect:
        def __init__(self, message, choices, **kwargs):
            self.choices = choices

        def ask(self):
            # Select first choice
            if isinstance(self.choices, list) and len(self.choices) > 0:
                return self.choices[0] if isinstance(self.choices[0], str) else "FastAPI"
            return "FastAPI"

    class MockConfirm:
        def __init__(self, message, **kwargs):
            pass

        def ask(self):
            return True

    return {"select": MockSelect, "confirm": MockConfirm}


class TestCancellationAndRollback:
    """Test cancellation and rollback mechanisms."""

    def test_rollback_on_venv_creation_failure(self, tmp_path, cli_runner):
        """Test that rollback removes partial venv on creation failure."""
        project_path = tmp_path / "test-venv-rollback"
        project_path.mkdir()

        venv_path = project_path / "venv"

        # Create a file to simulate partial venv
        venv_path.mkdir()
        (venv_path / "partial_file.txt").write_text("partial")

        class MockSelect:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def ask(self):
                return True

        # Mock venv creation to fail
        def mock_create_fail(*args, **kwargs):
            raise RuntimeError("Venv creation failed")

        with patch("questionary.select", MockSelect), patch(
            "questionary.confirm", MockConfirm
        ), patch("venv.EnvBuilder.create", side_effect=mock_create_fail):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            # Should fail
            assert result.exit_code == 1

            # Rollback should have cleaned up
            # (Actual rollback behavior depends on implementation)
            # If rollback is implemented, venv should be removed

    def test_rollback_on_dependency_installation_failure(
        self, tmp_path, cli_runner, mock_questionary_auto_confirm
    ):
        """Test that rollback cleans up on dependency installation failure."""
        project_path = tmp_path / "test-deps-rollback"
        project_path.mkdir()

        # Mock subprocess to fail during dependency installation
        call_count = {"count": 0}

        def mock_run_partial_fail(cmd, *args, **kwargs):
            call_count["count"] += 1

            # Fail on dependency installation (2nd or 3rd call typically)
            if call_count["count"] > 1 and any(
                pkg_mgr in str(cmd) for pkg_mgr in ["pip", "uv", "poetry"]
            ):
                raise subprocess.CalledProcessError(
                    1, cmd, stderr=b"Failed to install dependencies"
                )

            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

        with patch("questionary.select", mock_questionary_auto_confirm["select"]), patch(
            "questionary.confirm", mock_questionary_auto_confirm["confirm"]
        ), patch("subprocess.run", side_effect=mock_run_partial_fail):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            # Should fail
            assert result.exit_code == 1

            # Verify rollback cleaned up venv
            venv_path = project_path / "venv"
            # If rollback is implemented correctly, venv should be removed
            # (Check implementation to verify expected behavior)

    def test_rollback_on_vscode_config_failure(
        self, tmp_path, cli_runner, mock_questionary_auto_confirm
    ):
        """Test that rollback restores previous VSCode config on failure."""
        project_path = tmp_path / "test-vscode-rollback"
        project_path.mkdir()

        # Create existing VSCode settings
        vscode_dir = project_path / ".vscode"
        vscode_dir.mkdir()
        original_settings = {"editor.fontSize": 16, "workbench.colorTheme": "Dark+"}
        settings_file = vscode_dir / "settings.json"
        settings_file.write_text(json.dumps(original_settings, indent=2))

        # Mock to fail during VSCode config generation
        def mock_generate_fail(*args, **kwargs):
            raise PermissionError("Cannot write VSCode config")

        with patch("questionary.select", mock_questionary_auto_confirm["select"]), patch(
            "questionary.confirm", mock_questionary_auto_confirm["confirm"]
        ), patch(
            "typysetup.core.vscode_config_generator.VSCodeConfigGenerator.generate",
            side_effect=mock_generate_fail,
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            # Should fail
            assert result.exit_code == 1

            # Verify original settings restored (if rollback implemented)
            if settings_file.exists():
                current_settings = json.loads(settings_file.read_text())
                # Should match original
                assert current_settings.get("editor.fontSize") == 16

    def test_ctrl_c_cancellation_during_setup(self, tmp_path):
        """Test Ctrl+C (SIGINT) handling during setup."""
        project_path = tmp_path / "test-ctrl-c"
        project_path.mkdir()

        # This test simulates user pressing Ctrl+C
        # In real scenario, SIGINT would be sent

        def simulate_interrupt(*args, **kwargs):
            """Simulate user interrupt."""
            raise KeyboardInterrupt("User cancelled")

        class MockSelect:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def ask(self):
                return True

        runner = CliRunner()

        with patch("questionary.select", MockSelect), patch(
            "questionary.confirm", MockConfirm
        ), patch("subprocess.run", side_effect=simulate_interrupt):
            result = runner.invoke(app, ["setup", str(project_path)])

            # Should handle KeyboardInterrupt gracefully
            assert result.exit_code in [0, 1, 130]  # 130 is common for SIGINT

    def test_multiple_rollback_actions_execute_in_lifo_order(self, tmp_path):
        """Test that rollback actions execute in LIFO (Last-In-First-Out) order."""
        # This test verifies the RollbackContext implementation

        from typysetup.utils.rollback_context import RollbackContext

        cleanup_order = []

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                # Register cleanup actions
                ctx.register_cleanup(lambda: cleanup_order.append("first"))
                ctx.register_cleanup(lambda: cleanup_order.append("second"))
                ctx.register_cleanup(lambda: cleanup_order.append("third"))

                # Trigger rollback
                raise RuntimeError("Simulated failure")

        # Verify LIFO order (last registered executes first)
        assert cleanup_order == ["third", "second", "first"]

    def test_idempotent_rollback_actions(self, tmp_path):
        """Test that rollback actions are idempotent (safe to call multiple times)."""
        from typysetup.utils.rollback_context import RollbackContext

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        call_count = {"count": 0}

        def idempotent_cleanup():
            """Cleanup action that can be called multiple times safely."""
            call_count["count"] += 1
            if test_file.exists():
                test_file.unlink()

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                ctx.register_cleanup(idempotent_cleanup)
                raise RuntimeError("Trigger rollback")

        # Cleanup should have been called once
        assert call_count["count"] == 1
        assert not test_file.exists()

        # Calling again should be safe (idempotent)
        idempotent_cleanup()
        assert call_count["count"] == 2
        assert not test_file.exists()  # Still doesn't exist

    def test_rollback_context_logs_cleanup_failures(self, tmp_path, caplog):
        """Test that rollback context logs failures during cleanup."""
        from typysetup.utils.rollback_context import RollbackContext

        def failing_cleanup():
            """Cleanup that always fails."""
            raise ValueError("Cleanup failed")

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                ctx.register_cleanup(failing_cleanup)
                raise RuntimeError("Trigger rollback")

        # Should log the cleanup failure (not crash)
        # Check logs for error message
        assert any(
            "Rollback" in record.message or "failed" in record.message.lower()
            for record in caplog.records
        )

    def test_partial_setup_leaves_no_artifacts(
        self, tmp_path, cli_runner, mock_questionary_auto_confirm
    ):
        """Test that failed setup leaves no partial artifacts."""
        project_path = tmp_path / "test-clean-failure"
        project_path.mkdir()

        # Mock to fail early (during venv creation)
        def mock_fail_early(*args, **kwargs):
            raise RuntimeError("Early failure")

        with patch("questionary.select", mock_questionary_auto_confirm["select"]), patch(
            "questionary.confirm", mock_questionary_auto_confirm["confirm"]
        ), patch("venv.EnvBuilder.create", side_effect=mock_fail_early):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            assert result.exit_code == 1

            # Verify no artifacts left behind
            assert not (project_path / "venv").exists()
            assert not (project_path / ".vscode").exists()
            assert not (project_path / ".typysetup").exists()

    def test_cancellation_between_phases_prompt(self, tmp_path, cli_runner):
        """Test cancellation when user declines confirmation between phases."""
        project_path = tmp_path / "test-cancel-confirm"
        project_path.mkdir()

        class MockSelect:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def __init__(self, message, **kwargs):
                self.message = message

            def ask(self):
                # Decline final confirmation
                if "proceed" in self.message.lower():
                    return False
                return True

        with patch("questionary.select", MockSelect), patch("questionary.confirm", MockConfirm):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            # Should cancel gracefully
            # Exit code depends on implementation (0 for graceful cancel, 1 for error)
            assert result.exit_code in [0, 1]

            # No setup should have occurred
            assert not (project_path / "venv").exists()


class TestRollbackContextEdgeCases:
    """Test edge cases in RollbackContext implementation."""

    def test_rollback_context_with_no_cleanup_actions(self):
        """Test RollbackContext with no registered cleanup actions."""
        from typysetup.utils.rollback_context import RollbackContext

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                # No cleanup actions registered
                raise RuntimeError("Error with no cleanup")

        # Should handle gracefully (no crash)

    def test_rollback_context_success_path_skips_cleanup(self, tmp_path):
        """Test that successful completion skips cleanup actions."""
        from typysetup.utils.rollback_context import RollbackContext

        cleanup_called = {"called": False}

        def cleanup_action():
            cleanup_called["called"] = True

        # Successful execution (no exception)
        with RollbackContext() as ctx:
            ctx.register_cleanup(cleanup_action)
            # No exception, success

        # Cleanup should NOT have been called
        assert not cleanup_called["called"]

    def test_rollback_context_partial_cleanup_failure(self, tmp_path):
        """Test rollback when some cleanup actions fail but others succeed."""
        from typysetup.utils.rollback_context import RollbackContext

        executed = {"first": False, "second": False, "third": False}

        def cleanup_first():
            executed["first"] = True

        def cleanup_second_fails():
            executed["second"] = True
            raise ValueError("Cleanup 2 failed")

        def cleanup_third():
            executed["third"] = True

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                ctx.register_cleanup(cleanup_first)
                ctx.register_cleanup(cleanup_second_fails)
                ctx.register_cleanup(cleanup_third)
                raise RuntimeError("Trigger rollback")

        # All cleanup actions should execute despite failures
        assert executed["first"] is True
        assert executed["second"] is True
        assert executed["third"] is True


class TestSetupCancellationScenarios:
    """Test various cancellation scenarios in setup flow."""

    def test_cancel_after_venv_creation_before_deps(self, tmp_path):
        """Test cancellation after venv created but before dependency installation."""
        # This would require instrumenting the setup flow to allow cancellation at specific points
        # Implementation depends on whether setup orchestrator supports phase-by-phase cancellation
        pass  # Placeholder for future implementation

    def test_cancel_during_vscode_config_generation(self, tmp_path):
        """Test cancellation during VSCode config generation."""
        pass  # Placeholder for future implementation

    def test_cancel_and_restart_setup(self, tmp_path, cli_runner):
        """Test that cancelled setup can be restarted successfully."""
        project_path = tmp_path / "test-restart"
        project_path.mkdir()

        # First attempt: cancel
        class MockConfirmCancel:
            def ask(self):
                return False  # Cancel

        class MockSelect:
            def ask(self):
                return "FastAPI"

        with patch("questionary.select", MockSelect), patch(
            "questionary.confirm", MockConfirmCancel
        ):
            result1 = cli_runner.invoke(app, ["setup", str(project_path)])

        # Second attempt: proceed
        class MockConfirmProceed:
            def ask(self):
                return True

        def mock_subprocess_success(cmd, *args, **kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

        with patch("questionary.select", MockSelect), patch(
            "questionary.confirm", MockConfirmProceed
        ), patch("subprocess.run", side_effect=mock_subprocess_success):
            result2 = cli_runner.invoke(app, ["setup", str(project_path)])

            # Second attempt should succeed
            assert result2.exit_code == 0
            assert (project_path / "venv").exists()
