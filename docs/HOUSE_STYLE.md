# House style: Time Series Lab and Global Macro Charts

Ratified by Matthew Hornbach on 2026-09-30. It governs every user-facing message, dialog and About box in Time Series Lab. Global Macro Charts follows the same rules in its own repository.

## About box

Caption "About Time Series Lab". One full-width OK button, no icon. The lines, in order:

    Time Series Lab

    Build <describe> / <yyyy-MM-dd HH:mm>
    Created by Matthew Hornbach
    © 2026 All Rights Reserved

    Macro-finance time-series analysis add-in
    for Microsoft Excel 365 Desktop (Windows)

    Also by Matthew Hornbach: Global Macro Charts

Then the diagnostics block, one "Label: value" line each, in three groups separated by a blank line: Engine version, Engine status and Technique library; Platform, Runtime and Compute; Layout, Settings and Logs. There is no version-number line. "©" is the one permitted non-ASCII character. Global Macro Charts' About box carries the mirror line, "Also by Matthew Hornbach: Time Series Lab".

## Captions

- "Time Series Lab" for a plain message.
- "Time Series Lab - <Area>" when the action has one, with the area written exactly as its ribbon button is labelled. Every question carries an area, and so does every message from an action that has one.
- Every error appends " - Error".

## Look

- No icon. Severity shows only in the caption.
- A message has one full-width OK. Enter, Esc and the close box all dismiss it.
- A question has word-labelled buttons stacked full width, the first one the default, and a dedicated Cancel always last. Never Yes/No.
- When the text explains the buttons, it uses one "<Label> = <meaning>" line each.
- Free text goes through the house text box (OK and Cancel), never a native input box.
- Geometry follows Global Macro Charts' frmPrompt: a form 280 pt wide (about 373 logical pixels at 100% scaling); a prompt label 256 pt wide with word wrap; buttons 232 x 24 pt, stacked at 30 pt steps. The height grows with the text, and the form opens centred on the Excel window.
- The one native dialog Time Series Lab opens on purpose is Excel's Function Arguments dialog, from Insert in Help > UDF Formula Guide. The dialog check allows that one call and no other.
- Enforced by tools/check_house_dialogs.py, a gate step in ci_gate_local and in CI.

## Text

These rules apply to dialogs and to task-pane messages.

- Plain ASCII; sentence case; full stops; no exclamation marks, contractions or first person.
- One blank line between blocks; a path or value on its own line, indented four spaces.
- Command names exactly as the ribbon writes them. A route starts at the ribbon group and names each step, e.g. "Bespoke > Bond Yield Forecast > Open Input Template".
- US spelling; "e.g."; "X-axis"; straight quotes.
- These rules also cover the task pane's labels, tooltips and badges. Section headers in capitals, such as INPUT WORKBOOK, are a visual style and stay as they are.

## Errors and refusals

- Say what happened, then the state it left ("Nothing was changed."), then what to do when the user can act.
- Name the file or folder when the problem concerns one.
- Raw Excel or Python error text appears only after a plain sentence, never alone.
- Refusals name what is supported.
- Nothing fails silently.
- Where a colleague should get help: "Tell Matthew Hornbach."

## Branding

- The product names "Time Series Lab" and "Global Macro Charts" in all user text.
- The author as "Matthew Hornbach" everywhere: About boxes, guides and install notes, and in file properties the File description, "Time Series Lab, created by Matthew Hornbach", since the version resource has no author field.

## Installer and update messages

They run outside Excel, so they use a real Information or Critical icon, always state what changed, and may use numbered steps.
