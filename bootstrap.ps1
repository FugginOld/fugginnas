# bootstrap.ps1
# Pull global AI workflow config from FugginOld/ai-config into the current repo.
# Run from the target repo root.
#
# Default:    overwrite all managed files
# -FirstRun:  skip files that already exist
# -DryRun:    preview changes, no writes
# -SkipTools: skip npm/pip installs (file deploy only)
#
# Usage:
#   .\bootstrap.ps1
#   .\bootstrap.ps1 -FirstRun
#   .\bootstrap.ps1 -DryRun
#   .\bootstrap.ps1 -SkipTools
#   .\bootstrap.ps1 -Repo C:\path\to\repo
#   .\bootstrap.ps1 -Repo owner/repo

param(
    [string]$Repo,
    [switch]$FirstRun,
    [switch]$DryRun,
    [switch]$SkipTools
)

$ErrorActionPreference = "Stop"
$REPO = "FugginOld/ai-config"
$TMP  = ".ai-config-tmp"
$TARGET_REPO_TMP = Join-Path $env:TEMP "ai-config-bootstrap-target"

# ── OS detection ──────────────────────────────────────────────────────────────
$isWindowsFlag = $false
if ($null -ne (Get-Variable -Name IsWindows -Scope Global -ErrorAction SilentlyContinue)) {
    $isWindowsFlag = [bool]$IsWindows
}
$IsWin = $isWindowsFlag -or ($PSVersionTable.Platform -eq "Win32NT") -or ($env:OS -eq "Windows_NT")

function Get-HomeDir {
    if ($IsWin) { return $env:USERPROFILE } else { return $env:HOME }
}

