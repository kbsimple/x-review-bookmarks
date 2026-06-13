"""CLI integration tests for xbm export-static command.

EXPORT-01 through EXPORT-04: CLI command creates output directory with all files.
"""

import pytest
from pathlib import Path


class TestExportStaticCLI:
    """Integration tests for the export-static CLI command.

    Uses typer.testing.CliRunner -- same pattern as test_cli.py.
    All stubs until Wave 4 implements the CLI command.
    """

    @pytest.mark.skip(reason="Wave 4: implement export_static CLI command first")
    def test_export_static_command_creates_output_dir(self, tmp_path):
        """xbm export-static --output <tmp_path> exits 0 and creates directory."""
        pass

    @pytest.mark.skip(reason="Wave 4: implement export_static CLI command first")
    def test_export_static_with_custom_output_path(self, tmp_path):
        """--output flag routes output to specified directory."""
        pass

    @pytest.mark.skip(reason="Wave 4: implement export_static CLI command first")
    def test_export_static_prints_deployment_instructions(self, tmp_path):
        """CLI output contains 'netlify' in console output after completion."""
        pass

    @pytest.mark.skip(reason="Wave 4: implement export_static CLI command first")
    def test_export_static_summary_table_shows_file_sizes(self, tmp_path):
        """CLI output contains 'posts.json' in summary table."""
        pass
