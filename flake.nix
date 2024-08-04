{
  description = "Application packaged using poetry2nix";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs";
  inputs.poetry2nix = {
    url = "github:nix-community/poetry2nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = inputs @ { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
      in
      {
        packages = {
          default = poetry2nix.mkPoetryApplication { 
            projectDir = self;

            overrides = poetry2nix.overrides.withDefaults (self: super: {

              testcontainters = super.testcontainters.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or []) ++ [ super.hatchling super.hatch-vcs ];
              });

              docker = super.docker.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or []) ++ [ super.hatchling ];
                nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ super.hatchling super.hatch-vcs ];
              });

            });

            buildInputs = [ pkgs.python311Packages.hatchling ];
                       
          };
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.default ];
          packages = [ pkgs.poetry pkgs.mypy ];
        };

        checks = {
          pytest =
            self.packages.${system}.default.overrideAttrs
              (oldAttrs: {
                name = "check-${oldAttrs.name}";
                doCheck = true;
                checkPhase = "pytest";
              });
        };
      });
}