# Quantum MCP Relayer

> Add quantum computing to your AI apps in 5 minutes

Quantum-as-a-Service API exposing quantum algorithms as **MCP tools** for Claude and other AI assistants. Developers can add quantum computing capabilities without any quantum expertise.

## Tools

| Tool | What it does | Advantage |
|------|-------------|-----------|
| `quantum_portfolio_optimizer` | Optimize crypto/stock portfolios | 2-3x better Sharpe ratios |
| `quantum_route_optimizer` | Shortest route through locations (TSP) | 20-40% shorter routes |
| `quantum_meeting_scheduler` | Schedule meetings with constraints | 90% vs 60% satisfaction |

## Quick Start

### As MCP Server (for Claude Desktop)

```json
{
  "mcpServers": {
    "quantum": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/quantumproject"
    }
  }
}
```

### As REST API

```bash
pip install -e .
uvicorn src.api.app:app --reload
```

### With Docker

```bash
docker compose up
```

## API Examples

```bash
# Portfolio optimization
curl -X POST http://localhost:8000/api/v1/portfolio/optimize \
  -H "Content-Type: application/json" \
  -d '{"assets": [{"symbol": "BTC"}, {"symbol": "ETH"}, {"symbol": "SOL"}]}'

# Route optimization
curl -X POST http://localhost:8000/api/v1/route/optimize \
  -H "Content-Type: application/json" \
  -d '{"locations": [
    {"name": "Helsinki", "lat": 60.17, "lon": 24.94},
    {"name": "Tampere", "lat": 61.50, "lon": 23.79},
    {"name": "Turku", "lat": 60.45, "lon": 22.27}
  ]}'
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Architecture

```
User → Claude → MCP Server → QAOA Engine → Quantum Result → Claude → User
```

Uses QAOA (Quantum Approximate Optimization Algorithm) to solve optimization problems. Currently runs a classical simulator; connects to OriginQC's 72-qubit Wukong processor when configured.

## License

MIT
