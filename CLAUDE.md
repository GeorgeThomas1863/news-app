# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Important: You are the orchestrator. subagents execute. you should NOT build, verify, or code inline (if possible). your job is to plan, prioritize & coordinate the acitons of your subagents

Keep your replies extremely concise and focus on providing necessary information.

Put all pictures / screenshots you take with the mcp plugin in the "pics" subfolder, under the .claude folder in THIS project.

Do NOT commit anything to GitHub. The user will control all commits to GitHub. Do NOT edit or in any way change the user's Git history or interact with GitHub.

If you make a mistake or the user points out something is wrong or corrects you, please make note of it here, so you can avoid that mistake in the future.

# news-app

A Node.js/Express news aggregator web app.

## File Structure

```
news-app/
  app.js              # Entry point
  controllers/        # Route controllers
  html/               # HTML templates
  middleware/         # Express middleware
  models/             # Data models
  public/             # Static assets
  routes/             # Express routes
  src/                # Source files
  tests/              # Test files
  package.json
```

## Tech Stack

- Node.js
- Express
- (add more as the project grows)

## Key Commands

```bash
# Install dependencies
npm install

# Start the app
node app.js
```

## Dev Notes

- Project is in early stage — add notes here as development progresses.
