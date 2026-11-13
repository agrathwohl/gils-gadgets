{ pkgs, lib, ... }:

{
  environment.systemPackages = [ (pkgs.python3.withPackages (ps: [ ps.pyfiglet ])) ];

  # Copy the typing game into the system (all files in this folder, also audio/, but no dotfiles)
  environment.etc."typing-game".source = builtins.path {
    path = ./.;
    name = "typing-game";
    filter = path: type: !(lib.hasPrefix "." (baseNameOf path) || baseNameOf path == "__pycache__");
  };

  # Create symlink to game in root's home
  system.activationScripts.typingGame = ''
    ln -sfn /etc/typing-game /root/typing-game
  '';

  # Auto-start the typing game on root login on tty1 via fbterm (TTF font rendering with Braille support)
  programs.bash.interactiveShellInit = ''
    if [ "$(tty)" = "/dev/tty1" ] && [ "$USER" = "root" ]; then
      cd /root/typing-game
      exec fbterm -n "DejaVu Sans Mono" -s 8 -- python3 main.py
    fi
  '';
}
