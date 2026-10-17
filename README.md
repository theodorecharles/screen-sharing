# Screen Sharing

A native Linux client for Apple's Screen Sharing High Performance protocol.
Save your Macs from the command line, give each one an application launcher,
and open its desktop in a native, GPU-rendered window. Audio, clipboard,
keyboard and mouse support come from the upstream protocol engine.

No browser, local web server, or webview. The only application UI is the
native sign-in/progress dialog and the remote session itself.

## Install on Omarchy / Arch Linux

Install `uv` (or Python with pip/venv), `libfdk-aac`, `portaudio`,
`vulkan-icd-loader`, your GPU's Vulkan driver, and `wl-clipboard`.
Then, from this checkout:

```sh
./scripts/install.sh
```

This installs into `~/.local/share/screen-sharing/venv` and links the
`screen-sharing` command into `~/.local/bin`. Run the installer again after
pulling updates. No root permissions are needed for the application install.

On the Mac, enable **System Settings → General → Sharing → Screen Sharing**
and allow your Mac account to connect. Use a trusted LAN or private network
such as Tailscale. The remote host must support Apple's High Performance mode.

## Save Macs and create their apps

```sh
screen-sharing add 'Mac Mini' \
  --host mac-mini.local --user mac-user --machine mac-mini --shortcut

screen-sharing add 'Mac Studio' \
  --host mac-studio.local --user mac-user --machine mac-studio --shortcut
```

Each creates a separate Omarchy application entry with Apple's machine icon.
Select it from the app launcher to open that connection directly. Its context
menu also provides **Open in Window** and **Open Fullscreen** actions wherever
the desktop launcher supports Freedesktop actions.

```sh
screen-sharing list
screen-sharing connect 'Mac Mini'
screen-sharing connect 'Mac Studio' --fullscreen
screen-sharing edit 'Mac Studio' --fullscreen
screen-sharing edit 'Mac Mini' --host new-address.local --no-audio
screen-sharing shortcut 'Mac Mini'    # recreate or refresh its launcher
screen-sharing remove 'Mac Mini'      # remove profile, launcher, and saved password
```

`add --help` and `edit --help` list resolution, codec, display scale, audio,
keyboard capture, Ctrl-to-Command mapping, and physical-display blanking options.
The default is windowed with audio, automatic display scale, Ctrl-to-Command
mapping, and no physical-display blanking. Omarchy system shortcuts remain
available unless keyboard capture is explicitly enabled and supported.

## Session controls

| Shortcut | Action |
| --- | --- |
| Ctrl+Alt+Enter | Toggle fullscreen / windowed |
| Ctrl+Alt+Escape | Disconnect |
| Window close | Disconnect |

The viewer uses GLFW and wgpu, with native Wayland support on Omarchy. It
remembers the previous window geometry when leaving fullscreen; the compositor
controls placement and tiling on Wayland. On Wayland, fullscreen targets the
primary output. Additional remote monitors can open in separate windows.

Qt renders the sign-in dialog at the compositor's monitor scale, including
HiDPI icons. On Omarchy it reads the active `colors.toml` palette from the
current state directory (or the older config location) and follows theme
changes while open. Other Linux desktops keep their system Qt appearance.
The remote Mac's own theme is controlled on the Mac.

Automatic remote display scale follows the local display, including fractional
scales, and adapts when the viewer moves between differently scaled monitors.
The protocol's virtual-display size limits still apply; a larger requested
canvas can be capped or letterboxed.

## Passwords

Enter the Mac password in the native prompt. **Remember in system keyring**
stores it only after the first video frame arrives. Passwords never appear in
command arguments, desktop entries, or the connections JSON file. The keyring
option is disabled if a supported OS credential store is unavailable.

```sh
screen-sharing password 'Mac Studio'           # prompt and save in system keyring
screen-sharing password 'Mac Studio' --forget
```

Connection settings live at
`$XDG_CONFIG_HOME/screen-sharing/connections.json` (default `~/.config`),
with private file permissions. App launchers live in
`$XDG_DATA_HOME/applications` (default `~/.local/share`).

## Direct connections and diagnostics

```sh
screen-sharing session --host mac.local --user mac-user --fullscreen
screen-sharing session --help
screen-sharing --list-decoders
```

The direct command prompts for the password in the terminal. Automation can
supply it through stdin with `--password-stdin`. Run with `--verbose` for
diagnostics; `--headless --auto-quit-secs 10` runs a short protocol/decode test.

## Development

```sh
uv venv .venv
uv pip install --python .venv/bin/python -e '.[test]'
QT_QPA_PLATFORM=offscreen .venv/bin/pytest
QT_QPA_PLATFORM=offscreen .venv/bin/python tools/viewer_smoke.py --cycle
```

The viewer smoke tool sends a labeled synthetic frame through the actual
GLFW/wgpu window and can cycle fullscreen. It does not connect to a Mac.
Real authentication, audio, and remote input require a live Mac session.

## License and attribution

Code is AGPL-3.0-or-later. See [LICENSE](LICENSE) and [NOTICE](NOTICE) for
upstream attribution. Apple device artwork is separately attributed in
[src/screen_sharing/native/assets/NOTICE](src/screen_sharing/native/assets/NOTICE).
This project is independent of Apple.
