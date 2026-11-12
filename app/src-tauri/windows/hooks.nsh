; Hooks of the Reco NSIS installer (bundle > windows > nsis > installerHooks in tauri.conf.json).
; ASCII on purpose: makensis reads this file in the system codepage.
;
; Defect 5 of the real test (step 17, Fase 3, 2026-11-12): in silent (/S) and passive (/P) mode the Tauri template
; creates a Desktop shortcut without asking, because the finish page (where the checkbox lives) is skipped
; (installer.nsi: "Create desktop shortcut for silent and passive installers"). Reco wants only the Start Menu.
;
; - PREINSTALL remembers whether the Desktop shortcut already existed (made by hand, or by the checkbox of an earlier
;   install with a window); POSTINSTALL deletes it only if THIS silent or passive install created it.
; - The finish-page checkbox ("Create desktop shortcut") stays offered, but unchecked.
; - RECO_ATALHO_DESKTOP, when defined before this file, replaces the shortcut path: tools/test_nsis_atalho.py uses it
;   to prove the hooks in a temp folder, never on the real Desktop.

!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

Var RecoTinhaAtalhoDesktop

!macro RECO_CAMINHO_ATALHO_DESKTOP out
  !ifdef RECO_ATALHO_DESKTOP
    StrCpy ${out} "${RECO_ATALHO_DESKTOP}"
  !else
    StrCpy ${out} "$DESKTOP\${PRODUCTNAME}.lnk"
  !endif
!macroend

!macro NSIS_HOOK_PREINSTALL
  StrCpy $RecoTinhaAtalhoDesktop 0
  !insertmacro RECO_CAMINHO_ATALHO_DESKTOP $R9
  ${If} ${FileExists} "$R9"
    StrCpy $RecoTinhaAtalhoDesktop 1
  ${EndIf}
!macroend

!macro NSIS_HOOK_POSTINSTALL
  ${If} $RecoTinhaAtalhoDesktop = 0
    ${If} ${Silent}
    ${OrIf} $PassiveMode = 1
      !insertmacro RECO_CAMINHO_ATALHO_DESKTOP $R9
      Delete "$R9"
    ${EndIf}
  ${EndIf}
!macroend
