# Contributing to ALERTIX-AI

Thanks for your interest in improving ALERTIX-AI. This project is an open-source multi-hazard early-warning system for India, and contributions of all sizes are welcome.

## Ways to contribute

- Report a bug by opening an issue with clear reproduction steps.
- Improve documentation, including setup guides and inline comments.
- Add or refine hazard data connectors for sources such as USGS, IMD and NASA FIRMS.
- Improve the ML models or the SOS triage logic.
- Add tests that cover existing behaviour.

## Getting started

1. Fork the repository and clone your fork locally.
2. Copy .env.example to .env and fill in the required values.
3. Install the backend dependencies from the backend directory.
4. Install the frontend dependencies from the frontend directory.
5. Create a feature branch before making any changes.

## Branch naming

Use a short prefix that describes the change, for example feat/ for new features, fix/ for bug fixes, and docs/ for documentation only changes.

## Commit messages

This project follows Conventional Commits. Start the subject line with a type such as feat, fix, docs, chore, refactor or test, followed by a colon and a short description in the imperative mood.

## Pull requests

Before opening a pull request, please make sure that the project builds locally, that any new behaviour is covered by a test, and that documentation is updated where relevant. Describe what changed and why in the pull request body, and link any related issue.

## Code style

Python code should follow PEP 8. JavaScript and TypeScript code should match the existing formatting used in the frontend directory. Keep functions small and prefer clear names over comments where possible.

## Reporting security issues

Please do not open a public issue for security vulnerabilities. Contact the maintainer directly so the problem can be addressed before disclosure.

## License

By contributing you agree that your contributions will be licensed under the Apache License 2.0, the same license that covers this repository.
