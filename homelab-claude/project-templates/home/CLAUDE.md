# /workspace/home: Home Assistant control room

Home Assistant tools load only in this folder (via .mcp.json), so other projects don't pay for them.

- Read state with GetLiveContext before changing anything.
- Ask me before: locks, alarm, heating setpoints, anything that opens doors or windows.
- Automations live in Home Assistant itself. Write YAML here for review first, then apply in HA.
