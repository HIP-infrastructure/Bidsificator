# Architecture & Design

This section contains technical documentation about Bidsificator's architecture and design decisions.

## Architecture Documents

- [**Schema-Driven BIDS**](schema-driven-bids.md) - How Bidsificator implements the BIDS schema dynamically

## Coming Soon

- **MVC Pattern** - Model-View-Controller architecture overview
- **Converter System** - File format converter registry and priority system
- **Metadata Extraction** - Schema-driven metadata generation
- **Worker Processes** - Background processing architecture
- **Database Schema** - Data models and relationships

## Key Design Principles

### 1. Schema-Driven Everything
- No hardcoded BIDS rules
- All validation and generation driven by official BIDS schema
- Automatically adapts to schema updates

### 2. Separation of Concerns
- **Models** - Data representation
- **Views** - PyQt6 GUI components
- **Controllers** - Business logic coordination
- **Services** - Reusable business logic
- **Workers** - Background processing

### 3. Extensibility
- Plugin-based converter system
- Configurable validation rules
- Modular service architecture
- Site-specific configuration support

### 4. BIDS Compliance
- Official BIDS specification (1.10.0)
- Schema version 0.11.3
- Passes official BIDS validator
- Follows BIDS best practices

## Component Overview

```
bidsificator/
├── controllers/    # Business logic coordination
├── models/         # Data models
├── ui/             # PyQt6 views
├── services/       # Reusable services
├── workers/        # Background processes
├── core/           # Core BIDS functionality
│   ├── schema/     # BIDS schema management
│   └── converters/ # File format converters
└── config/         # Configuration files
```

## For Developers

- Read [CLAUDE.md](../../CLAUDE.md) for AI-assisted development instructions
- Check [tests/](../../tests/) for code examples and usage patterns
- Report issues or contribute on GitHub

---

[← Back to Documentation Hub](../README.md)
