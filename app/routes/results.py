"""
Results page route handler for LifeFinances app.
"""

import pandas as pd
import plotly
import plotly.graph_objects as go
from flask import render_template, session


class ResultsPage:
    """
    A class representing the results page of the LifeFinances app.

    Attributes:
        template (str): The HTML template for the results page.
    """

    def __init__(self):
        import logging

        logger = logging.getLogger(__name__)
        logger.info("ResultsPage.__init__ called")

        # Retrieve results from session
        self._first_results_data = session.get("first_results_data")
        self._first_results_columns = session.get("first_results_columns")

        logger.info("Retrieved from session:")
        logger.info(
            f"  first_results_data: {self._first_results_data is not None} (length: {len(self._first_results_data) if self._first_results_data else 0})"
        )
        logger.info(f"  first_results_columns: {self._first_results_columns}")
        logger.info(
            f"  success_percentage raw: {session.get('success_percentage')} (type: {type(session.get('success_percentage'))})"
        )

        # Convert success_percentage to float if it's a string
        success_pct = session.get("success_percentage")
        if success_pct is not None and isinstance(success_pct, str):
            self._success_percentage = float(success_pct)
            logger.info(
                f"  Converted success_percentage from string to float: {self._success_percentage}"
            )
        else:
            self._success_percentage = success_pct
            logger.info(f"  Using success_percentage as-is: {self._success_percentage}")

        # Generate visualizations if data available
        logger.info("Generating visualizations...")
        self._gauge_chart = self._generate_gauge_chart()
        logger.info(f"  Gauge chart generated: {self._gauge_chart is not None}")

        self._net_worth_chart = self._generate_net_worth_chart()
        logger.info(f"  Net worth chart generated: {self._net_worth_chart is not None}")

        self._first_results_table = self._generate_results_table()
        logger.info(
            f"  Results table generated: {self._first_results_table is not None}"
        )

    def _generate_gauge_chart(self) -> str | None:
        """
        Generate Plotly gauge chart for success rate.

        Returns:
            str | None: Plotly chart JSON or None if no data available.
        """
        if self._success_percentage is None:
            return None

        # Determine color based on success rate
        if self._success_percentage >= 80:
            color = "#10B981"  # Green
        elif self._success_percentage >= 60:
            color = "#F59E0B"  # Amber
        else:
            color = "#EF4444"  # Red

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=self._success_percentage,
                title={"text": "Success Rate", "font": {"color": "#F1F5F9"}},
                number={"suffix": "%", "font": {"color": "#F1F5F9"}},
                gauge={
                    "axis": {"range": [None, 100], "tickcolor": "#94A3B8"},
                    "bar": {"color": color},
                    "bgcolor": "#1E293B",
                    "borderwidth": 2,
                    "bordercolor": "#334155",
                    "steps": [
                        {"range": [0, 60], "color": "#334155"},
                        {"range": [60, 80], "color": "#475569"},
                        {"range": [80, 100], "color": "#64748B"},
                    ],
                },
            )
        )

        fig.update_layout(
            paper_bgcolor="#1E293B",
            plot_bgcolor="#1E293B",
            font={"color": "#F1F5F9"},
            height=250,
            margin=dict(l=20, r=20, t=40, b=20),
        )

        return plotly.io.to_json(fig)

    def _generate_net_worth_chart(self) -> str | None:
        """
        Generate Plotly line chart for net worth projection.

        Returns:
            str | None: Plotly chart JSON or None if no data available.
        """
        if self._first_results_data is None or self._first_results_columns is None:
            return None

        # Reconstruct DataFrame
        df = pd.DataFrame(self._first_results_data, columns=self._first_results_columns)

        # Need at least 2 columns for a meaningful chart
        if len(df.columns) < 2:
            return None

        # Assuming columns are: index, date, net_worth, ... (adjust as needed)
        # Try to find date and net worth columns
        date_col = None
        net_worth_col = None

        for col in df.columns:
            col_lower = col.lower()
            if "date" in col_lower or "time" in col_lower:
                date_col = col
            if "net" in col_lower and "worth" in col_lower:
                net_worth_col = col

        if date_col is None or net_worth_col is None:
            # Fallback: use second column for x and third for y (or first two if only 2 columns)
            if len(df.columns) >= 3:
                date_col = df.columns[1]
                net_worth_col = df.columns[2]
            else:
                date_col = df.columns[0]
                net_worth_col = df.columns[1]

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df[date_col],
                y=df[net_worth_col],
                mode="lines",
                name="Net Worth",
                line=dict(color="#3B82F6", width=2),
                fill="tozeroy",
                fillcolor="rgba(59, 130, 246, 0.1)",
                hovertemplate="<b>%{x}</b><br>Net Worth: $%{y:,.0f}K<extra></extra>",
            )
        )

        fig.update_layout(
            paper_bgcolor="#1E293B",
            plot_bgcolor="#1E293B",
            font={"color": "#F1F5F9"},
            height=300,
            margin=dict(l=50, r=20, t=20, b=40),
            xaxis=dict(
                gridcolor="#334155",
                showgrid=True,
                tickangle=45,
                tickfont={"color": "#94A3B8"},
            ),
            yaxis=dict(
                gridcolor="#334155",
                showgrid=True,
                tickfont={"color": "#94A3B8"},
                tickformat="$,.0f",
                ticksuffix="K",
            ),
            hovermode="x unified",
            showlegend=False,
        )

        return plotly.io.to_json(fig)

    def _generate_results_table(self) -> str | None:
        """
        Generate HTML table from session data.

        Returns:
            str | None: HTML table string or None if no data available.
        """
        if self._first_results_data is None or self._first_results_columns is None:
            return None

        # Reconstruct DataFrame from dict
        df = pd.DataFrame(self._first_results_data, columns=self._first_results_columns)

        # Generate HTML table with styling
        return df.to_html(classes="table table-striped", index=False)

    def _get_chartable_columns(self) -> list:
        """
        Get list of columns that can be charted with metadata.

        Returns:
            list: List of dicts with column info (name, display_name, category)
        """
        if self._first_results_columns is None:
            return []

        # Define column categories for better organization
        categories = {
            "wealth": ["Net Worth", "Portfolio Return", "Net Transaction"],
            "income": [
                "Job Income",
                "SS User",
                "SS Partner",
                "Pension",
                "Total Income",
                "Annuity",
            ],
            "expenses": ["Spending", "Kids", "Total Costs"],
            "taxes": [
                "Income Taxes",
                "Medicare Taxes",
                "Social Security Taxes",
                "Portfolio Taxes",
                "Total Taxes",
            ],
            "allocation": [col for col in self._first_results_columns if "%" in col],
            "rates": [
                col for col in self._first_results_columns if "rate" in col.lower()
            ],
            "other": ["Inflation"],
        }

        chartable = []
        categorized = set()

        # Add categorized columns
        for category, cols in categories.items():
            for col in cols:
                if col in self._first_results_columns and col != "Date":
                    chartable.append(
                        {"name": col, "display_name": col, "category": category.title()}
                    )
                    categorized.add(col)

        # Add any uncategorized numeric columns
        for col in self._first_results_columns:
            if col not in categorized and col != "Date":
                chartable.append(
                    {"name": col, "display_name": col, "category": "Other"}
                )

        return chartable

    @property
    def template(self):
        """Render the results page template"""
        import json

        # Prepare data for JavaScript
        results_data_json = None
        if self._first_results_data is not None:
            results_data_json = json.dumps(self._first_results_data)

        return render_template(
            "results.html",
            first_results_table=self._first_results_table,
            success_percentage=self._success_percentage,
            gauge_chart_json=self._gauge_chart,
            net_worth_chart_json=self._net_worth_chart,
            chartable_columns=self._get_chartable_columns(),
            results_data_json=results_data_json,
        )
