with import <nixpkgs> { };

let
  pythonPackages = python3Packages;
in pkgs.mkShell {
  buildInputs = [
    pythonPackages.python

    # Core dependencies
    pythonPackages.pip
    pythonPackages.pandas
    pythonPackages.beautifulsoup4
    pythonPackages.requests
    pythonPackages.lxml
    pythonPackages.tqdm
    pythonPackages.odfpy
    pythonPackages.openpyxl

    # Development tools
    prek
    ruff
    pythonPackages.pytest
    pythonPackages.pytest-cov
    pythonPackages.pytest-mock
    ty
  ];

}
