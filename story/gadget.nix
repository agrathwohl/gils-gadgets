{ pkgs, lib, settings, ... }:

let
  python = pkgs.python3.withPackages (ps: [ ps.pyfiglet ps.sherpa-onnx ps.sentencepiece ]);
  models = import ./models.nix { inherit pkgs; };
  # With another gadget on the screen, the story waits on tty4 and shows itself when Gil says "story".
  # Without one, the story has tty1 and shows at boot.
  alone = !(lib.elem "typing-game" settings.gadgets || lib.elem "musical-keyboard" settings.gadgets);
  tty = if alone then "tty1" else "tty4";

  # Only the files that the story reads, in the layout of the repo. Not story/clips/ (test clips, later Gil's
  # voice), story/models (a local build), the soundfont, the songs or the typing game's voices.
  files = builtins.path {
    path = ../.;
    name = "story-files";
    filter = path: type:
      let
        rel = lib.removePrefix "${toString ../.}/" (toString path);
        under = dir: rel == dir || lib.hasPrefix "${dir}/" rel;
        name = baseNameOf path;
      in
      !(lib.hasPrefix "." name || name == "__pycache__")
      && (lib.elem rel [ "screen-saver" "screen-saver/screensaver.py" "typing-game" "typing-game/assets" "musical-keyboard" "musical-keyboard/assets" ]
        || under "story" && !(under "story/clips" || under "story/models")
        || lib.any under [ "screen-saver/pictures" "typing-game/assets/ascii" "musical-keyboard/assets/ascii" ]);
  };
  root = pkgs.runCommand "story-root" { } ''
    cp -r ${files} $out
    chmod u+w $out/story
    ln -s ${models} $out/story/models
  '';
in
{
  environment.etc."story-root".source = root;

  # Log in on tty4 at boot (NixOS otherwise starts it only when switched to) so the story listens
  systemd.targets.getty.wants = lib.optional (!alone) "getty@tty4.service";

  programs.bash.interactiveShellInit = ''
    if [ "$(tty)" = "/dev/${tty}" ] && [ "$USER" = "root" ]; then
      cd /etc/story-root/story
      exec fbterm -n "DejaVu Sans Mono" -s 8 -- ${python.interpreter} story.py${lib.optionalString (!alone) " --wait --vt 4"}
    fi
  '';
}
