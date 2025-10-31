{ pkgs, lib, config, inputs, ... }:

{
  packages = [
    config.languages.python.package.pkgs.pjsua2
    pkgs.git
  ];

  languages.python = {
    enable = true;
    version = "3.13";
    directory = "./";
    venv.enable = true;
    venv.quiet = true;
    venv.requirements = ''click
requests
pydantic
pydantic-settings
markdown
bs4'';
  };

  git-hooks.hooks = {
    clippy.enable = true;
  };
  
  enterShell = ''
    pip install --upgrade pip
    git --version
    python --version
    pip install -e .
  '';

}
