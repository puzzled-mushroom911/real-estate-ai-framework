# Node/TypeScript Conventions

## MCP Server & Tools
- TypeScript for all MCP server code
- Build: `npx tsc` for compilation
- Dev: `ts-node-dev src/index.ts` for hot-reload development
- PascalCase for classes and interfaces, camelCase for methods/variables
- Use async/await over raw Promises
- Structured error responses with error codes

## Web Projects
- React + Vite + TypeScript for any frontend
- Tailwind CSS for styling
- React Router for navigation
- React Hook Form for forms
- PascalCase for components, camelCase for logic/utilities

## Shared Rules
- Use .env files for secrets (never commit)
- package.json for all dependencies (no global installs)
- ESLint + Prettier for code quality
- No hardcoded API keys or credentials
- Use path aliases (e.g., @/) for clean imports
