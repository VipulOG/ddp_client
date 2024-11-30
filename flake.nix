{
  description = "Python development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
      p2n = poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };

      pypkgs-build-requirements = {};

      p2n-overrides = p2n.defaultPoetryOverrides.extend (self: super:
        builtins.mapAttrs (package: build-requirements:
          (builtins.getAttr package super).overridePythonAttrs (old: {
            buildInputs = (old.buildInputs or [ ]) ++ (builtins.map (pkg:
                if builtins.isString pkg then builtins.getAttr pkg super else pkg
              ) build-requirements);
          })
        ) pypkgs-build-requirements
      );

      poetryEnv = p2n.mkPoetryEnv {
        projectDir = ./.;
        python = pkgs.python311;
        preferWheels = true;
        overrides = p2n-overrides;
      };

    in {
      devShells.default = pkgs.mkShell {
        buildInputs = [
          poetryEnv
          pkgs.poetry
        ];
      };
    }
  );
}
