# 09: Prepped chase and party files

**What to build:** Prep workflow. The app lists JSON files in a chases folder and a parties folder in dropdowns. Loading a chase brings in its locations, hazards/barriers, and NPCs. Importing a party adds its investigators. "Save as" writes the current chase's prep content (locations, hazards, NPCs) to the chases folder under a name. Starting a blank chase stays possible. Files are human-readable and carry a version field.

**Blocked by:** 02 (Autosave, undo and event log), 05 (Barriers and track editing), 06 (Multi-participant setup)

**Status:** ready-for-agent

- [ ] The chases and parties dropdowns list the files in their folders
- [ ] Loading a chase plus importing a party gives a ready-to-establish chase
- [ ] Save as writes only prep content, never live state such as positions, round, or log
- [ ] Hand-edited files load correctly; invalid files show an error instead of crashing
- [ ] Test: a save-as/load round trip keeps locations, hazards, and NPCs
