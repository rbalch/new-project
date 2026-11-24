{
  # Tools for working on the template itself: rendering a scaffold and running its gate.
  description = "new-project (template) dev shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            python313
            uv
            git
            gh
            gnumake
            jq
          ];

          # Nix owns the interpreter; uv never downloads its own, so the shell and
          # pyproject's requires-python agree on one Python.
          env = {
            UV_PYTHON = "${pkgs.python313}/bin/python3.13";
            UV_PYTHON_DOWNLOADS = "never";
          };
        };
      });
    };
}
