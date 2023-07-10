with import <nixpkgs> { };

let
  pythonPackages = python3Packages;
in pkgs.mkShell rec {
  name = "steamStatsPythonEnv";
  venvDir = "~/Documents/venvs/steam_stats_venv";
  buildInputs = [
    pythonPackages.python

    pythonPackages.pip
    pythonPackages.pandas
    pythonPackages.beautifulsoup4
    pythonPackages.requests
    pythonPackages.lxml
    pythonPackages.tqdm
    pythonPackages.openpyxl
    pythonPackages.odfpy

  ];

}
