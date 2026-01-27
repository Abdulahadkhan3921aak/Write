"""
Integration test for Write IDE GUI refactoring.
Tests theme, completions, keyword help, and editor features.
"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.gui.theme import ThemeManager, ThemeMode
from src.gui.keyword_help import KeywordDatabase
from src.gui.completions import CompletionProvider, CompletionModel
from src.gui.diagnostics import DiagnosticsHelper


def test_theme_manager():
    """Test theme manager functionality."""
    print("Testing ThemeManager...")
    mgr = ThemeManager()

    # Test mode switching
    mgr.save_theme_mode(ThemeMode.LIGHT)
    assert mgr.current_mode == ThemeMode.LIGHT
    print("  ✓ Light theme mode")

    mgr.save_theme_mode(ThemeMode.DARK)
    assert mgr.current_mode == ThemeMode.DARK
    print("  ✓ Dark theme mode")

    # Test palette generation
    light_pal = mgr._create_light_palette()
    dark_pal = mgr._create_dark_palette()
    assert light_pal is not None
    assert dark_pal is not None
    print("  ✓ Palette generation")

    # Test syntax colors
    colors = mgr.get_syntax_colors()
    assert "keyword" in colors
    assert "number" in colors
    assert "string" in colors
    print("  ✓ Syntax colors")


def test_keyword_database():
    """Test keyword database."""
    print("\nTesting KeywordDatabase...")

    # Test keyword retrieval
    all_kw = KeywordDatabase.get_all_keywords()
    assert "make" in all_kw
    assert "list" in all_kw
    assert "as" in all_kw
    assert "of" in all_kw
    assert "size" in all_kw
    print(f"  ✓ {len(all_kw)} keywords available")

    # Test help text
    help_make = KeywordDatabase.get_help("make")
    assert "make" in help_make.lower()
    print("  ✓ Help text for 'make'")

    # Test keyword checking
    assert KeywordDatabase.is_keyword("function")
    assert KeywordDatabase.is_keyword("FUNCTION")  # Case insensitive
    assert not KeywordDatabase.is_keyword("myvar")
    print("  ✓ Keyword checking")


def test_completion_provider():
    """Test completion provider."""
    print("\nTesting CompletionProvider...")

    keywords = ["make", "as", "list", "size", "function"]
    provider = CompletionProvider(keywords)

    # Test completion matching
    comps = provider.get_completions("ma")
    assert "make" in comps
    print("  ✓ Keyword prefix matching")

    # Test symbol completion
    provider.set_symbols({"myFunc"}, {"myVar", "x", "y"})
    comps = provider.get_completions("my", "set")
    assert "myVar" in comps or "myFunc" in comps
    print("  ✓ Symbol-based completion")

    # Test best completion
    best = provider.get_best_completion("func")
    assert best == "function"
    print("  ✓ Best completion selection")


def test_completion_model():
    """Test completion model."""
    print("\nTesting CompletionModel...")

    model = CompletionModel()
    items = ["function", "for", "from"]
    model.set_items(items)

    assert model.rowCount() == 3
    print("  ✓ Model item count")

    data = model.data(model.index(0, 0))
    assert data == "function"
    print("  ✓ Model data retrieval")


def test_diagnostics_helper():
    """Test diagnostics helper."""
    print("\nTesting DiagnosticsHelper...")

    # Test diagnostic parsing
    stderr = "Error at 5:10: unexpected token\nWarning at 3:2: unused variable"
    diags = DiagnosticsHelper.parse_diagnostics(stderr)
    assert len(diags) > 0
    print(f"  ✓ Parsed {len(diags)} diagnostics")

    # Test lint hints generation
    stderr_func = "Error: function mismatch"
    hints = DiagnosticsHelper.generate_lint_hints(stderr_func)
    assert len(hints) > 0
    print("  ✓ Lint hints generation")

    # Test lightweight linting
    code = """function "test" arguments:(x:int)
    set y to x
end function"""
    lint_hints = DiagnosticsHelper.compute_lightweight_hints(code)
    assert isinstance(lint_hints, list)
    print("  ✓ Lightweight linting")


def test_keyword_list():
    """Verify all required keywords are available."""
    print("\nTesting required keywords...")

    required = ["make", "list", "as", "of", "size", "set", "print", "if", "function"]
    for kw in required:
        assert KeywordDatabase.is_keyword(kw), f"Missing keyword: {kw}"

    print(f"  ✓ All {len(required)} required keywords present")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Write IDE GUI Refactoring - Integration Tests")
    print("=" * 60)

    try:
        test_theme_manager()
        test_keyword_database()
        test_completion_provider()
        test_completion_model()
        test_diagnostics_helper()
        test_keyword_list()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
