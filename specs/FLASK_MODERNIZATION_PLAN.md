# Flask Web Interface Modernization Plan

## Overview

Modernize the LifeFinances Flask web interface with a professional, dark-themed UI that matches modern financial planning applications. The modernization will use Bootstrap 5, custom CSS for dark blue theming, and leverage the Pydantic metadata from the config models to auto-generate forms.

## Current State

**Existing Flask App:**
- Bootstrap 3 (outdated)
- Simple two-column layout (config editor left, results right)
- Raw YAML text editor for configuration
- Basic table display for simulation results
- No navigation or multi-page structure
- Light theme with gray backgrounds

**Files:**
- `app/templates/index.html` - Single page template
- `app/routes/index.py` - Single page route
- `app/static/` - Currently empty (no custom CSS/JS)

## Modernization Goals

1. **Modern UI Framework** - Upgrade to Bootstrap 5
2. **Dark Blue Theme** - Professional night-mode color scheme
3. **Multi-Page Structure** - Dashboard, Config, Run, Results pages
4. **Form-Based Config** - Auto-generated forms from Pydantic metadata
5. **Better Visualization** - Charts and enhanced result displays
6. **Responsive Design** - Mobile-friendly layout
7. **Headless Testing** - Automated tests for all Flask routes and templates

## Phase Plan

### Phase F1: Foundation & Theme System
**Goal:** Establish Bootstrap 5 and dark blue theme

**Tasks:**
1. Upgrade to Bootstrap 5
2. Create custom CSS with dark blue color palette
3. Create base template with navigation
4. Add theme CSS variables
5. Set up static file structure

**Deliverables:**
- `app/static/css/theme.css` - Dark blue theme
- `app/templates/base.html` - Base template with nav
- Updated `app/templates/index.html` using new theme

**Testing:**
- Visual inspection of theme
- Verify static files served correctly

### Phase F2: Multi-Page Navigation
**Goal:** Create multi-page structure with navigation

**Tasks:**
1. Create navigation bar component
2. Create separate pages: Dashboard, Config, Run, Results
3. Add Flask routes for each page
4. Implement page navigation
5. Add breadcrumbs/active states

**Deliverables:**
- `app/templates/dashboard.html` - Homepage
- `app/templates/config.html` - Config editor
- `app/templates/run.html` - Run simulation page
- `app/templates/results.html` - Results viewer
- `app/routes/dashboard.py`, `app/routes/config.py`, etc.

**Testing:**
- Headless tests for all routes (pytest-flask)
- Verify navigation links work
- Test page rendering

### Phase F3: Metadata-Driven Form Builder
**Goal:** Auto-generate config forms from Pydantic metadata

**Tasks:**
1. Create form generator that reads Pydantic Field metadata
2. Generate HTML forms with proper input types
3. Add client-side validation
4. Handle nested models (Portfolio, Social Security, etc.)
5. Replace YAML editor with form-based interface

**Deliverables:**
- `app/forms/generator.py` - Form generation from metadata
- `app/templates/components/form_field.html` - Reusable field template
- Updated config page with generated forms

**Testing:**
- Unit tests for form generator
- Test form submission and validation
- Test nested model handling

### Phase F4: Enhanced Results Visualization
**Goal:** Improve results display with charts and tables

**Tasks:**
1. Integrate Chart.js or Plotly for interactive charts
2. Create success rate visualization
3. Add multiple trial comparison
4. Improve table formatting
5. Add export functionality (CSV, PDF)

**Deliverables:**
- Enhanced results templates with charts
- JavaScript for interactive visualizations
- Export functionality

**Testing:**
- Test chart rendering
- Test data accuracy in visualizations
- Test export functionality

### Phase F5: Dashboard & Quick Actions
**Goal:** Create engaging homepage with stats and quick actions

**Tasks:**
1. Design dashboard with key metrics
2. Add recent simulations history
3. Create quick action cards
4. Add success rate trends
5. Implement session management for configs

**Deliverables:**
- Complete dashboard page
- Session/state management
- Quick action functionality

**Testing:**
- Test dashboard renders correctly
- Test quick actions navigate properly
- Test session persistence

### Phase F6: Advanced Features & Polish
**Goal:** Add professional finishing touches

**Tasks:**
1. Add loading spinners for simulations
2. Implement error handling and user feedback
3. Add help tooltips throughout
4. Optimize performance
5. Add keyboard shortcuts
6. Mobile responsive refinements

**Deliverables:**
- Loading states and animations
- Error handling
- Performance optimizations
- Mobile responsiveness

**Testing:**
- Cross-browser testing
- Mobile responsive testing
- Performance testing
- Accessibility testing

## Color Palette (Dark Blue Theme)

Based on the Qt GUI theme, adapted for web:

**Primary Colors:**
- Primary: `#1E3A8A` (Dark Blue)
- Primary Light: `#3B82F6` (Bright Blue for hover)
- Primary Container: `#0F1F47` (Very Dark Blue)

**Background:**
- Background: `#0F172A` (Almost black with blue tint)
- Surface: `#1E293B` (Dark slate)
- Surface Variant: `#334155` (Medium slate)

**Text:**
- On Background: `#F1F5F9` (Off-white)
- On Surface: `#E2E8F0` (Light gray)
- Muted: `#94A3B8` (Gray)

**Accent Colors:**
- Success: `#10B981` (Green)
- Warning: `#F59E0B` (Amber)
- Error: `#EF4444` (Red)
- Info: `#3B82F6` (Blue)

## Technology Stack

**Backend:**
- Flask 3.0.0 (existing)
- Jinja2 templates
- Pydantic for config validation

**Frontend:**
- Bootstrap 5.3
- Custom CSS for dark theme
- Chart.js or Plotly for visualizations
- Vanilla JavaScript (minimal dependencies)

**Testing:**
- pytest-flask for route testing
- Selenium or Playwright for headless browser tests
- Coverage reports

## Testing Strategy

**Unit Tests:**
- Form generator logic
- Route handlers
- Template rendering

**Integration Tests:**
- Full page workflows (create config → run simulation → view results)
- Form submission and validation
- Navigation flows

**Headless Browser Tests:**
- Visual regression testing
- JavaScript functionality
- Responsive layout testing

**Test Coverage Goal:** 80%+ for Flask routes and forms

## Migration Path

1. **Phase F1-F2** can be done without breaking existing functionality
2. **Phase F3** replaces YAML editor - will be the major breaking change
3. Keep YAML editor as "Advanced" option for power users
4. Add feature flags to gradually roll out changes

## Success Metrics

- **Performance:** Page load < 2 seconds
- **Accessibility:** WCAG 2.1 AA compliance
- **Mobile:** Fully functional on mobile devices
- **Test Coverage:** 80%+ for new code
- **User Experience:** Professional, modern appearance matching native desktop apps

## Notes

- All documentation goes in `specs/` directory (not root)
- Reuse metadata from config.py (already has UI metadata)
- Maintain compatibility with existing config files
- No Qt dependencies
- Focus on web-native solutions
