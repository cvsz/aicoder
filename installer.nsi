; ============================================================================
; ZAI Coder CLI — Windows Installer (NSIS)
; Creates a proper Windows installer with:
;   - Start Menu shortcuts
;   - Add to PATH option
;   - Uninstaller
;   - License agreement
; ============================================================================

!define PRODUCT_NAME "ZAI Coder"
!define PRODUCT_VERSION "1.23.0"
!define PRODUCT_PUBLISHER "ZeaZDev"
!define PRODUCT_WEB_SITE "https://github.com/cvsz/zaicoder"
!define PRODUCT_EXE "zai-coder.exe"
!define PRODUCT_DIR_REGKEY "Software\ZeaZDev\ZAI Coder"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

; MUI (Modern UI)
!include "MUI2.nsh"
!include "EnvVarUpdate.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Installer pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${PRODUCT_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Run ZAI Coder (opens help)"
!define MUI_FINISHPAGE_RUN_PARAMETERS "--help"
!define MUI_FINISHPAGE_LINK "Visit GitHub repository"
!define MUI_FINISHPAGE_LINK_LOCATION "${PRODUCT_WEB_SITE}"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

; Installer attributes
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "dist\ZAI-Coder-${PRODUCT_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES64\ZAI Coder"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
RequestExecutionLevel admin
ShowInstDetails show
ShowUnInstDetails show

; Version info
VIProductVersion "${PRODUCT_VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "${PRODUCT_NAME} Installer"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "LegalCopyright" "Copyright (c) 2026 ${PRODUCT_PUBLISHER}"

; ============================================================================
; Sections
; ============================================================================

Section "Main Application" SecMain
    SectionIn RO

    SetOutPath "$INSTDIR"

    ; Copy executable
    File "dist\${PRODUCT_EXE}"

    ; Copy documentation
    File "README.md"
    File "LICENSE"
    File "CHANGELOG.md"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Registry entries
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${PRODUCT_EXE}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoRepair" 1

    ; Estimated size
    WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "EstimatedSize" 50000
SectionEnd

Section "Add to PATH" SecPath
    ; Add install directory to system PATH
    ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$INSTDIR"
SectionEnd

Section "Start Menu Shortcuts" SecShortcuts
    CreateDirectory "$SMPROGRAMS\ZAI Coder"
    CreateShortCut "$SMPROGRAMS\ZAI Coder\ZAI Coder.lnk" "$INSTDIR\${PRODUCT_EXE}" "--help"
    CreateShortCut "$SMPROGRAMS\ZAI Coder\ZAI Coder TUI.lnk" "$INSTDIR\${PRODUCT_EXE}" "--tui"
    CreateShortCut "$SMPROGRAMS\ZAI Coder\README.lnk" "$INSTDIR\README.md"
    CreateShortCut "$SMPROGRAMS\ZAI Coder\Uninstall.lnk" "$INSTDIR\uninstall.exe"
SectionEnd

; ============================================================================
; Descriptions
; ============================================================================

LangString DESC_SecMain ${LANG_ENGLISH} "ZAI Coder CLI standalone executable"
LangString DESC_SecPath ${LANG_ENGLISH} "Add ZAI Coder to system PATH so you can run it from any terminal"
LangString DESC_SecShortcuts ${LANG_ENGLISH} "Create Start Menu shortcuts"

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecPath} $(DESC_SecPath)
    !insertmacro MUI_DESCRIPTION_TEXT ${SecShortcuts} $(DESC_SecShortcuts)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ============================================================================
; Uninstaller
; ============================================================================

Section "Uninstall"
    ; Remove files
    Delete "$INSTDIR\${PRODUCT_EXE}"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\LICENSE"
    Delete "$INSTDIR\CHANGELOG.md"
    Delete "$INSTDIR\uninstall.exe"

    ; Remove shortcuts
    RMDir /r "$SMPROGRAMS\ZAI Coder"

    ; Remove from PATH
    ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$INSTDIR"

    ; Remove registry entries
    DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"

    ; Remove install directory
    RMDir "$INSTDIR"
SectionEnd
