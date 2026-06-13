# Make Agent.md

Use the consitution.md as a base, but modify it according to best agent.md practices

The most effective AGENTS.md files follow a "README for machines" approach, focusing on executable instructions rather than vague explanations. Because this format is designed to be universally compatible with tools like Cursor, GitHub Copilot, and Windsurf, you can leverage several proven templates and skill patterns. 

## Recommended Template Structure

A standard, high-performing template typically covers six core areas:

* Persona & Tech Stack: Define the agent's role (e.g., "Senior React Developer") and specific versions (e.g., "Use MUI v3, not v4").
* Project Structure: Provide a "map" of the codebase using a tree command output so the agent knows where files live.
* Executable Commands: List exact scripts for building, linting, and testing (e.g., pnpm turbo run test).
* Code Style Patterns: Use "Do vs. Don't" code snippets instead of long prose. Examples of your specific patterns (like Redux primitives or styled components) can improve code reuse by 20%.
* Git & Workflow: Define how it should handle commits, branches, or PR descriptions.
* Boundaries (Guardrails): Explicitly state what it should never do (e.g., "Never modify .github/workflows" or "Ask before adding new heavy dependencies"). 

## Essential Skills for Writing the File

Writing for an AI agent is a specialized skill often called "Agent Engineering". Key principles include: 

* Positive & Negative Constraints: Use "Always" for mandatory patterns and "Never" for hard stops. If an agent repeats a mistake, add it as a "Don't" rule.
* Selective Loading (Agent Skills): For large projects, don't put everything in one file. Use a "Skills" folder at the root with specialized skill.md files (e.g., one for "Database Querying," one for "API Design") that the agent only loads when relevant.
* Passive vs. Active Context: Treat AGENTS.md at the root as "always-on" rules. For more obscure info (like ARCHITECTURE.md), use [AGENTS.md](https://agents.md/) to point the agent to them: "Read ARCHITECTURE.md before refactoring core modules".
* Iterative Refinement: The best AGENTS.md files are built through trial and error. When the agent produces "bad" code, update the file immediately with a "bad vs. corrected" example. [](https://maxcorbridge.substack.com/p/update-40-agent-skill-security-issues#:~:text=I%20first%20heard%20about%20them%20%28%20agent,agents%20across%20a%20variety%20of%20use%20cases.)