$HOME_DIR        = Get-HomeDir
$VENV_DIR        = Join-Path $HOME_DIR ".venvs/mempalace"
$VENV_PYTHON     = if ($IsWin) { Join-Path $VENV_DIR "Scripts/python.exe" } else { Join-Path $VENV_DIR "bin/python" }
$CLAUDE_DIR      = Join-Path $HOME_DIR ".claude"
$CLAUDE_SETTINGS = Join-Path $CLAUDE_DIR "settings.json"
$SKILLS_DIR      = Join-Path $CLAUDE_DIR "skills"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-Done($msg) { Write-Host "   OK  $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "   --  $msg" -ForegroundColor Yellow }
function Write-Dry($msg)  { Write-Host "   DRY $msg" -ForegroundColor Magenta }
function Write-Warn($msg) { Write-Host "   !!  $msg" -ForegroundColor Red }

function Copy-Managed($src, $dst) {
    if (!(Test-Path $src)) { Write-Warn "Source missing: $src"; return }
    if ($DryRun) { Write-Dry "$src -> $dst"; return }
    $dstDir = Split-Path $dst -Parent
    if ($dstDir -and !(Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    if ((Test-Path $dst) -and $FirstRun) { Write-Skip "$dst (exists, -FirstRun)" }
    else { Copy-Item $src $dst -Force; Write-Done $dst }
}

function Invoke-Cmd($cmd, $desc) {
    if ($DryRun) { Write-Dry $desc; return }
    Write-Host "   .. $desc" -ForegroundColor DarkCyan
    Invoke-Expression $cmd
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { Write-Warn "Exit $LASTEXITCODE — $desc" }
}

function Test-Command($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Resolve-TargetRepoDir([string]$repoArg) {
    if ([string]::IsNullOrWhiteSpace($repoArg)) {
        return (Get-Location).Path
    }

    $repoArgTrim = $repoArg.Trim()
    if (Test-Path -LiteralPath $repoArgTrim) {
        return (Resolve-Path -LiteralPath $repoArgTrim).Path
    }

    if ($repoArgTrim -match '^[^/\s]+/[^/\s]+$') {
        if (!(Test-Command "gh")) { throw "gh CLI not found. Required for -Repo owner/name." }

        if (!(Test-Path $TARGET_REPO_TMP)) { New-Item -ItemType Directory -Path $TARGET_REPO_TMP -Force | Out-Null }
        $repoName = ($repoArgTrim -split '/')[1]
        $repoDir = Join-Path $TARGET_REPO_TMP $repoName

        if (Test-Path $repoDir) {
            Push-Location $repoDir
            try {
                git pull --quiet
            } finally {
                Pop-Location
            }
        } else {
            gh repo clone $repoArgTrim $repoDir -- --depth 1 --quiet
        }
        return $repoDir
    }

    throw "Invalid -Repo value '$repoArgTrim'. Use an existing local path or owner/repo."
}

# ── Merge JSON helper (shallow — merges top-level keys) ───────────────────────
function Merge-JsonFile($existing, $incoming) {
    # Returns merged hashtable: incoming keys overwrite matching top-level keys,
    # nested objects (env, permissions, hooks, mcpServers) are merged one level deep.
    $merged = @{}
    if (Test-Path $existing) {
        $base = Get-Content $existing -Raw | ConvertFrom-Json
        $base.PSObject.Properties | ForEach-Object { $merged[$_.Name] = $_.Value }
    }
    $inc = Get-Content $incoming -Raw | ConvertFrom-Json
    $inc.PSObject.Properties | ForEach-Object {
        $key = $_.Name
        if ($merged.ContainsKey($key) -and $merged[$key] -is [PSCustomObject]) {
            # Deep merge one level
            $sub = @{}
            $merged[$key].PSObject.Properties | ForEach-Object { $sub[$_.Name] = $_.Value }
            $_.Value.PSObject.Properties       | ForEach-Object { $sub[$_.Name] = $_.Value }
            $merged[$key] = [PSCustomObject]$sub
        } else {
            $merged[$key] = $_.Value
        }
    }
    return $merged
}

# ── CONTEXT.md interactive handler ───────────────────────────────────────────
function Invoke-ContextMd($src) {
    $dst = "CONTEXT.md"
    if (!(Test-Path $dst)) {
        Copy-Managed $src $dst
        Write-Host "   -> Edit CONTEXT.md with repo-specific details before first agent run." -ForegroundColor Yellow
        return
    }
    if ($DryRun) { Write-Dry "CONTEXT.md exists — would prompt for action"; return }
    Write-Host ""
    Write-Host "   CONTEXT.md already exists." -ForegroundColor Yellow
    Write-Host "   [1] Append new sections from template (safe merge)"
    Write-Host "   [2] Skip (keep existing)"
    Write-Host "   [3] Overwrite (replace with template)"
    $choice = Read-Host "   Choice [1/2/3]"
    switch ($choice) {
        "1" {
            $existing = Get-Content $dst -Raw
            $template = Get-Content $src -Raw
            # Append only the sections not already present (match by ## heading)
            $newSections = [regex]::Matches($template, '(?m)^## .+?(?=^## |\Z)', [System.Text.RegularExpressions.RegexOptions]::Singleline)
            $added = 0
            foreach ($section in $newSections) {
                $heading = [regex]::Match($section.Value, '^## .+').Value.Trim()
                if ($existing -notmatch [regex]::Escape($heading)) {
                    Add-Content $dst "`n$($section.Value.TrimEnd())"
                    $added++
                }
            }
            Write-Done "CONTEXT.md — appended $added new section(s)"
        }
        "3" { Copy-Item $src $dst -Force; Write-Done "CONTEXT.md overwritten" }
        default { Write-Skip "CONTEXT.md unchanged" }
    }
}

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
Write-Step "Checking prerequisites"
if (!(Test-Command "gh"))  { Write-Error "gh CLI not found. Install: https://cli.github.com" }
Write-Done "gh CLI"
if (!(Test-Command "node")) { Write-Warn "node not found — npm installs will be skipped" }
if (!(Test-Command "python3") -and !(Test-Command "python")) { Write-Warn "python not found — MemPalace install will be skipped" }

$TARGET_REPO_DIR = Resolve-TargetRepoDir $Repo
Write-Step "Target repository"
Write-Done $TARGET_REPO_DIR

# ── 2. Clone ai-config ────────────────────────────────────────────────────────
Write-Step "Cloning $REPO"
if (Test-Path $TMP) { Remove-Item $TMP -Recurse -Force }
if (!$DryRun) {
    gh repo clone $REPO $TMP -- --depth 1 --quiet
    Write-Done "Cloned to $TMP"
} else {
    Write-Dry "Would clone $REPO to $TMP"
}

# ── 3. Agent entry point files ────────────────────────────────────────────────
Push-Location $TARGET_REPO_DIR
try {
Write-Step "Deploying agent files"
Copy-Managed "$TMP/agents/AGENTS.md"               "AGENTS.md"
Copy-Managed "$TMP/agents/CLAUDE.md"               "CLAUDE.md"
Copy-Managed "$TMP/agents/copilot-instructions.md" ".github/copilot-instructions.md"

# ── 4. CONTEXT.md ─────────────────────────────────────────────────────────────
Write-Step "Checking CONTEXT.md"
Invoke-ContextMd "$TMP/CONTEXT.md"

# ── 5. VS Code MCP config (MemPalace — Copilot) ───────────────────────────────
Write-Step "Deploying .vscode/mcp.json (MemPalace)"
Copy-Managed "$TMP/memory/mempalace/vscode-mcp.json" ".vscode/mcp.json"
} finally {
    Pop-Location
}

# ── 6. Merge ~/.claude/settings.json ─────────────────────────────────────────
Write-Step "Merging ~/.claude/settings.json"
if (!$DryRun) {
    if (!(Test-Path $CLAUDE_DIR)) { New-Item -ItemType Directory -Path $CLAUDE_DIR -Force | Out-Null }
    # Merge context-mode security policy + claude-mem env settings
    $merged1 = Merge-JsonFile $CLAUDE_SETTINGS "$TMP/plugins/context-mode/claude-settings.json"
    $tmp1    = Join-Path $env:TEMP "settings_merge1.json"
    $merged1 | ConvertTo-Json -Depth 10 | Set-Content $tmp1
    $merged2 = Merge-JsonFile $tmp1 "$TMP/plugins/claude-mem/claude-settings-template.json"
    # Also merge MemPalace MCP + hooks
    $tmp2    = Join-Path $env:TEMP "settings_merge2.json"
    $merged2 | ConvertTo-Json -Depth 10 | Set-Content $tmp2
    $merged3 = Merge-JsonFile $tmp2 "$TMP/memory/mempalace/hooks/claude-code-settings.json"
    $merged3 | ConvertTo-Json -Depth 10 | Set-Content $CLAUDE_SETTINGS
    Write-Done $CLAUDE_SETTINGS
} else {
    Write-Dry "Would merge context-mode + claude-mem + MemPalace into $CLAUDE_SETTINGS"
}

# ── 7. Install/update context-mode (global npm) ───────────────────────────────
if (!$SkipTools) {
    Write-Step "context-mode (npm global)"
    if (Test-Command "npm") {
        Invoke-Cmd "npm install -g context-mode@latest --silent" "npm install -g context-mode@latest"
        Write-Done "context-mode installed"
    } else {
        Write-Skip "npm not found — install manually: npm install -g context-mode@latest"
    }
}

# ── 8. Install mattpocock skills (global) ────────────────────────────────────
Write-Step "Deploying skills to $SKILLS_DIR"
if (!$DryRun) {
    if (!(Test-Path $SKILLS_DIR)) { New-Item -ItemType Directory -Path $SKILLS_DIR -Force | Out-Null }
    $skillSrc = "$TMP/skills/mattpocock"
    Get-ChildItem $skillSrc -Directory | ForEach-Object {
        $skillName = $_.Name
        $destSkill = Join-Path $SKILLS_DIR $skillName
        if (!(Test-Path $destSkill)) { New-Item -ItemType Directory -Path $destSkill -Force | Out-Null }
        Copy-Item "$($_.FullName)/SKILL.md" "$destSkill/SKILL.md" -Force
        Write-Done "skill: $skillName"
    }
    # Attempt full install via npx for canonical versions
    if (!$SkipTools -and (Test-Command "npx")) {
        Write-Host "   .. Pulling canonical skills via npx" -ForegroundColor DarkCyan
        $skills = @("caveman","grill-me","grill-with-docs","write-a-prd","tdd","diagnose","write-a-skill","git-guardrails-claude-code")
        foreach ($s in $skills) {
            npx skills@latest add "mattpocock/skills/$s" -y -g 2>$null
        }
        Write-Done "npx skills install attempted (failures fall back to vendored stubs)"
    }
} else {
    Write-Dry "Would copy skills from $TMP/skills/mattpocock/ to $SKILLS_DIR"
}

# ── 9. Install MemPalace (venv) ───────────────────────────────────────────────
if (!$SkipTools) {
    Write-Step "MemPalace (Python venv: $VENV_DIR)"
    $pyCmd = if (Test-Command "python3") { "python3" } elseif (Test-Command "python") { "python" } else { $null }
    if ($pyCmd) {
        if (!(Test-Path $VENV_DIR)) {
            Invoke-Cmd "$pyCmd -m venv $VENV_DIR" "Creating venv at $VENV_DIR"
        } else {
            Write-Done "venv exists: $VENV_DIR"
        }
        if (!$DryRun) {
            if ($IsWin) {
                Invoke-Cmd "& `"$VENV_PYTHON`" -m pip install --upgrade mempalace --quiet" "pip install mempalace"
            } else {
                Invoke-Cmd "& $VENV_PYTHON -m pip install --upgrade mempalace --quiet" "pip install mempalace"
            }
            Write-Done "MemPalace installed"
            # Run init only if palace doesn't exist
            $palaceConfig = Join-Path $HOME_DIR ".mempalace/config.json"
            if (!(Test-Path $palaceConfig)) {
                Write-Host "   -> No palace found. Run: mempalace init ~/projects" -ForegroundColor Yellow
                Write-Host "   -> Then: mempalace mine ~/.claude/projects/ --mode convos" -ForegroundColor Yellow
            } else {
                Write-Done "Palace exists at ~/.mempalace/"
            }
        }
    } else {
        Write-Skip "python not found — install manually. See: memory/mempalace/INSTALL.md"
    }
}

# ── 10. claude-mem reminder ───────────────────────────────────────────────────
Write-Step "claude-mem"
Write-Host "   claude-mem must be installed from inside a Claude Code session:" -ForegroundColor Yellow
Write-Host "     /plugin marketplace add thedotmack/claude-mem" -ForegroundColor DarkCyan
Write-Host "     /plugin install claude-mem" -ForegroundColor DarkCyan
Write-Host "   Or run: npx claude-mem@latest install" -ForegroundColor DarkCyan

# ── 11. OpenClaw config ───────────────────────────────────────────────────────
Push-Location $TARGET_REPO_DIR
try {
    Write-Step "OpenClaw config"
    $openclawFiles = @(
        @{ Src = "$TMP/openclaw/OPENCLAW_CONTEXT.md";   Dst = ".claude/OPENCLAW_CONTEXT.md"              },
        @{ Src = "$TMP/openclaw/skill-map.md";           Dst = ".claude/skill-map.md"                     },
        @{ Src = "$TMP/openclaw/channel-map.md";         Dst = ".claude/channel-map.md"                   },
        @{ Src = "$TMP/openclaw/tdd.prompt.md";          Dst = ".claude/prompts/tdd.prompt.md"            },
        @{ Src = "$TMP/openclaw/diagnose.prompt.md";     Dst = ".claude/prompts/diagnose.prompt.md"       },
        @{ Src = "$TMP/openclaw/repo-review.prompt.md";  Dst = ".claude/prompts/repo-review.prompt.md"   }
    )
    foreach ($f in $openclawFiles) { Copy-Managed $f.Src $f.Dst }
} finally {
    Pop-Location
}

# ── 12. Cleanup ───────────────────────────────────────────────────────────────
Write-Step "Cleanup"
if (!$DryRun -and (Test-Path $TMP)) { Remove-Item $TMP -Recurse -Force; Write-Done "Removed $TMP" }

# ── 13. Validation hints ──────────────────────────────────────────────────────
Write-Step "Validation"
if (!$DryRun) {
    Write-Host "   context-mode validation has two stages:" -ForegroundColor DarkCyan
    Write-Host "   [1] CLI health   -> context-mode doctor" -ForegroundColor DarkCyan
    Write-Host "   [2] MCP smoke    -> run inside session: ctx_doctor, ctx_search(sort: `\"timeline`\"), ctx_batch_execute(...)" -ForegroundColor DarkCyan
    if (Test-Command "context-mode") {
        Invoke-Cmd "context-mode doctor" "context-mode doctor (CLI health)"
        Write-Host "   If MCP tools fail with: Dynamic require of `\"node:fs`\" is not supported" -ForegroundColor Yellow
        Write-Host "   run /ctx-upgrade, restart the session, then re-run MCP smoke tests." -ForegroundColor Yellow
    }
    else {
        Write-Skip "context-mode not in PATH — install/upgrade first, then run MCP smoke tests in-session"
    }
    Write-Host "   MemPalace: mempalace status" -ForegroundColor DarkCyan
    Write-Host "   claude-mem: npx claude-mem worker:status" -ForegroundColor DarkCyan
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
if ($DryRun) {
    Write-Host "Dry run complete. No files changed." -ForegroundColor Magenta
} elseif ($FirstRun) {
    Write-Host "First-run bootstrap complete." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Edit CONTEXT.md with repo purpose, vocab, commands, known risks."
    Write-Host "  2. Install claude-mem from inside Claude Code (see step 10 above)."
    Write-Host "  3. Run: mempalace init ~/projects"
    Write-Host "  4. Run: mempalace mine ~/.claude/projects/ --mode convos"
    Write-Host "  5. Open Claude Code and run: /grill-with-docs"
    Write-Host "  6. See howto.md Section 11 for VS Code / OpenClaw per-repo setup."
} else {
    Write-Host "Sync complete. All managed files updated from FugginOld/ai-config." -ForegroundColor Green
    Write-Host "CONTEXT.md: handled interactively (see above)." -ForegroundColor Yellow
}
