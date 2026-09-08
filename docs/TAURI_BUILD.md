# Building with Tauri

## Prerequisites

- Rust 1.56+
- Node.js 12+
- Tauri CLI

## Development

```bash
cd desktop
npm install
npm run dev
```

## Building for Release

### Windows
```bash
cd desktop
cargo tauri build
```

### macOS
Requires signing certificate. Set in `tauri.conf.json`

### Linux
```bash
cd desktop
cargo tauri build
```

## Output

Built app will be in: `desktop/src-tauri/target/release/`

## Troubleshooting

- Frontend not loading? Run `npm run build` first
- Rust compilation errors? Update Rust: `rustup update`
- Window not appearing? Check `tauri.conf.json` configuration
