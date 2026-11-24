{
  # Ships nearly empty on purpose. Fill it with every tool {project_name} uses, the first
  # time you work in the repo and whenever a task needs a new one. Never install a tool
  # any other way.
  description = "{project_name} dev shell";

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
            # TODO: add the project's tools here (e.g. ruff, jq, google-cloud-sdk, docker-client).
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
