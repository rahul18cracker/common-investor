"""
Tests for Research Agent

Unit tests for the qualitative research agent components.
"""

import pytest
from app.nlp.research_agent.experimental.workflows import (
    QualitativeResearchWorkflow,
    analyze_ticker,
)
from app.nlp.research_agent.experimental.tools import (
    SECFilingTool,
    FinancialMetricsTool,
    get_tool,
)
from app.nlp.research_agent.reports.generator import ReportGenerator


class TestSECFilingTool:
    """Tests for SEC filing retrieval tool."""

    def test_sec_tool_initialization(self):
        """Test SEC tool can be initialized."""
        tool = SECFilingTool()
        assert tool.name == "SEC Filing Retriever"
        assert tool.description is not None

    def test_get_filing_returns_dict(self):
        """Test get_filing returns expected structure."""
        tool = SECFilingTool()
        result = tool.get_filing("AAPL", "10-K")

        assert isinstance(result, dict)
        assert "ticker" in result
        assert "form_type" in result
        assert result["ticker"] == "AAPL"
        assert result["form_type"] == "10-K"


class TestFinancialMetricsTool:
    """Tests for financial metrics tool."""

    def test_metrics_tool_initialization(self):
        """Test metrics tool can be initialized."""
        tool = FinancialMetricsTool()
        assert tool.name == "Financial Metrics Retriever"

    def test_get_metrics_returns_dict(self):
        """Test get_metrics returns expected structure."""
        tool = FinancialMetricsTool()
        result = tool.get_metrics("MSFT")

        assert isinstance(result, dict)
        assert "ticker" in result
        assert result["ticker"] == "MSFT"


class TestQualitativeResearchWorkflow:
    """Tests for the research workflow."""

    def test_workflow_initialization(self):
        """Test workflow can be initialized."""
        workflow = QualitativeResearchWorkflow()
        assert workflow.sec_tool is not None
        assert workflow.metrics_tool is not None

    def test_analyze_company_returns_result(self):
        """Test analyze_company returns AnalysisResult."""
        workflow = QualitativeResearchWorkflow()
        result = workflow.analyze_company("AAPL")

        assert result.ticker == "AAPL"
        assert result.status in ["pending", "processing", "completed", "failed"]

    def test_analyze_ticker_convenience_function(self):
        """Test the convenience function works."""
        result = analyze_ticker("GOOGL")
        assert result.ticker == "GOOGL"


class TestReportGenerator:
    """Tests for report generation."""

    def test_generator_initialization(self):
        """Test report generator can be initialized."""
        generator = ReportGenerator()
        assert generator.template_dir is not None

    def test_generate_markdown_report(self):
        """Test markdown report generation."""
        generator = ReportGenerator()

        analysis_result = {
            "business_analysis": {"score": 8.0},
            "moat_analysis": {"score": 7.5},
            "management_analysis": {"score": 8.5},
            "recommendation": {"overall_score": 8.0},
        }

        report = generator.generate_markdown_report(
            ticker="AAPL",
            company_name="Apple Inc.",
            analysis_result=analysis_result,
            cost_usd=0.25,
        )

        assert isinstance(report, str)
        assert "AAPL" in report
        assert "Apple Inc." in report
        assert "Qualitative Analysis" in report


# Integration test placeholder
@pytest.mark.skip(reason="Integration test - requires LLM API")
def test_full_analysis_workflow():
    """
    Full integration test for the research agent.

    This test is skipped by default as it requires:
    - LLM API access (OpenAI/Anthropic)
    - SEC data ingestion
    - Significant execution time
    """
    result = analyze_ticker("MSFT")
    assert result.status == "completed"
    assert result.business_analysis is not None
    assert result.moat_analysis is not None
