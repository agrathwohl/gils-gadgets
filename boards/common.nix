{ settings, pkgs, lib, ... }:

{
  # Prevent ZFS build failure
  boot.supportedFilesystems.zfs = lib.mkForce false;

  # When the Pi cannot read the display's EDID at boot, it falls back to 1024x768
  # and the bottom of the console is off a smaller panel
  boot.kernelParams = lib.optionals (settings.screen != null) [
    "video=HDMI-A-1:${settings.screen}M@60D"
    "video=HDMI-A-2:${settings.screen}M@60D"
  ];

  # Audio (boards/<board>.nix sets the output)
  services.pulseaudio.enable = false;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };

  # Console font — Unifont has Braille Patterns (U+2800-U+28FF) for the ASCII art assets
  console.font = "${pkgs.unifont}/share/consolefonts/Unifont-APL8x16.psf.gz";

  # Auto-login as root; each gadget starts from root's login shell (see <gadget>/gadget.nix)
  services.getty.autologinUser = "root";

  environment.systemPackages = with pkgs; [
    alsa-utils
    vim
    fbterm
    dejavu_fonts
  ];

  # Basic networking
  networking = {
    hostName = "gils-gadgets";
    wireless.enable = false;
  };

  # Disable unnecessary services
  systemd.services.NetworkManager.enable = false;

  system.stateVersion = "24.11";
}
