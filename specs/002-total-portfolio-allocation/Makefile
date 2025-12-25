# Total Portfolio Allocation Strategy - Feature-Specific Commands
#
# Usage:
#   cd specs/002-total-portfolio-allocation
#   make profile        # Profile allocation performance
#   make test           # Run feature-specific tests
#   make coverage       # Run tests with coverage for this feature

WORKSPACE := $(shell cd ../.. && pwd)
SPEC_DIR := $(shell pwd)

.PHONY: profile test coverage help

help:
	@echo "Total Portfolio Allocation Strategy - Available Commands:"
	@echo ""
	@echo "  make profile    - Profile allocation performance (generates profiling.prof)"
	@echo "  make test       - Run feature-specific tests"
	@echo "  make coverage   - Run tests with coverage for allocation, portfolio, user modules"
	@echo "  make help       - Show this help message"
	@echo ""
	@echo "Results:"
	@echo "  - profiling.prof           - cProfile output"
	@echo "  - profiling_results.md     - Performance analysis"
	@echo ""

profile:
	@echo "Profiling total portfolio allocation strategy..."
	@cd $(WORKSPACE) && python -m cProfile -o $(SPEC_DIR)/profiling.prof $(SPEC_DIR)/profiling.py
	@echo ""
	@echo "✓ Profile saved to: $(SPEC_DIR)/profiling.prof"
	@echo ""
	@echo "To view interactively:"
	@echo "  cd $(SPEC_DIR) && snakeviz profiling.prof"
	@echo ""
	@echo "To view text summary:"
	@echo "  cd $(SPEC_DIR) && python -c \"import pstats; from pstats import SortKey; p = pstats.Stats('profiling.prof'); p.sort_stats(SortKey.CUMULATIVE).print_stats(20)\""

test:
	@echo "Running total portfolio allocation tests..."
	@cd $(WORKSPACE) && pytest \
		tests/models/controllers/test_allocation.py::TestTotalPortfolioStrategy \
		tests/models/config/test_portfolio.py \
		tests/models/test_config.py::test_total_portfolio_strategy_config_loading \
		tests/models/test_config.py::test_total_portfolio_strategy_requires_age_based_social_security \
		tests/models/test_config.py::test_total_portfolio_strategy_requires_age_based_or_cashout_pension \
		tests/models/test_config.py::test_total_portfolio_strategy_allows_age_based_strategies \
		tests/models/test_config.py::test_total_portfolio_strategy_allows_cashout_pension \
		-v

coverage:
	@echo "Running total portfolio allocation tests with coverage..."
	@cd $(WORKSPACE) && pytest \
		tests/models/controllers/test_allocation.py::TestTotalPortfolioStrategy \
		tests/models/config/test_portfolio.py \
		tests/models/test_config.py::test_total_portfolio_strategy_config_loading \
		tests/models/test_config.py::test_total_portfolio_strategy_requires_age_based_social_security \
		tests/models/test_config.py::test_total_portfolio_strategy_requires_age_based_or_cashout_pension \
		tests/models/test_config.py::test_total_portfolio_strategy_allows_age_based_strategies \
		tests/models/test_config.py::test_total_portfolio_strategy_allows_cashout_pension \
		--cov=app.models.controllers.allocation \
		--cov=app.models.config.portfolio \
		--cov=app.models.config.user \
		--cov-report=term-missing \
		--cov-report=html
	@echo ""
	@echo "✓ Coverage report: $(WORKSPACE)/htmlcov/index.html"

