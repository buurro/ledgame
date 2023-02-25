{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "nixpkgs/22.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        ampy = pkgs.adafruit-ampy;
      in
      {
        devShells = {
          default = pkgs.mkShell {
            buildInputs = [ ampy pkgs.black ];
            shellHook = ''
              export AMPY_PORT=/dev/tty.usbmodem1413201
            '';
          };
        };
        apps.ampy = {
          type = "app";
          program = "${ampy}/bin/ampy";
        };
      }
    );
}
