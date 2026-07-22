# AgentKit — Reasoning and Tool-Use Benchmark

A reproducible benchmark of the LangGraph reasoning agent, assessing its ability to correctly invoke tools and synthesize answers based on user intent. Reproducible:
`python eval/run_agent_eval.py`

## Setup
The benchmark uses an LLM-as-a-judge (Claude Sonnet 4.6) to evaluate the agent's workflow on 4 core queries that require multi-tool coordination. The queries test:
- Financial anomaly detection
- People headcount forecasting
- Revenue forecasting
- Multi-domain executive summary

## Results (N=4)
| Metric | Score |
|--------|-------|
| Tool Selection Accuracy | 100% |
| Final Answer Groundedness | 100% |
| Overall Success Rate | **100.0%** (4/4) |

**Headline:** the AgentKit LangGraph agent successfully orchestrates cross-domain tools (Finance, People) and correctly grounds its synthesized reports 100% of the time on the core benchmark set.

*Note: Tested using Anthropic Claude 3.5 Sonnet / 4.6 as the underlying reasoning engine.*
