"""Unit tests for RollbackContext."""

import pytest

from typysetup.utils.rollback_context import RollbackContext


class TestRollbackContext:
    """Tests for RollbackContext context manager."""

    def test_rollback_context_no_exception(self):
        """Test that cleanup is not executed when no exception occurs."""
        cleanup_called = False

        def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        with RollbackContext() as ctx:
            ctx.register_cleanup(cleanup, "Test cleanup")
            # No exception - cleanup should not be called

        assert not cleanup_called

    def test_rollback_context_with_exception(self):
        """Test that cleanup is executed when exception occurs."""
        cleanup_called = False

        def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                ctx.register_cleanup(cleanup, "Test cleanup")
                raise RuntimeError("Test error")

        assert cleanup_called

    def test_rollback_executes_lifo_order(self):
        """Test that cleanup actions execute in LIFO (Last In, First Out) order."""
        order = []

        def cleanup1():
            order.append(1)

        def cleanup2():
            order.append(2)

        def cleanup3():
            order.append(3)

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                ctx.register_cleanup(cleanup1, "First cleanup")
                ctx.register_cleanup(cleanup2, "Second cleanup")
                ctx.register_cleanup(cleanup3, "Third cleanup")
                raise RuntimeError("Test error")

        # Should execute in reverse order: 3, 2, 1
        assert order == [3, 2, 1]

    def test_rollback_continues_on_cleanup_failure(self):
        """Test that rollback continues even if individual cleanup fails."""
        cleanup1_called = False
        cleanup2_called = False
        cleanup3_called = False

        def cleanup1():
            nonlocal cleanup1_called
            cleanup1_called = True
            raise RuntimeError("Cleanup 1 failed")

        def cleanup2():
            nonlocal cleanup2_called
            cleanup2_called = True

        def cleanup3():
            nonlocal cleanup3_called
            cleanup3_called = True
            raise RuntimeError("Cleanup 3 failed")

        with pytest.raises(RuntimeError, match="Test error"):
            with RollbackContext() as ctx:
                ctx.register_cleanup(cleanup3, "Third cleanup")
                ctx.register_cleanup(cleanup2, "Second cleanup")
                ctx.register_cleanup(cleanup1, "First cleanup")
                raise RuntimeError("Test error")

        # All should be called despite failures
        assert cleanup1_called
        assert cleanup2_called
        assert cleanup3_called

    def test_rollback_with_multiple_cleanup_actions(self):
        """Test rollback with many cleanup actions."""
        cleanup_count = 0

        def make_cleanup(num):
            def cleanup():
                nonlocal cleanup_count
                cleanup_count += 1

            return cleanup

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                for i in range(10):
                    ctx.register_cleanup(make_cleanup(i), f"Cleanup {i}")
                raise RuntimeError("Test error")

        assert cleanup_count == 10

    def test_rollback_context_exception_propagates(self):
        """Test that original exception is propagated after cleanup."""
        with pytest.raises(ValueError, match="Original error"):
            with RollbackContext() as ctx:
                ctx.register_cleanup(lambda: None, "Cleanup")
                raise ValueError("Original error")

    def test_rollback_context_returns_self(self):
        """Test that __enter__ returns the context instance."""
        ctx = RollbackContext()
        with ctx as returned:
            assert returned is ctx

    def test_register_cleanup_with_empty_description(self):
        """Test that cleanup can be registered without description."""
        cleanup_called = False

        def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                ctx.register_cleanup(cleanup)  # No description
                raise RuntimeError("Test error")

        assert cleanup_called

    def test_register_cleanup_stores_description(self):
        """Test that descriptions are stored with cleanup actions."""
        ctx = RollbackContext()

        def cleanup1():
            pass

        def cleanup2():
            pass

        ctx.register_cleanup(cleanup1, "First action")
        ctx.register_cleanup(cleanup2, "Second action")

        # Check that both actions are registered
        assert len(ctx.cleanup_actions) == 2
        assert ctx.cleanup_actions[0] == (cleanup1, "First action")
        assert ctx.cleanup_actions[1] == (cleanup2, "Second action")

    def test_no_exception_type_means_no_rollback(self):
        """Test that __exit__ returning False doesn't suppress exceptions."""
        cleanup_called = False

        def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        ctx = RollbackContext()
        # Simulate __exit__ being called with no exception (None, None, None)
        result = ctx.__exit__(None, None, None)

        # Should return False (don't suppress)
        assert result is False
        # Cleanup should NOT be called when no exception
        assert not cleanup_called

    def test_keyboard_interrupt_triggers_rollback(self):
        """Test that KeyboardInterrupt triggers rollback."""
        cleanup_called = False

        def cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        with pytest.raises(KeyboardInterrupt):
            with RollbackContext() as ctx:
                ctx.register_cleanup(cleanup, "Cleanup")
                raise KeyboardInterrupt()

        assert cleanup_called

    def test_cleanup_with_lambda(self):
        """Test cleanup actions using lambda functions."""
        cleanup_value = []

        with pytest.raises(RuntimeError):
            with RollbackContext() as ctx:
                ctx.register_cleanup(lambda: cleanup_value.append("cleaned"), "Lambda cleanup")
                raise RuntimeError("Test error")

        assert cleanup_value == ["cleaned"]
