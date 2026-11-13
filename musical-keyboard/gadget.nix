{ pkgs, lib, settings, ... }:

let
  soundfont = "Timbres of Heaven GM_GS_XG_SFX V 3.4 Final.sf2";
  # With the typing game on tty1, the musical keyboard waits on tty2 and shows itself on the first MIDI key.
  # Without it, the musical keyboard has tty1 and shows at boot.
  withTypingGame = lib.elem "typing-game" settings.gadgets;
  tty = if withTypingGame then "tty2" else "tty1";
in
{
  assertions = [{
    assertion = builtins.pathExists (./. + "/${soundfont}");
    message = "musical-keyboard: put \"${soundfont}\" in musical-keyboard/ (see musical-keyboard/README.md), and build with ./build.sh";
  }];

  environment.systemPackages = [ pkgs.fluidsynth ];

  # Copy the app and the soundfont into the system (no dotfiles)
  environment.etc."musical-keyboard".source = builtins.path {
    path = ./.;
    name = "musical-keyboard";
    filter = path: type: !(lib.hasPrefix "." (baseNameOf path) || baseNameOf path == "__pycache__");
  };

  # Log in on tty2 at boot (NixOS otherwise starts it only when switched to) so the app waits for MIDI
  systemd.targets.getty.wants = lib.optional withTypingGame "getty@tty2.service";

  programs.bash.interactiveShellInit = ''
    if [ "$(tty)" = "/dev/${tty}" ] && [ "$USER" = "root" ]; then
      cd /etc/musical-keyboard
      exec fbterm -n "DejaVu Sans Mono" -s 8 -- ${pkgs.python3.interpreter} app.py --port ${lib.escapeShellArg settings.midiKeyboard}${lib.optionalString withTypingGame " --wait --vt 2"}
    fi
  '';
}
