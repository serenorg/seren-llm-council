# seren-llm-council

A multi-model AI consensus service that reduces hallucinations through structured deliberation between five diverse language models.

> Inspired by [Andrej Karpathy's llm-council](https://github.com/karpathy/llm-council). This fork also replaces OpenRouter with [SerenAI's x402 micropayments Store](https://serendb.com/bestsellers) of API publishers, enabling composable pay-per-query access without API keys for AI agents.

## Overview

Individual LLMs hallucinate, miss edge cases, and have blind spots. `seren-llm-council` addresses this by running every query through a three-stage deliberation process:

1. **Parallel Opinions**: 5 models (Claude, GPT-5, Kimi K2, Gemini, Perplexity Sonar) independently answer
2. **Mutual Critique**: Each model reviews and critiques the others' responses
3. **Chairman Synthesis**: A coordinator model analyzes all opinions and critiques to produce a final answer

This architecture catches factual errors that any single model would miss, surfaces diverse perspectives, and provides higher-quality outputs for queries where accuracy matters more than speed.

**Why debate works:** Different models have different failure modes. Running them in parallel and forcing explicit critique exposes contradictions, highlights uncertain claims, and removes unsupported assertions—especially on factual questions, edge cases, and multi-step reasoning.

## When To Use This

This is not a replacement for single-model inference. It's ~15x slower and costs more. Use it when:

- **Critical decisions**: Your AI agent needs to make a high-stakes choice
- **Fact verification**: You need to validate information before acting on it
- **Complex reasoning**: The query requires nuanced analysis that benefits from multiple approaches
- **Catching hallucinations**: You've been burned by confidently-wrong single-model outputs

Think of it as the difference between asking one person vs. convening an expert panel.

## Usage

### Production API

```bash
curl -X POST https://llm-council.serendb.com/v1/council/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the failure modes of RAG systems in production?",
    "chairman": "claude-opus-4.5"
  }'
```

Response includes:
- All 5 initial opinions
- Cross-model critiques highlighting disagreements
- Final synthesized answer with cited reasoning

### Via x402 MCP (for AI Agents)

AI agents using Claude Code, Cursor, or other MCP-enabled tools can query the council directly through the x402 MCP server.

**1. Install the x402 MCP server:**

```bash
npm install -g @anthropic/mcp-x402
```

**2. Add to your MCP config** (`~/.claude/claude_desktop_config.json` or IDE settings):

```json
{
  "mcpServers": {
    "x402": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-x402"],
      "env": {
        "X402_WALLET_PRIVATE_KEY": "your-wallet-private-key"
      }
    }
  }
}
```

**3. Query the council via MCP tools:**

```
Publisher ID: 081fc577-2cd9-425d-adf5-675af76e0b7a

Tool: mcp__x402__pay_for_query
Parameters:
  publisher_id: "081fc577-2cd9-425d-adf5-675af76e0b7a"
  request:
    method: "POST"
    path: "/v1/council/query"
    body:
      query: "Your question here"
      chairman: "claude-opus-4.5"  # optional
```

The MCP handles payment automatically from your prepaid balance.

### Local Development

```bash
git clone https://github.com/serenorg/seren-llm-council.git
cd seren-llm-council
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your x402 publisher IDs

# Run
uvicorn backend.main:app --reload --port 8000
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────┐
│  User Query                                     │
└──────────────────┬──────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      │  Stage 1: Parallel      │
      │  Opinion Generation     │
      └────────────┬────────────┘
                   │
    ┌──────┬───────┼───────┬──────┐
    │      │       │       │      │
┌───▼──┐ ┌─▼───┐ ┌─▼───┐ ┌─▼──┐ ┌─▼────┐
│Claude│ │GPT-5│ │Kimi │ │Gem │ │Sonar │
└───┬──┘ └──┬──┘ └──┬──┘ └──┬─┘ └──┬───┘
    │       │       │       │      │
    └───────┴───────┼───────┴──────┘
                    │
       ┌────────────▼────────────┐
       │  Stage 2: Critique      │
       │  Each model reviews     │
       │  all other responses    │
       └────────────┬────────────┘
                    │
       ┌────────────▼────────────┐
       │  Stage 3: Chairman      │
       │  Synthesizes final      │
       │  answer with sources    │
       └─────────────────────────┘
```

### Technical Stack

- **FastAPI** backend with async request handling
- **Parallel API calls** to 5 different LLM providers via x402
- **Structured prompting** ensures models focus on critiquing logic, not style
- **Deterministic synthesis** - Chairman cites which models contributed to final answer

### Repo Layout

```
seren-llm-council/
├── backend/
│   ├── config.py       # Council roster, publisher IDs, defaults
│   ├── council.py      # 3-stage orchestration logic
│   ├── main.py         # FastAPI routes
│   ├── models.py       # Pydantic request/response models
│   └── x402_client.py  # x402 gateway communication
├── api/
│   └── index.py        # Vercel serverless entry point
├── tests/              # Pytest test suite
├── .env.example
└── pyproject.toml
```

## Pricing

**$0.75 flat fee per query.**

- Predictable cost: no token counting
- Covers ~12 underlying API calls (opinions + critiques + synthesis)
- Simple billing for agents that need to budget

## Why Not Just Use Mixture-of-Agents?

MoA is great for aggregating similar models. This council differs because it:

- Uses **architecturally different** models (different training, strengths, weaknesses)
- Has an **explicit critique phase** that forces models to challenge each other
- Provides **transparent reasoning** - you see all opinions, not just the aggregate
- Is **debuggable** - when the answer is wrong, you can trace which model led it astray

## Building Your Own

This service itself consumes 5 other x402-enabled AI services. **Fork this repo** to build your own composable services:

- Ensemble different model combinations for your domain
- Add specialized models (code, math, legal)
- Create multi-stage pipelines (research → analysis → summary)
- Chain multiple councils together for iterative refinement

Because each upstream model is an x402 publisher, you can swap, version, or independently operate any component.

## Payment Infrastructure

This service uses x402 for micropayments between services. Think of it as HTTP-native micropayments—infrastructure that enables pay-per-use AI without vendor accounts. It's a payment primitive for composable services, not a protocol ideology.

If you want to run locally with direct API keys instead, modify `backend/x402_client.py` to call providers directly.

## License

MIT License - fork it, modify it, sell it, whatever. If you build something interesting, open an issue.

## Contributing

Issues and PRs welcome. Particularly interested in:

- New model integrations
- Improved critique prompts
- Alternative chairman synthesis strategies
- Performance optimizations

---

## Meta: This README Was Written by the Council

This README was generated by querying the seren-llm-council itself. Cost: **$0.75**. Time: 115 seconds.

Each model produced a draft README, critiqued the others, and the Chairman synthesized the final version.

**Council Rankings (Stage 2 Critique Results):**

| Critic | 1st    | 2nd    | 3rd    | 4th    | 5th   |
| ------ | ------ | ------ | ------ | ------ | ----- |
| Claude | Claude | GPT-5  | Gemini | Kimi   | Sonar |
| GPT-5  | Claude | GPT-5  | Kimi   | Gemini | Sonar |
| Kimi   | Claude | GPT-5  | Kimi   | Gemini | Sonar |
| Gemini | GPT-5  | Claude | Gemini | Kimi   | Sonar |
| Sonar  | Claude | GPT-5  | Kimi   | Gemini | Sonar |

**Consensus:** Claude's draft won 4-1. Key feedback from critics:

- Leads with engineering value, not payments
- "When To Use This" section addresses skeptics directly
- "Why Not MoA?" preemptively answers HN objections
- x402 framed as infrastructure, not ideology

---

**Engineering > Marketing.** This is a tool, not a movement. Use it if it solves your problem.
