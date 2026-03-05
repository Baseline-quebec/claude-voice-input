#!/usr/bin/env bash
set -euo pipefail

REPO="Baseline-quebec/claude-voice-input"
INSTALL_DIR="${CLAUDE_VOICE_DIR:-$HOME/.claude-voice-input}"
WHISPER_MODEL="${WHISPER_MODEL:-base}"
WHISPER_DEVICE="${WHISPER_DEVICE:-auto}"
WHISPER_COMPUTE_TYPE="${WHISPER_COMPUTE_TYPE:-int8}"

info() { printf '\033[1;34m[voice]\033[0m %s\n' "$1"; }
error() { printf '\033[1;31m[voice]\033[0m %s\n' "$1" >&2; exit 1; }

# --- Check dependencies ---
info "Vérification des dépendances..."

if ! command -v python3 &>/dev/null; then
    error "Python 3.10+ requis. Installe-le d'abord."
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.minor}")')
if [ "$PYTHON_VERSION" -lt 10 ]; then
    error "Python 3.10+ requis (trouvé 3.$PYTHON_VERSION)."
fi

# PortAudio (needed by sounddevice)
install_portaudio() {
    info "Installation de PortAudio..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y portaudio19-dev
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y portaudio-devel
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm portaudio
    elif command -v brew &>/dev/null; then
        brew install portaudio
    else
        error "Impossible d'installer PortAudio automatiquement. Installe-le manuellement."
    fi
}

# Check if portaudio is available
if ! pkg-config --exists portaudio-2.0 2>/dev/null && ! [ -f /usr/include/portaudio.h ] && ! [ -f /opt/homebrew/include/portaudio.h ]; then
    install_portaudio
fi

# --- Clone or update repo ---
if [ -d "$INSTALL_DIR" ]; then
    info "Mise à jour du repo existant..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    info "Clonage du repo..."
    git clone "https://github.com/$REPO.git" "$INSTALL_DIR"
fi

# --- Create venv and install ---
info "Création de l'environnement virtuel..."
python3 -m venv "$INSTALL_DIR/.venv"
source "$INSTALL_DIR/.venv/bin/activate"

info "Installation des dépendances..."
pip install --upgrade pip -q
pip install -e "$INSTALL_DIR" -q

# --- Verify installation ---
if ! "$INSTALL_DIR/.venv/bin/claude-voice-input" --help &>/dev/null; then
    # faster-whisper MCP server won't have --help, just check the binary exists
    if [ ! -f "$INSTALL_DIR/.venv/bin/claude-voice-input" ]; then
        error "L'installation a échoué — binaire introuvable."
    fi
fi

# --- Configure Claude Code ---
SETTINGS_FILE="$HOME/.claude/settings.json"
SERVER_CMD="$INSTALL_DIR/.venv/bin/claude-voice-input"

info "Configuration de Claude Code..."
mkdir -p "$HOME/.claude"

if [ -f "$SETTINGS_FILE" ]; then
    # Check if voice server already configured
    if python3 -c "import json; d=json.load(open('$SETTINGS_FILE')); exit(0 if 'voice' in d.get('mcpServers',{}) else 1)" 2>/dev/null; then
        info "Serveur MCP 'voice' déjà configuré — mise à jour du chemin."
        python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    settings = json.load(f)
settings['mcpServers']['voice']['command'] = '$SERVER_CMD'
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(settings, f, indent=2)
"
    else
        # Add voice server to existing settings
        python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    settings = json.load(f)
settings.setdefault('mcpServers', {})
settings['mcpServers']['voice'] = {
    'command': '$SERVER_CMD',
    'env': {
        'WHISPER_MODEL': '$WHISPER_MODEL',
        'WHISPER_DEVICE': '$WHISPER_DEVICE',
        'WHISPER_COMPUTE_TYPE': '$WHISPER_COMPUTE_TYPE'
    }
}
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(settings, f, indent=2)
"
    fi
else
    # Create new settings file
    python3 -c "
import json
settings = {
    'mcpServers': {
        'voice': {
            'command': '$SERVER_CMD',
            'env': {
                'WHISPER_MODEL': '$WHISPER_MODEL',
                'WHISPER_DEVICE': '$WHISPER_DEVICE',
                'WHISPER_COMPUTE_TYPE': '$WHISPER_COMPUTE_TYPE'
            }
        }
    }
}
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(settings, f, indent=2)
"
fi

info "Installation terminée !"
echo ""
echo "  Installé dans : $INSTALL_DIR"
echo "  Modèle Whisper : $WHISPER_MODEL"
echo "  Device         : $WHISPER_DEVICE"
echo ""
echo "  Redémarre Claude Code pour activer le serveur vocal."
echo "  Ensuite, demande à Claude : « écoute-moi » ou « voice_listen »"
echo ""
echo "  Pour changer le modèle, réinstalle avec :"
echo "    WHISPER_MODEL=medium bash install.sh"
