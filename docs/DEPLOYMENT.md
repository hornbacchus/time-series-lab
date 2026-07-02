# TSL Deployment Runbook — locked-down work PC (no admin rights)

The bundle (`TSL_Install_<commit>.zip` + `.sha256` sidecar) is produced by
`tools\build_pack.ps1` on a build machine and is only distributable when the
packed-runtime verification gate (`tools\verify_pack.ps1`, 7 sub-checks) is
GREEN. `VERSION.txt` at the bundle root records the commit / build date /
python version — the artifact-to-validated-lineage traceability record.

Everything below is per-user: `%LOCALAPPDATA%\TimeSeriesLab\` files + one
HKCU registry value. **No admin rights are needed at any step.**

## Install steps

1. **Transfer** the ZIP to the target machine (email/share/USB — assume it
   arrives zone-flagged). Optionally verify the SHA-256 against the sidecar:
   `Get-FileHash TSL_Install_<commit>.zip -Algorithm SHA256`.
2. **UNBLOCK THE ZIP FIRST — before extracting.** Right-click the ZIP →
   Properties → General → tick **Unblock** → OK. *Why first:* extraction
   propagates the Mark-of-the-Web (Zone.Identifier) from the container to
   every extracted file; modern Excel **hard-blocks zone-flagged XLLs** —
   silently or with a policy banner. Unblocking the one container beats
   unblocking hundreds of files. (`install.ps1` also runs a defensive
   `Unblock-File` over the installed tree, but do not rely on it alone.)
3. **Extract locally** (e.g. `%USERPROFILE%\Downloads\TSL_Install\`) — not
   onto a network share and not into a OneDrive-synced folder.
4. **Run the installer** from the extracted folder:

   ```
   powershell -ExecutionPolicy Bypass -File .\install.ps1
   ```

   `-ExecutionPolicy Bypass` is process-scoped — it overrides the machine
   policy for this one invocation without changing anything (a supported
   precedence rule, not a hack). `TSL.Installer.exe` (same folder) is the
   GUI alternative; `install.ps1` is the primary path here because it prints
   an honest, state-aware epilogue and unblocks the installed tree.
5. **Read the epilogue.** It reports install outcome × registration outcome
   honestly; on a first install it prints the Excel registration steps
   (File → Options → Add-ins → Manage: Excel Add-ins → Go… → tick →
   restart). A failure is never printed green.

## Symptom table

| Symptom | Likely cause | Action |
|---|---|---|
| Add-in listed/ticked but no "Time Series Lab" tab, no error | MotW on the XLL/DLLs (skipped step 2), or add-in policy | `Unblock-File -Path "$env:LOCALAPPDATA\TimeSeriesLab\addin\*"` then restart Excel; if still absent, check File → Options → Trust Center → Add-ins for "require signed add-ins" |
| Excel shows a "blocked add-in / signed add-ins required" banner | **GPO: signed-only XLL policy — the one hard-stop class** | STOP. Do not improvise (self-signing / policy edits). Surface to the maintainers — the bundle needs a signing story |
| Tab appears; first run fails with "engine failed to start" | EDR blocking `python.exe` spawn from `%LOCALAPPDATA%`, or runtime missing | Check `%LOCALAPPDATA%\TimeSeriesLab\logs\tsl_*.log`; if EDR-on-spawn, surface to the maintainers (config-override escalation, DP4) |
| Workbook-input techniques fail (Bond Yield Forecast etc.) | Runtime integrity (openpyxl missing = a stale pre-fix runtime) | Re-run `install.ps1` — the VERSION.txt marker forces a runtime refresh |
| `install.ps1` won't run at all | Execution policy blocks even Bypass (rare hardening) | Use `TSL.Installer.exe` instead; if that is SmartScreen-blocked, unblock the exe (Properties → Unblock) |

## Uninstall

Run `install.ps1`'s GUI sibling `TSL.Installer.exe` → Uninstall, or manually:
delete the `OPEN<n>` value containing `TimeSeriesLab-AddIn` under
`HKCU\Software\Microsoft\Office\16.0\Excel\Options`, then delete
`%LOCALAPPDATA%\TimeSeriesLab\`.
