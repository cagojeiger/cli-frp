# FRP Python Wrapper

A Python wrapper for FRP (Fast Reverse Proxy) that simplifies tunneling and path-based routing.

## Features

- **Simple API**: Easy-to-use Python interface with familiar exception handling
- **Path-based Routing**: Direct integration with FRP's native `locations` feature
- **No External Dependencies**: Uses FRP's built-in capabilities, no Nginx required
- **Context Managers**: Automatic resource cleanup
- **Clean Architecture**: Object-oriented design with Pydantic models

## Quick Start

```python
from frp_wrapper import create_tunnel

# Expose local service to the internet
url = create_tunnel("example.com", 3000, "/myapp")
print(f"🔗 Your app is live at: {url}")
# https://example.com/myapp/
```

## Installation

```bash
pip install frp-wrapper
```

**Requirements:**
- Python 3.8+
- FRP binary (automatically downloaded or manually installed)

## Architecture

```
User Request → FRP Server (with locations) → Your Local Service
```

Uses FRP's native `locations` parameter for clean, direct path routing:

```toml
[[proxies]]
name = "myapp"
type = "http"
localPort = 3000
customDomains = ["example.com"]
locations = ["/myapp"]  # Native FRP feature!
```

## Documentation

- 📖 [Quick Start Guide](docs/00-quickstart.md) - Get running in 5 minutes
- 🔧 [Installation](docs/01-installation.md) - Detailed setup instructions
- 🏗️ [Project Overview](docs/spec/00-overview.md) - Core concepts and architecture
- 🎯 [Architecture Guide](docs/architecture/domain-model.md) - Object-oriented design with Pydantic

## Project Status

**✅ Checkpoint 5 Complete - Context Manager Implementation**

This project has been implemented with:
- Object-oriented design with Pydantic models
- Test-driven development (95%+ coverage achieved)
- Protocol pattern for clean architecture
- Native FRP `locations` support
- Context managers for automatic resource cleanup
- Async support (AsyncProcessManager)
- Tunnel groups for batch management

See [CLAUDE.md](CLAUDE.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

We welcome contributions! Please see our [development roadmap](plan/) for planned features and checkpoints.
