{ nixos-raspberrypi, settings, ... }:

{
  imports = with nixos-raspberrypi.nixosModules; [
    raspberry-pi-5.base
    trusted-nix-caches
  ];

  # HDMI 0 has one subdevice: only one program can play at a time, so only one gadget can have sound
  assertions = [{
    assertion = builtins.length settings.gadgets < 2;
    message = "rpi5: HDMI sound plays one program at a time, so choose one gadget in gadgets.nix";
  }];

  # Pi 5 has no headphone jack. PipeWire does not start for root (ConditionUser=!root) and the
  # gadgets run as root, so ALSA's default device goes straight to HDMI 0
  # (alsa-lib's vc4-hdmi card config does the IEC958 conversion)
  environment.etc."asound.conf".text = ''
    pcm.!default {
      type plug
      slave.pcm "sysdefault:CARD=vc4hdmi0"
    }
    ctl.!default {
      type hw
      card vc4hdmi0
    }
  '';
}
