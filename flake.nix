{
  inputs.nixos-raspberrypi.url = "github:nvmd/nixos-raspberrypi/main";

  outputs = { nixos-raspberrypi, ... }:
    let settings = import ./gadgets.nix; in {
      nixosConfigurations.gils-gadgets = nixos-raspberrypi.lib.nixosSystem {
        specialArgs = { inherit nixos-raspberrypi settings; };
        modules = [
          nixos-raspberrypi.nixosModules.sd-image
          ./boards/common.nix
          ./boards/${settings.board}.nix
        ] ++ map (gadget: ./${gadget}/gadget.nix) settings.gadgets;
      };
    };
}
