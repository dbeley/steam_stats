with import <nixpkgs> { };

let
  pythonPackages = python3Packages;
in pkgs.mkShell rec {
  name = "steamStatsPythonEnv";
  buildInputs = [
    pythonPackages.python

    pythonPackages.pip
    pythonPackages.pandas
    pythonPackages.beautifulsoup4
    pythonPackages.requests
    pythonPackages.lxml
    pythonPackages.tqdm

    pre-commit
  ];

}
