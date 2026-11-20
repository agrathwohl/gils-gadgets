{ pkgs, lib, settings, ... }:

let
  python = pkgs.python3.withPackages (ps: [ ps.pyfiglet ]);

  # Cron runs this every minute that a screen saver is on. When the screens were idle long enough, it shows
  # the screen saver on its own console (tty9). When a key stops it, openvt switches back to the console from before.
  screenSaver = pkgs.writeShellScript "screen-saver" ''
    . /etc/set-environment  # LANG and LOCALE_ARCHIVE, for the pictures in Braille
    cd /etc/screen-saver
    ${python.interpreter} screensaver.py --check "$1" || exit 0
    exec openvt -c 9 -s -w -- fbterm -n "DejaVu Sans Mono" -s 8 -- ${python.interpreter} screensaver.py "$1"
  '';
in
{
  # Copy the app into the system (no dotfiles)
  environment.etc."screen-saver".source = builtins.path {
    path = ./.;
    name = "screen-saver";
    filter = path: type: !(lib.hasPrefix "." (baseNameOf path) || baseNameOf path == "__pycache__");
  };

  # The times in screensavers.toml are in this time zone
  time.timeZone = settings.timeZone;

  # One crontab line for each screen saver. flock: one screen saver at a time. Cron reads % as a new line.
  services.cron.enable = true;
  services.cron.systemCronJobs = lib.mapAttrsToList
    (name: saver: "${saver.when} root flock -n /run/screen-saver.lock ${screenSaver} ${lib.replaceStrings [ "%" ] [ "\\%" ] (lib.escapeShellArg name)}")
    (builtins.fromTOML (builtins.readFile ./screensavers.toml));
}
