{ nixos-raspberrypi, ... }:

{
  imports = with nixos-raspberrypi.nixosModules; [
    raspberry-pi-4.base
    trusted-nix-caches
  ];

  # PipeWire does not start for root (ConditionUser=!root) and the gadgets run as root,
  # so ALSA's default device goes straight to the 3.5mm jack (8 subdevices: both gadgets can play at once)
  environment.etc."asound.conf".text = ''
    pcm.!default {
      type plug
      slave.pcm "hw:Headphones"
    }
    ctl.!default {
      type hw
      card Headphones
    }
  '';
}
