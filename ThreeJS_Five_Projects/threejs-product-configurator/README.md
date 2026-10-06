# Product Studio

Configure a procedural desk lamp. Orbit, change its finish, adjust its height, and export the configuration.

## Run
Requires Node.js 22 or newer. Run `npm start`, then open http://localhost:5173. No npm install is needed. Three.js 0.186.1 loads from jsDelivr, so internet access is required. Do not open index.html directly.

## Controls
Drag to orbit, scroll or pinch to zoom. Tap objects for labels. Reset camera restores the initial view; Save image exports a PNG. Project controls are in the sidebar.

## Verification
Run `npm test`. Tests cover source syntax and local HTTP delivery. Domain tests cover layout or parser behavior when applicable. Automated checks do not replace WebGL and touch-device QA.

## Deployment
Upload index.html, style.css and browser JS modules to any static host. Keep the import-map CDN accessible. The local server is for development only.

## Provenance
Created as a new AI-assisted portfolio example in this session, not historical client work. Commits reflect actual work and use an explicit Codex author identity. No backdated commits, user credentials, or client assets are included.

## Limitations
Procedural assets, no backend, no production guarantees. Review and extend before commercial use.
