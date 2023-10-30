with import <nixpkgs> { };

let
  pythonPackages = python3Packages;
in pkgs.mkShell {
  buildInputs = [
    pythonPackages.python

    pythonPackages.pip
    pythonPackages.pandas
    pythonPackages.beautifulsoup4
    pythonPackages.requests
    pythonPackages.lxml
    pythonPackages.tqdm
    pythonPackages.odfpy

    pre-commit
  ];

}
