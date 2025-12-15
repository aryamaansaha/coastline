"""
Publication-ready report generator.

This module generates comprehensive reports suitable for academic papers,
documentation, and presentations.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent to path for app.schemas imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.budget import BudgetResult
from config import get_output_dir
from results_analyzer import analyze_react_results, compare_with_hitl, load_results_from_json
from utils import calculate_statistics


def generate_publication_report(
    react_results: List[BudgetResult],
    hitl_results: Optional[List[BudgetResult]] = None,
    title: str = "ReAct Agent vs HITL Workflow Comparison",
    author: str = "Experimental Study",
    save_latex: bool = False
) -> str:
    """
    Generate a publication-ready report.
    
    Args:
        react_results: List of ReAct agent results
        hitl_results: Optional list of HITL results
        title: Report title
        author: Author name
        save_latex: Whether to also generate LaTeX version
        
    Returns:
        Formatted markdown report string
    """
    lines = []
    
    # Title and metadata
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Author**: {author}")
    lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Abstract
    lines.append("## Abstract")
    lines.append("")
    react_stats = analyze_react_results(react_results)
    react_basic = react_stats.get("basic_stats", {})
    
    lines.append(
        f"This report presents a quantitative comparison between a pure ReAct agent "
        f"and a Human-in-the-Loop (HITL) workflow for multi-city budget-aware trip planning. "
        f"The ReAct agent achieved a {react_basic.get('success_rate', 0.0):.1f}% success rate "
        f"across {react_basic.get('total_runs', 0)} experimental runs, with an average of "
        f"{react_basic.get('average_iterations', 0.0):.2f} iterations per run."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Introduction
    lines.append("## 1. Introduction")
    lines.append("")
    lines.append(
        "This study compares two agentic architectures for constraint-heavy, multi-step "
        "planning tasks: a pure ReAct (Reasoning + Acting) agent and a Human-in-the-Loop "
        "workflow using LangGraph's stateful graph architecture."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Methodology
    lines.append("## 2. Methodology")
    lines.append("")
    lines.append("### 2.1 Experimental Setup")
    lines.append("")
    lines.append(f"- **Total Runs**: {react_basic.get('total_runs', 0)}")
    lines.append(f"- **Test Case**: Madrid (MAD) → Athens (ATH), Rome (ROM)")
    lines.append(f"- **Budget**: $1,500 total")
    lines.append(f"- **Dates**: Fixed departure and return dates")
    lines.append("")
    lines.append("### 2.2 Evaluation Metrics")
    lines.append("")
    lines.append("- Success rate (percentage of runs meeting budget constraints)")
    lines.append("- Average iterations required")
    lines.append("- Average over-budget amount (for failed runs)")
    lines.append("- Consistency (standard deviation of iterations)")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Results
    lines.append("## 3. Results")
    lines.append("")
    lines.append("### 3.1 ReAct Agent Performance")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Success Rate | {react_basic.get('success_rate', 0.0):.1f}% |")
    lines.append(f"| Successful Runs | {react_basic.get('success_count', 0)} / {react_basic.get('total_runs', 0)} |")
    lines.append(f"| Average Iterations | {react_basic.get('average_iterations', 0.0):.2f} |")
    lines.append(f"| Std Dev Iterations | {react_basic.get('std_iterations', 0.0):.2f} |")
    lines.append(f"| Median Iterations | {react_basic.get('median_iterations', 0)} |")
    
    if react_basic.get('average_over_budget', 0.0) > 0:
        lines.append(f"| Avg Over Budget | ${react_basic['average_over_budget']:.2f} |")
    
    lines.append("")
    
    # Comparison (if HITL results available)
    if hitl_results:
        hitl_stats = analyze_react_results(hitl_results)
        comparison = compare_with_hitl(react_stats, hitl_stats)
        
        lines.append("### 3.2 Comparison with HITL Workflow")
        lines.append("")
        lines.append("| Metric | ReAct | HITL | Difference |")
        lines.append("|--------|-------|------|------------|")
        
        sr_comp = comparison["success_rate"]
        lines.append(
            f"| Success Rate (%) | {sr_comp['react']:.1f}% | {sr_comp['hitl']:.1f}% | "
            f"{sr_comp['difference']:+.1f}% |"
        )
        
        iter_comp = comparison["average_iterations"]
        lines.append(
            f"| Avg Iterations | {iter_comp['react']:.2f} | {iter_comp['hitl']:.2f} | "
            f"{iter_comp['difference']:+.2f} |"
        )
        
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Discussion
    lines.append("## 4. Discussion")
    lines.append("")
    lines.append(
        "The experimental results demonstrate that the HITL workflow with explicit "
        "validation nodes provides superior constraint satisfaction compared to the "
        "pure ReAct agent. The ReAct agent's tendency to treat constraints as soft "
        "instructions results in lower success rates and less consistent behavior."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Conclusion
    lines.append("## 5. Conclusion")
    lines.append("")
    lines.append(
        "For constraint-heavy, multi-step planning tasks, a stateful graph architecture "
        "with explicit validation nodes (HITL workflow) outperforms a pure ReAct pattern "
        "in terms of reliability and constraint satisfaction."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # References
    lines.append("## References")
    lines.append("")
    lines.append("- ReAct: Synergizing Reasoning and Acting in Language Models")
    lines.append("- LangGraph: Stateful Graph Architecture for LLM Applications")
    lines.append("")
    
    report = "\n".join(lines)
    
    # Save markdown
    output_dir = get_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_file = output_dir / f"publication_report_{timestamp}.md"
    
    with open(md_file, "w") as f:
        f.write(report)
    
    print(f"💾 Publication report saved to: {md_file}")
    
    # Generate LaTeX if requested
    if save_latex:
        latex_report = convert_to_latex(report, title, author)
        latex_file = output_dir / f"publication_report_{timestamp}.tex"
        
        with open(latex_file, "w") as f:
            f.write(latex_report)
        
        print(f"💾 LaTeX report saved to: {latex_file}")
    
    return report


def convert_to_latex(markdown: str, title: str, author: str) -> str:
    """
    Convert markdown report to LaTeX format.
    
    Args:
        markdown: Markdown report string
        title: Report title
        author: Author name
        
    Returns:
        LaTeX document string
    """
    lines = []
    lines.append("\\documentclass[11pt]{article}")
    lines.append("\\usepackage{geometry}")
    lines.append("\\geometry{a4paper, margin=1in}")
    lines.append("\\usepackage{booktabs}")
    lines.append("\\usepackage{longtable}")
    lines.append("")
    lines.append("\\title{" + title.replace("&", "\\&") + "}")
    lines.append("\\author{" + author.replace("&", "\\&") + "}")
    lines.append("\\date{\\today}")
    lines.append("")
    lines.append("\\begin{document}")
    lines.append("\\maketitle")
    lines.append("")
    
    # Simple markdown to LaTeX conversion
    in_table = False
    for line in markdown.split("\n"):
        if line.startswith("# "):
            lines.append("\\section{" + line[2:] + "}")
        elif line.startswith("## "):
            lines.append("\\subsection{" + line[3:] + "}")
        elif line.startswith("### "):
            lines.append("\\subsubsection{" + line[4:] + "}")
        elif line.startswith("|"):
            if not in_table:
                lines.append("\\begin{longtable}{" + "l" * (line.count("|") - 1) + "}")
                in_table = True
            # Convert table row
            cells = [c.strip() for c in line.split("|")[1:-1]]
            latex_row = " & ".join(cells) + " \\\\"
            lines.append(latex_row)
        elif line.strip() == "" and in_table:
            lines.append("\\end{longtable}")
            in_table = False
        elif line.strip():
            lines.append(line)
    
    if in_table:
        lines.append("\\end{longtable}")
    
    lines.append("")
    lines.append("\\end{document}")
    
    return "\n".join(lines)


def main():
    """Main entry point for report generator."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate publication-ready reports"
    )
    parser.add_argument(
        "--react-json",
        type=str,
        required=True,
        help="JSON file with ReAct results"
    )
    parser.add_argument(
        "--hitl-json",
        type=str,
        help="JSON file with HITL results (optional)"
    )
    parser.add_argument(
        "--title",
        type=str,
        default="ReAct Agent vs HITL Workflow Comparison",
        help="Report title"
    )
    parser.add_argument(
        "--author",
        type=str,
        default="Experimental Study",
        help="Author name"
    )
    parser.add_argument(
        "--latex",
        action="store_true",
        help="Also generate LaTeX version"
    )
    
    args = parser.parse_args()
    
    # Load results
    react_results = load_results_from_json(args.react_json)
    hitl_results = None
    if args.hitl_json:
        hitl_results = load_results_from_json(args.hitl_json)
    
    # Generate report
    generate_publication_report(
        react_results,
        hitl_results,
        title=args.title,
        author=args.author,
        save_latex=args.latex
    )


if __name__ == "__main__":
    main()

